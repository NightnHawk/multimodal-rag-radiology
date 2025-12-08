"""Embedding service using open_clip for RTG scan embeddings."""
import open_clip
import torch
from PIL import Image
from typing import List, Union
import numpy as np
import logging

logger = logging.getLogger(__name__)


class EmbeddingService:
    """Service for generating embeddings using CLIP model."""
    
    def __init__(self, model_name: str = "hf-hub:luhuitong/CLIP-ViT-L-14-448px-MedICaT-ROCO"):
        """
        Initialize the embedding service.
        
        Args:
            model_name: Name of the CLIP model to use
        """
        self.model_name = model_name
        self.model = None
        self.preprocess = None
        self.tokenizer = None
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        logger.info(f"Using device: {self.device}")
        
    def _load_model(self):
        """Lazy load the model (loads on first use)."""
        if self.model is None:
            logger.info(f"Loading CLIP model: {self.model_name}")
            try:
                self.model, _, self.preprocess = open_clip.create_model_and_transforms(
                    self.model_name,
                    pretrained=True,
                    device=self.device
                )
                self.model.eval()
                logger.info("Model loaded successfully")
            except Exception as e:
                logger.error(f"Error loading model: {str(e)}")
                raise
    
    def embed_image(self, image: Image.Image) -> np.ndarray:
        """
        Generate embedding for a single image.
        
        Args:
            image: PIL Image object
            
        Returns:
            numpy array of embedding vector
        """
        self._load_model()
        
        try:
            # Preprocess image
            image_tensor = self.preprocess(image).unsqueeze(0).to(self.device)
            
            # Generate embedding
            with torch.no_grad():
                image_features = self.model.encode_image(image_tensor)
                # Normalize embeddings
                image_features = image_features / image_features.norm(dim=-1, keepdim=True)
                embedding = image_features.cpu().numpy().flatten()
            
            return embedding.astype(np.float32)
            
        except Exception as e:
            logger.error(f"Error generating embedding: {str(e)}")
            raise
    
    def embed_images(self, images: List[Image.Image]) -> List[np.ndarray]:
        """
        Generate embeddings for multiple images (batch processing).
        
        Args:
            images: List of PIL Image objects
            
        Returns:
            List of numpy arrays (embedding vectors)
        """
        self._load_model()
        
        try:
            # Preprocess all images
            image_tensors = torch.stack([
                self.preprocess(img) for img in images
            ]).to(self.device)
            
            # Generate embeddings
            with torch.no_grad():
                image_features = self.model.encode_image(image_tensors)
                # Normalize embeddings
                image_features = image_features / image_features.norm(dim=-1, keepdim=True)
                embeddings = image_features.cpu().numpy()
            
            return [emb.astype(np.float32) for emb in embeddings]
            
        except Exception as e:
            logger.error(f"Error generating batch embeddings: {str(e)}")
            raise
    
    def get_embedding_dimension(self) -> int:
        """
        Get the dimension of embeddings produced by this model.
        
        Returns:
            Embedding dimension
        """
        self._load_model()
        # CLIP ViT-L-14 typically produces 768-dimensional embeddings
        # Test with a dummy image to get actual dimension
        dummy_image = Image.new('RGB', (224, 224), color='white')
        test_embedding = self.embed_image(dummy_image)
        return len(test_embedding)


# Global embedding service instance
_embedding_service: EmbeddingService = None


def get_embedding_service(model_name: str = None) -> EmbeddingService:
    """
    Get or create the global embedding service instance.
    
    Args:
        model_name: Optional model name (uses default if None)
        
    Returns:
        EmbeddingService instance
    """
    global _embedding_service
    if _embedding_service is None:
        from app.config import settings
        model = model_name or settings.clip_model_name
        _embedding_service = EmbeddingService(model)
    return _embedding_service

