"""Configuration management for the application."""
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # OpenSearch Configuration
    opensearch_host: str = "localhost"
    opensearch_port: int = 9200
    opensearch_user: Optional[str] = None
    opensearch_password: Optional[str] = None
    opensearch_use_ssl: bool = False
    opensearch_verify_certs: bool = False
    
    # OpenAI Configuration
    openai_api_key: str
    
    # Application Configuration
    index_name: str = "rtg_scans_index"
    embedding_dimension: int = 768
    k_retrieval_count: int = 5
    
    # String Similarity Validation Configuration
    enable_description_validation: bool = True
    similarity_threshold: float = 0.5
    min_approved_ratio: float = 0.6
    filter_outliers: bool = True  # If True, remove outliers from retrieved documents
    ensure_exact_count: bool = True  # If True, ensure exactly k_retrieval_count validated documents
    initial_retrieval_multiplier: float = 2.0  # Retrieve this many times more documents initially
    sentence_transformer_model: str = "kamalkraj/BioSimCSE-BioLinkBERT-BASE"
    
    # Model Configuration
    clip_model_name: str = "hf-hub:luhuitong/CLIP-ViT-L-14-448px-MedICaT-ROCO"
    
    # Data Paths
    dicom_data_path: str = "../data"
    json_metadata_path: str = "../data/metadata.json"
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


# Global settings instance
settings = Settings()

