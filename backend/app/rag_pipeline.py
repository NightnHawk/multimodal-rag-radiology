"""RAG pipeline orchestrating the complete workflow."""
import uuid
from typing import Dict, Any, Optional, List
import logging
from PIL import Image
import os

from app.embedding import get_embedding_service
from app.opensearch_client import get_opensearch_client
from app.gpt_client import get_gpt_client
from app.ai_judge import get_ai_judge
from app.dicom_processor import load_image_from_bytes
from app.string_similarity import StringSimilarity
from app.config import settings

logger = logging.getLogger(__name__)


class RAGPipeline:
    """Main RAG pipeline orchestrator."""
    
    def __init__(self):
        """Initialize RAG pipeline components."""
        self.embedding_service = get_embedding_service()
        self.opensearch_client = get_opensearch_client()
        self.gpt_client = get_gpt_client()
        self.ai_judge = get_ai_judge()
        
        # Initialize string similarity validator if enabled
        self.string_similarity = None
        if settings.enable_description_validation:
            try:
                self.string_similarity = StringSimilarity(
                    sentence_transformer_model=settings.sentence_transformer_model
                )
                logger.info("String similarity validation enabled")
            except Exception as e:
                logger.warning(f"Failed to initialize string similarity validator: {str(e)}")
                logger.warning("Continuing without description validation")
        
        # Ensure index exists
        if not self.opensearch_client.index_exists():
            logger.info("Creating OpenSearch index...")
            self.opensearch_client.create_index()
    
    def process_query(
        self,
        image_bytes: bytes,
        filename: str,
        use_retrieved_images: bool = False,
        clear_context: bool = False
    ) -> Dict[str, Any]:
        """
        Process a query through the complete RAG pipeline.
        
        Args:
            image_bytes: Image file as bytes (DICOM, PNG, or JPG)
            filename: Original filename
            use_retrieved_images: Whether to include retrieved images in GPT prompt
            clear_context: If True, start a fresh conversation with GPT (no influence from previous queries)
            
        Returns:
            Dictionary with query_id, generated_description, retrieved_documents,
            quality_score, quality_approved, and message
        """
        query_id = str(uuid.uuid4())
        
        try:
            # Step 1: Load and process input image
            logger.info(f"Processing query {query_id}: Loading image")
            input_image = load_image_from_bytes(image_bytes, filename)
            
            # Step 2: Generate embedding
            logger.info(f"Processing query {query_id}: Generating embedding")
            embedding = self.embedding_service.embed_image(input_image)
            embedding_list = embedding.tolist()
            
            # Step 3: Retrieve and validate documents until we have exactly k_retrieval_count validated documents
            logger.info(f"Processing query {query_id}: Searching OpenSearch")
            target_count = settings.k_retrieval_count
            validated_docs = []
            all_retrieved_docs = []
            excluded_doc_ids = []
            validation_info = None
            max_iterations = 5  # Prevent infinite loops
            iteration = 0
            use_validation = (self.string_similarity and settings.enable_description_validation 
                            and settings.ensure_exact_count)
            
            while len(validated_docs) < target_count and iteration < max_iterations:
                iteration += 1
                # Calculate how many more documents we need
                needed = target_count - len(validated_docs)
                
                if use_validation:
                    # Retrieve more than needed to account for potential outliers
                    retrieve_count = max(needed, int(target_count * settings.initial_retrieval_multiplier))
                else:
                    # No validation - just retrieve what we need
                    retrieve_count = needed
                
                logger.info(
                    f"Retrieval iteration {iteration}: Need {needed} more documents, "
                    f"retrieving {retrieve_count} (excluding {len(excluded_doc_ids)} already processed)"
                )
                
                # Retrieve documents (excluding already processed ones)
                batch_docs = self.opensearch_client.search_similar(
                    embedding_list,
                    k=retrieve_count,
                    exclude_doc_ids=excluded_doc_ids if excluded_doc_ids else None
                )
                
                if not batch_docs:
                    logger.warning(f"No more documents available in index")
                    break
                
                all_retrieved_docs.extend(batch_docs)
                
                # Validate this batch if validation is enabled
                if use_validation:
                    logger.info(f"Validating batch of {len(batch_docs)} documents")
                    batch_validated, batch_outliers, batch_validation_info = self.string_similarity.validate_retrieved_documents(
                        batch_docs,
                        similarity_threshold=settings.similarity_threshold,
                        min_approved_ratio=settings.min_approved_ratio
                    )
                    
                    # Add validated documents to our collection
                    validated_docs.extend(batch_validated)
                    
                    # Track excluded document IDs for next iteration
                    for doc in batch_docs:
                        if doc.get("_id"):
                            excluded_doc_ids.append(doc["_id"])
                    
                    # Update validation info (aggregate across all batches)
                    if validation_info is None:
                        validation_info = batch_validation_info.copy()
                        validation_info["total_retrieved"] = len(batch_docs)
                        validation_info["total_validated"] = len(batch_validated)
                        validation_info["iterations"] = iteration
                    else:
                        validation_info["total_retrieved"] += len(batch_docs)
                        validation_info["total_validated"] = len(validated_docs)
                        validation_info["iterations"] = iteration
                    
                    logger.info(
                        f"Batch validation: {len(batch_validated)} validated, "
                        f"{len(batch_outliers)} outliers. Total validated: {len(validated_docs)}/{target_count}"
                    )
                else:
                    # No validation - use all documents
                    validated_docs.extend(batch_docs)
                    if len(validated_docs) >= target_count:
                        break
                    # Track excluded document IDs for next iteration
                    for doc in batch_docs:
                        if doc.get("_id"):
                            excluded_doc_ids.append(doc["_id"])
            
            # Take exactly target_count documents
            retrieved_docs = validated_docs[:target_count]
            
            if not retrieved_docs:
                return {
                    "query_id": query_id,
                    "generated_description": "",
                    "retrieved_documents": [],
                    "quality_score": None,
                    "quality_approved": False,
                    "message": "No similar documents found in index. Please index some data first.",
                    "validation_info": validation_info,
                    "prompt_used": None
                }
            
            # Update validation info with final counts
            if validation_info:
                validation_info["final_count"] = len(retrieved_docs)
                validation_info["requested_count"] = target_count
                if len(retrieved_docs) < target_count:
                    logger.warning(
                        f"Could only retrieve {len(retrieved_docs)} validated documents "
                        f"out of {target_count} requested after {iteration} iterations"
                    )
                else:
                    logger.info(
                        f"Successfully retrieved exactly {len(retrieved_docs)} validated documents "
                        f"after {iteration} iteration(s)"
                    )
            elif use_validation is False and len(retrieved_docs) < target_count:
                logger.warning(
                    f"Could only retrieve {len(retrieved_docs)} documents "
                    f"out of {target_count} requested (validation disabled)"
                )
            
            # Step 4: Optionally load retrieved images
            retrieved_images = []
            if use_retrieved_images:
                logger.info(f"Processing query {query_id}: Loading retrieved images")
                from app.dicom_processor import load_image
                base_path = settings.dicom_data_path
                for doc in retrieved_docs:
                    try:
                        img_path = doc['image_path']
                        # Resolve relative paths against configured DICOM base path
                        if not os.path.isabs(img_path):
                            img_path = os.path.join(base_path, img_path)
                        img = load_image(img_path)
                        retrieved_images.append(img)
                    except Exception as e:
                        logger.warning(f"Could not load image {doc['image_path']}: {str(e)}")
            
            # Step 5: Generate description using GPT-4o
            logger.info(f"Processing query {query_id}: Generating description with GPT-4o (clear_context={clear_context})")
            prompt_used = None
            if use_retrieved_images and retrieved_images:
                generated_description, prompt_used = self.gpt_client.generate_with_retrieved_images(
                    input_image,
                    retrieved_docs,
                    retrieved_images,
                    clear_context=clear_context
                )
            else:
                generated_description, prompt_used = self.gpt_client.generate_description(
                    input_image,
                    retrieved_docs,
                    filename.split('.')[-1].lower(),
                    clear_context=clear_context
                )
            
            if not prompt_used:
                logger.warning(f"Warning: prompt_used is None for query {query_id} - building fallback prompt")
                # Build prompt as fallback
                try:
                    if use_retrieved_images and retrieved_images:
                        prompt_text = self.gpt_client._build_prompt_with_images(retrieved_docs)
                    else:
                        prompt_text = self.gpt_client._build_prompt(retrieved_docs, filename.split('.')[-1].lower())
                    system_prompt = "You are an expert chest X-ray radiologist."
                    if clear_context:
                        system_prompt += " This is a new, independent analysis. Do not reference or be influenced by any previous queries or conversations."
                    if use_retrieved_images and retrieved_images:
                        prompt_used = f"System: {system_prompt}\n\nUser: {prompt_text}\n\n[Images: {len(retrieved_images) + 1} images - input image + {len(retrieved_images)} reference images, all base64 encoded]"
                    else:
                        prompt_used = f"System: {system_prompt}\n\nUser: {prompt_text}\n\n[Image: base64 encoded]"
                    logger.info(f"Built fallback prompt for query {query_id}")
                except Exception as e:
                    logger.error(f"Could not build fallback prompt: {str(e)}")
                    prompt_used = "Error: Could not build prompt"
            
            logger.info(f"Prompt used length: {len(prompt_used) if prompt_used else 0}")
            
            # Step 6: Validate with AI-as-Judge
            logger.info(f"Processing query {query_id}: Validating with AI Judge")
            evaluation = self.ai_judge.evaluate_quality(
                generated_description,
                filename.split('.')[-1].lower(),
                retrieved_docs
            )
            
            # Step 7: Return results
            # Ensure prompt_used is always a string, never None
            if not prompt_used:
                logger.error(f"prompt_used is still None/empty for query {query_id} after all attempts")
                prompt_used = "Error: Prompt could not be retrieved"
            
            result = {
                "query_id": query_id,
                "generated_description": generated_description,
                "retrieved_documents": retrieved_docs,
                "quality_score": evaluation["quality_score"],
                "quality_approved": evaluation["approved"],
                "message": evaluation["feedback"] if not evaluation["approved"] else None,
                "validation_info": validation_info,
                "prompt_used": prompt_used
            }
            
            logger.info(f"Returning result with prompt_used length: {len(prompt_used)}")
            
            logger.info(f"Query {query_id} completed: approved={evaluation['approved']}")
            return result
            
        except Exception as e:
            logger.error(f"Error processing query {query_id}: {str(e)}")
            return {
                "query_id": query_id,
                "generated_description": "",
                "retrieved_documents": [],
                "quality_score": None,
                "quality_approved": False,
                "message": f"Error processing query: {str(e)}",
                "validation_info": None,
                "prompt_used": None
            }
    
    def regenerate_query(
        self,
        query_id: str,
        image_bytes: Optional[bytes] = None,
        filename: Optional[str] = None,
        use_same_retrieval: bool = False
    ) -> Dict[str, Any]:
        """
        Regenerate answer for a query (optionally with new retrieval).
        
        Args:
            query_id: Original query ID (for tracking)
            image_bytes: Optional new image bytes (if None, uses cached)
            filename: Optional filename
            use_same_retrieval: Whether to use same retrieval or re-query
            
        Returns:
            Same format as process_query
        """
        # For now, just process again (in production, you'd cache embeddings/retrievals)
        if image_bytes and filename:
            return self.process_query(image_bytes, filename)
        else:
            return {
                "query_id": query_id,
                "generated_description": "",
                "retrieved_documents": [],
                "quality_score": None,
                "quality_approved": False,
                "message": "Cannot regenerate without image. Please provide image bytes.",
                "validation_info": None,
                "prompt_used": None
            }


# Global RAG pipeline instance
_rag_pipeline: RAGPipeline = None


def get_rag_pipeline() -> RAGPipeline:
    """
    Get or create the global RAG pipeline instance.
    
    Returns:
        RAGPipeline instance
    """
    global _rag_pipeline
    if _rag_pipeline is None:
        _rag_pipeline = RAGPipeline()
    return _rag_pipeline

