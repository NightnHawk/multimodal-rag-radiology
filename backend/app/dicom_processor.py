"""DICOM file processing utilities."""
import pydicom
from PIL import Image
import numpy as np
from typing import Union
import io
import logging

logger = logging.getLogger(__name__)


def extract_image_from_dicom(dicom_path: str) -> Image.Image:
    """
    Extract image from DICOM file and convert to PIL Image.
    
    Args:
        dicom_path: Path to the DICOM file
        
    Returns:
        PIL Image object
        
    Raises:
        Exception: If DICOM file cannot be read or processed
    """
    try:
        # Read DICOM file
        dicom_data = pydicom.dcmread(dicom_path)
        
        # Get pixel array
        pixel_array = dicom_data.pixel_array
        
        # Normalize pixel values to 0-255 range
        if pixel_array.max() > 255:
            # Handle 16-bit images
            pixel_array = ((pixel_array - pixel_array.min()) / 
                          (pixel_array.max() - pixel_array.min()) * 255).astype(np.uint8)
        else:
            pixel_array = pixel_array.astype(np.uint8)
        
        # Convert to PIL Image
        image = Image.fromarray(pixel_array)
        
        # Convert to RGB if needed (CLIP models typically expect RGB)
        if image.mode != 'RGB':
            image = image.convert('RGB')
            
        return image
        
    except Exception as e:
        logger.error(f"Error processing DICOM file {dicom_path}: {str(e)}")
        raise


def load_image(file_path: str) -> Image.Image:
    """
    Load image from file (supports DICOM, PNG, JPG).
    
    Args:
        file_path: Path to the image file
        
    Returns:
        PIL Image object
    """
    file_path_lower = file_path.lower()
    
    if file_path_lower.endswith(('.dcm', '.dicom')):
        return extract_image_from_dicom(file_path)
    elif file_path_lower.endswith(('.png', '.jpg', '.jpeg')):
        return Image.open(file_path)
    else:
        raise ValueError(f"Unsupported file format: {file_path}")


def load_image_from_bytes(file_bytes: bytes, filename: str) -> Image.Image:
    """
    Load image from bytes (for uploaded files).
    
    Args:
        file_bytes: Image file as bytes
        filename: Original filename (for format detection)
        
    Returns:
        PIL Image object
    """
    filename_lower = filename.lower()
    
    if filename_lower.endswith(('.dcm', '.dicom')):
        # Read DICOM from bytes
        dicom_data = pydicom.dcmread(io.BytesIO(file_bytes))
        pixel_array = dicom_data.pixel_array
        
        # Normalize and convert
        if pixel_array.max() > 255:
            pixel_array = ((pixel_array - pixel_array.min()) / 
                          (pixel_array.max() - pixel_array.min()) * 255).astype(np.uint8)
        else:
            pixel_array = pixel_array.astype(np.uint8)
        
        image = Image.fromarray(pixel_array)
        if image.mode != 'RGB':
            image = image.convert('RGB')
        return image
    else:
        # Regular image format
        return Image.open(io.BytesIO(file_bytes))

