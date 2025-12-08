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
        
        # Ensure index exists
        if not self.opensearch_client.index_exists():
            logger.info("Creating OpenSearch index...")
            self.opensearch_client.create_index()
    
    def process_query(
        self,
        image_bytes: bytes,
        filename: str,
        use_retrieved_images: bool = False
    ) -> Dict[str, Any]:
        """
        Process a query through the complete RAG pipeline.
        
        Args:
            image_bytes: Image file as bytes (DICOM, PNG, or JPG)
            filename: Original filename
            use_retrieved_images: Whether to include retrieved images in GPT prompt
            
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
            
            # Step 3: Retrieve similar documents from OpenSearch
            logger.info(f"Processing query {query_id}: Searching OpenSearch")
            retrieved_docs = self.opensearch_client.search_similar(
                embedding_list,
                k=settings.k_retrieval_count
            )
            
            if not retrieved_docs:
                return {
                    "query_id": query_id,
                    "generated_description": "",
                    "retrieved_documents": [],
                    "quality_score": None,
                    "quality_approved": False,
                    "message": "No similar documents found in index. Please index some data first."
                }
            
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
            logger.info(f"Processing query {query_id}: Generating description with GPT-4o")
            if use_retrieved_images and retrieved_images:
                generated_description = self.gpt_client.generate_with_retrieved_images(
                    input_image,
                    retrieved_docs,
                    retrieved_images
                )
            else:
                generated_description = self.gpt_client.generate_description(
                    input_image,
                    retrieved_docs,
                    filename.split('.')[-1].lower()
                )
            
            # Step 6: Validate with AI-as-Judge
            logger.info(f"Processing query {query_id}: Validating with AI Judge")
            evaluation = self.ai_judge.evaluate_quality(
                generated_description,
                filename.split('.')[-1].lower(),
                retrieved_docs
            )
            
            # Step 7: Return results
            result = {
                "query_id": query_id,
                "generated_description": generated_description,
                "retrieved_documents": retrieved_docs,
                "quality_score": evaluation["quality_score"],
                "quality_approved": evaluation["approved"],
                "message": evaluation["feedback"] if not evaluation["approved"] else None
            }
            
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
                "message": f"Error processing query: {str(e)}"
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
                "message": "Cannot regenerate without image. Please provide image bytes."
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

