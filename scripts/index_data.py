"""Batch indexing script for DICOM files from JSON metadata."""
import sys
import os
import json
import logging
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from app.opensearch_client import get_opensearch_client
from app.embedding import get_embedding_service
from app.dicom_processor import load_image
from app.config import settings

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def index_from_json(json_path: str = None, dicom_base_path: str = None):
    """
    Index DICOM files from JSON metadata file.
    
    Args:
        json_path: Path to JSON metadata file (uses config default if None)
        dicom_base_path: Base path for DICOM files (uses config default if None)
    """
    json_path = json_path or settings.json_metadata_path
    dicom_base_path = dicom_base_path or settings.dicom_data_path
    
    # Check if JSON file exists
    if not os.path.exists(json_path):
        logger.error(f"JSON file not found: {json_path}")
        logger.info(f"Please ensure your JSON metadata file exists at: {json_path}")
        logger.info("Or specify the path using: python index_data.py <json_path> [dicom_base_path]")
        return
    
    # Read JSON file
    logger.info(f"Reading JSON metadata from: {json_path}")
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            metadata = json.load(f)
    except Exception as e:
        logger.error(f"Error reading JSON file: {str(e)}")
        return
    
    if not isinstance(metadata, list):
        logger.error("JSON file must contain an array of objects")
        return
    
    logger.info(f"Found {len(metadata)} items to index")
    
    # Initialize services
    logger.info("Initializing services...")
    opensearch_client = get_opensearch_client()
    embedding_service = get_embedding_service()
    
    # Ensure index exists
    if not opensearch_client.index_exists():
        logger.info("Creating OpenSearch index...")
        opensearch_client.create_index()
    else:
        logger.info("OpenSearch index already exists")
    
    # Process each item
    indexed_count = 0
    skipped_count = 0
    error_count = 0
    
    for i, item in enumerate(metadata, 1):
        try:
            image_path = item.get('image_path', '')
            short_desc = item.get('short_description', '')
            full_desc = item.get('full_description', '')
            
            if not image_path:
                logger.warning(f"Item {i}/{len(metadata)}: Skipping - missing image_path")
                skipped_count += 1
                continue
            
            # Resolve full path
            if not os.path.isabs(image_path):
                full_image_path = os.path.join(dicom_base_path, image_path)
            else:
                full_image_path = image_path
            
            if not os.path.exists(full_image_path):
                logger.warning(f"Item {i}/{len(metadata)}: Skipping - file not found: {full_image_path}")
                skipped_count += 1
                continue
            
            # Load and embed image
            logger.info(f"Item {i}/{len(metadata)}: Processing {image_path}")
            try:
                image = load_image(full_image_path)
                embedding = embedding_service.embed_image(image)
            except Exception as e:
                logger.error(f"Item {i}/{len(metadata)}: Error processing image: {str(e)}")
                error_count += 1
                continue
            
            # Index document
            try:
                opensearch_client.index_document(
                    embedding=embedding.tolist(),
                    image_path=image_path,
                    short_description=short_desc,
                    full_description=full_desc
                )
                indexed_count += 1
                logger.info(f"Item {i}/{len(metadata)}: Successfully indexed")
            except Exception as e:
                logger.error(f"Item {i}/{len(metadata)}: Error indexing: {str(e)}")
                error_count += 1
                continue
            
        except Exception as e:
            logger.error(f"Item {i}/{len(metadata)}: Unexpected error: {str(e)}")
            error_count += 1
            continue
    
    # Summary
    logger.info("=" * 50)
    logger.info("Indexing Summary:")
    logger.info(f"  Total items: {len(metadata)}")
    logger.info(f"  Successfully indexed: {indexed_count}")
    logger.info(f"  Skipped: {skipped_count}")
    logger.info(f"  Errors: {error_count}")
    logger.info("=" * 50)
    
    # Verify final count
    final_count = opensearch_client.get_document_count()
    logger.info(f"Total documents in index: {final_count}")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Index DICOM files from JSON metadata")
    parser.add_argument(
        "json_path",
        nargs="?",
        help="Path to JSON metadata file (default: from config)"
    )
    parser.add_argument(
        "dicom_base_path",
        nargs="?",
        help="Base path for DICOM files (default: from config)"
    )
    
    args = parser.parse_args()
    
    index_from_json(args.json_path, args.dicom_base_path)

