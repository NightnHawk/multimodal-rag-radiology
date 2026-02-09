"""String similarity checking for retrieved document validation."""
from sentence_transformers import SentenceTransformer, util
from rapidfuzz import fuzz
from rapidfuzz.utils import default_process
import numpy as np
from typing import List, Dict, Tuple
import logging

logger = logging.getLogger(__name__)


class StringSimilarity:
    """Class for computing string similarities using multiple methods."""
    
    def __init__(self, sentence_transformer_model: str = "kamalkraj/BioSimCSE-BioLinkBERT-BASE"):
        """
        Initialize StringSimilarity with a sentence transformer model.
        
        Args:
            sentence_transformer_model: Model name for sentence transformer
        """
        self.sentence_transformer_model = sentence_transformer_model
        logger.info(f"Loading sentence transformer model: {sentence_transformer_model}")
        try:
            self.model = SentenceTransformer(self.sentence_transformer_model)
            logger.info("Sentence transformer model loaded successfully")
        except Exception as e:
            logger.error(f"Error loading sentence transformer model: {str(e)}")
            raise
    
    def emb_similarity(self, s1: str, s2: str) -> float:
        """
        Compute embedding-based similarity between two strings.
        
        Args:
            s1: First string
            s2: Second string
            
        Returns:
            Cosine similarity score between 0 and 1
        """
        try:
            embeddings = self.model.encode([s1, s2], convert_to_tensor=True)
            score = util.pytorch_cos_sim(embeddings[0], embeddings[1]).item()
            return float(score)
        except Exception as e:
            logger.warning(f"Error computing embedding similarity: {str(e)}")
            return 0.0
    
    @staticmethod
    def preprocess(text: str) -> str:
        """
        Preprocess text for fuzzy matching.
        
        Args:
            text: Input text
            
        Returns:
            Preprocessed text
        """
        return default_process(text)
    
    def token_similarity(self, text1: str, text2: str) -> float:
        """
        Compute token-based similarity using token set ratio.
        
        Args:
            text1: First text
            text2: Second text
            
        Returns:
            Similarity score between 0 and 1
        """
        p1, p2 = self.preprocess(text1), self.preprocess(text2)
        return fuzz.token_set_ratio(p1, p2) / 100.0
    
    def weighted_similarity(self, text1: str, text2: str) -> float:
        """
        Compute weighted similarity using WRatio.
        
        Args:
            text1: First text
            text2: Second text
            
        Returns:
            Similarity score between 0 and 1
        """
        p1, p2 = self.preprocess(text1), self.preprocess(text2)
        return fuzz.WRatio(p1, p2) / 100.0
    
    def similarity_matrix(self, texts: List[str]) -> np.ndarray:
        """
        Compute similarity matrix for a list of texts.
        
        Args:
            texts: List of text strings
            
        Returns:
            NxN numpy array of similarity scores
        """
        n = len(texts)
        matrix = np.zeros((n, n))
        
        for i in range(n):
            for j in range(n):
                if i == j:
                    matrix[i, j] = 1.0
                else:
                    # Use embedding similarity for better semantic understanding
                    matrix[i, j] = self.emb_similarity(texts[i], texts[j])
        
        return matrix
    
    def validate_retrieved_documents(
        self,
        retrieved_docs: List[Dict],
        similarity_threshold: float = 0.5,
        min_approved_ratio: float = 0.6
    ) -> Tuple[List[Dict], List[Dict], Dict]:
        """
        Validate retrieved documents by checking description similarity.
        
        Args:
            retrieved_docs: List of retrieved documents with descriptions
            similarity_threshold: Minimum similarity score to consider a match
            min_approved_ratio: Minimum ratio of documents that should match
            
        Returns:
            Tuple of (validated_docs, outliers, validation_info)
        """
        if not retrieved_docs or len(retrieved_docs) < 2:
            return retrieved_docs, [], {"message": "Insufficient documents for validation"}
        
        # Extract descriptions (combine short and full descriptions)
        descriptions = []
        for doc in retrieved_docs:
            short_desc = doc.get('short_description', '')
            full_desc = doc.get('full_description', '')
            # Combine descriptions for better context
            combined = f"{short_desc}. {full_desc}".strip()
            descriptions.append(combined if combined else "No description")
        
        # Compute similarity matrix
        logger.info(f"Computing similarity matrix for {len(descriptions)} documents")
        matrix = self.similarity_matrix(descriptions)
        
        # Calculate mean similarity for each document (excluding self-similarity)
        mean_similarities = []
        for i in range(len(descriptions)):
            # Exclude diagonal (self-similarity)
            similarities = [matrix[i, j] for j in range(len(descriptions)) if i != j]
            mean_sim = np.mean(similarities) if similarities else 0.0
            mean_similarities.append(mean_sim)
        
        mean_similarities = np.array(mean_similarities)
        
        # Identify outliers (documents with mean similarity below threshold)
        outlier_indices = np.where(mean_similarities < similarity_threshold)[0]
        valid_indices = np.where(mean_similarities >= similarity_threshold)[0]
        
        # Separate validated docs and outliers
        validated_docs = []
        for i in valid_indices:
            doc = retrieved_docs[i].copy()  # Create a copy to avoid modifying original
            doc['mean_similarity'] = float(mean_similarities[i])
            validated_docs.append(doc)
        
        outliers = []
        for i in outlier_indices:
            doc = retrieved_docs[i].copy()  # Create a copy to avoid modifying original
            doc['mean_similarity'] = float(mean_similarities[i])
            outliers.append(doc)
        
        # Check if enough documents passed validation
        approval_ratio = len(validated_docs) / len(retrieved_docs) if retrieved_docs else 0
        
        validation_info = {
            "total_documents": len(retrieved_docs),
            "validated_count": len(validated_docs),
            "outlier_count": len(outliers),
            "approval_ratio": float(approval_ratio),
            "mean_similarity_threshold": similarity_threshold,
            "passed_validation": approval_ratio >= min_approved_ratio,
            "mean_similarities": mean_similarities.tolist(),
            "total_retrieved": len(retrieved_docs),  # For tracking across batches
            "total_validated": len(validated_docs),  # For tracking across batches
            "iterations": 1,  # Will be updated by pipeline
            "final_count": len(validated_docs),  # Will be updated by pipeline
            "requested_count": None  # Will be set by pipeline
        }
        
        if outliers:
            logger.warning(
                f"Found {len(outliers)} outlier documents with mean similarity < {similarity_threshold}"
            )
        
        return validated_docs, outliers, validation_info
