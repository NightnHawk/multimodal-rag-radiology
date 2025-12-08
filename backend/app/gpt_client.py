"""GPT-4o client for generating descriptions."""
from openai import OpenAI
from typing import List, Dict, Any, Optional
import base64
import io
from PIL import Image
import logging
from app.config import settings

logger = logging.getLogger(__name__)


class GPTClient:
    """Client for OpenAI GPT-4o API."""
    
    def __init__(self):
        """Initialize GPT client."""
        self.client = OpenAI(api_key=settings.openai_api_key)
        self.model = "gpt-4o"
    
    def _image_to_base64(self, image: Image.Image) -> str:
        """
        Convert PIL Image to base64 string.
        
        Args:
            image: PIL Image object
            
        Returns:
            Base64 encoded string
        """
        buffered = io.BytesIO()
        image.save(buffered, format="PNG")
        img_str = base64.b64encode(buffered.getvalue()).decode()
        return img_str
    
    def generate_description(
        self,
        input_image: Image.Image,
        retrieved_documents: List[Dict[str, Any]],
        input_type: str = "dicom"
    ) -> str:
        """
        Generate description using GPT-4o with vision capabilities.
        
        Args:
            input_image: PIL Image of the input scan
            retrieved_documents: List of retrieved similar documents with descriptions
            input_type: Type of input ("dicom", "png", "jpg")
            
        Returns:
            Generated description
        """
        try:
            # Convert input image to base64
            input_image_b64 = self._image_to_base64(input_image)
            
            # Build content with input image and retrieved context
            content = [
                {
                    "type": "text",
                    "text": self._build_prompt(retrieved_documents, input_type)
                },
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/png;base64,{input_image_b64}"
                    }
                }
            ]
            
            # Call GPT-4o
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a medical imaging expert specializing in RTG (X-ray) scan analysis. Provide detailed, accurate descriptions of medical images based on the input scan and similar reference cases."
                    },
                    {
                        "role": "user",
                        "content": content
                    }
                ],
                max_tokens=1000,
                temperature=0.7
            )
            
            description = response.choices[0].message.content
            logger.info("Generated description successfully")
            return description
            
        except Exception as e:
            logger.error(f"Error generating description with GPT-4o: {str(e)}")
            raise
    
    def _build_prompt(
        self,
        retrieved_documents: List[Dict[str, Any]],
        input_type: str
    ) -> str:
        """
        Build prompt for GPT-4o with retrieved context.
        
        Args:
            retrieved_documents: List of retrieved documents
            input_type: Type of input image
            
        Returns:
            Formatted prompt string
        """
        prompt = f"""Analyze the provided RTG (X-ray) scan image. Below are {len(retrieved_documents)} similar reference cases with their descriptions for cross-reference:

"""
        
        for i, doc in enumerate(retrieved_documents, 1):
            prompt += f"""Reference Case {i}:
- Short Description: {doc.get('short_description', 'N/A')}
- Full Description: {doc.get('full_description', 'N/A')}
- Similarity Score: {doc.get('score', 0):.4f}

"""
        
        prompt += """Based on the input image and the reference cases above, provide a comprehensive description of the RTG scan. Include:
1. Overall assessment
2. Key findings
3. Notable features or abnormalities (if any)
4. Comparison with reference cases (if relevant)

Format your response as a clear, professional medical description."""
        
        return prompt
    
    def generate_with_retrieved_images(
        self,
        input_image: Image.Image,
        retrieved_documents: List[Dict[str, Any]],
        retrieved_images: List[Image.Image]
    ) -> str:
        """
        Generate description with both input and retrieved images visible to the model.
        
        Args:
            input_image: PIL Image of the input scan
            retrieved_documents: List of retrieved documents with descriptions
            retrieved_images: List of PIL Images from retrieved documents
            
        Returns:
            Generated description
        """
        try:
            # Build content with multiple images
            content = [
                {
                    "type": "text",
                    "text": self._build_prompt_with_images(retrieved_documents)
                },
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/png;base64,{self._image_to_base64(input_image)}"
                    }
                }
            ]
            
            # Add retrieved images
            for img in retrieved_images:
                content.append({
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/png;base64,{self._image_to_base64(img)}"
                    }
                })
            
            # Call GPT-4o
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a medical imaging expert specializing in RTG (X-ray) scan analysis. Analyze the input image and compare it with the provided reference images and their descriptions."
                    },
                    {
                        "role": "user",
                        "content": content
                    }
                ],
                max_tokens=1000,
                temperature=0.7
            )
            
            description = response.choices[0].message.content
            logger.info("Generated description with retrieved images successfully")
            return description
            
        except Exception as e:
            logger.error(f"Error generating description with images: {str(e)}")
            raise
    
    def _build_prompt_with_images(
        self,
        retrieved_documents: List[Dict[str, Any]]
    ) -> str:
        """Build prompt when images are also provided."""
        prompt = f"""Analyze the first RTG (X-ray) scan image (the input query). The following images are similar reference cases with their descriptions:

"""
        
        for i, doc in enumerate(retrieved_documents, 1):
            prompt += f"""Reference Case {i}:
- Short Description: {doc.get('short_description', 'N/A')}
- Full Description: {doc.get('full_description', 'N/A')}
- Similarity Score: {doc.get('score', 0):.4f}

"""
        
        prompt += """Compare the input image with the reference cases and provide a comprehensive description including findings, abnormalities, and relevant comparisons."""
        
        return prompt


# Global GPT client instance
_gpt_client: GPTClient = None


def get_gpt_client() -> GPTClient:
    """
    Get or create the global GPT client instance.
    
    Returns:
        GPTClient instance
    """
    global _gpt_client
    if _gpt_client is None:
        _gpt_client = GPTClient()
    return _gpt_client

