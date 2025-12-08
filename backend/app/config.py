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

