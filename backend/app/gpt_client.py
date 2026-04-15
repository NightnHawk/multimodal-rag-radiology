"""GPT-4o client for generating descriptions."""
from openai import OpenAI
from typing import List, Dict, Any, Optional
import base64
import io
from PIL import Image
import logging
import json
from app.config import settings
from app.models import StructuredDescription

logger = logging.getLogger(__name__)


class GPTClient:
    """Client for OpenAI GPT-4o API."""
    
    def __init__(self):
        """Initialize GPT client."""
        self.client = OpenAI(api_key=settings.openai_api_key)
        self.model = "gpt-4o"
    
    def _build_system_prompt(self, clear_context: bool = False) -> str:
        """
        Build the system prompt to position the model as decision support.
        """
        prompt = (
            "You are an AI assistant for licensed radiologists. Describe observable "
            "radiographic findings in chest X-ray images to assist, not replace, clinician "
            "judgment. Do not provide medical advice, clinical decisions, or definitive "
            "diagnoses. Assume all data are de-identified and the output will be reviewed "
            "by a radiologist. Only say 'Insufficient visual information to describe findings.' "
            "if the image content is actually unreadable (missing/blank/corrupted). Otherwise, "
            "provide the best concise observable description, even if findings are normal. "
            "Do not refuse; stay strictly within observable-image description. End with: "
            "'For clinician review only; not a final medical report.'"
        )
        if clear_context:
            prompt += (
                " This is a new, independent analysis. Do not reference or be influenced "
                "by any previous queries or conversations."
            )
        return prompt

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
        input_type: str = "dicom",
        clear_context: bool = False,
        use_structured_output: bool = True
    ) -> tuple[str, str]:
        """
        Generate description using GPT-4o with vision capabilities.
        
        Args:
            input_image: PIL Image of the input scan
            retrieved_documents: List of retrieved similar documents with descriptions
            input_type: Type of input ("dicom", "png", "jpg")
            clear_context: If True, start a fresh conversation (no influence from previous queries)
            use_structured_output: If True, use structured output format
            
        Returns:
            Tuple of (generated_description, full_prompt)
        """
        try:
            # Convert input image to base64
            input_image_b64 = self._image_to_base64(input_image)
            
            # Build prompt with retrieved documents (always use them, clear_context is about conversation state)
            prompt_text = self._build_prompt(retrieved_documents, input_type)
            logger.debug(f"Built prompt text (length: {len(prompt_text)}): {prompt_text[:300]}...")
            
            # Prepare API call parameters
            system_prompt = self._build_system_prompt(clear_context)
            
            # Build full prompt for return (includes system prompt and user prompt)
            full_prompt = f"System: {system_prompt}\n\nUser: {prompt_text}\n\n[Image: base64 encoded]"
            logger.info(f"Full prompt built (length: {len(full_prompt)})")
            
            # Build content with input image
            content = [
                {
                    "type": "text",
                    "text": prompt_text
                },
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/png;base64,{input_image_b64}"
                    }
                }
            ]
            
            # Log the actual prompt being sent (first 500 chars for debugging)
            logger.info(f"Sending prompt to GPT-4o. User message text preview: {prompt_text[:500]}...")
            logger.debug(f"System prompt: {system_prompt}")
            logger.debug(f"Full prompt text contains 'DO NOT USE MARKDOWN': {'DO NOT USE MARKDOWN' in prompt_text}")
            logger.debug(f"Full prompt text contains 'DO NOT REFER TO THE CASES': {'DO NOT REFER TO THE CASES' in prompt_text}")
            
            api_params = {
                "model": self.model,
                "messages": [
                    {
                        "role": "system",
                        "content": system_prompt
                    },
                    {
                        "role": "user",
                        "content": content
                    }
                ],
                "max_tokens": 2000,
                "temperature": 0.7
            }
            
            # Note: Structured output disabled for this prompt format as it requires specific text format
            # The prompt explicitly requests plain text output in a numbered/bullet format
            
            # Call GPT-4o
            response = self.client.chat.completions.create(**api_params)
            
            # Use plain text response (prompt requires specific text format, not JSON)
            description = response.choices[0].message.content
            logger.info("Generated description successfully")
            logger.debug(f"Prompt used (length: {len(full_prompt) if full_prompt else 0}): {full_prompt[:200] if full_prompt else 'None'}...")
            
            if not full_prompt:
                logger.error("full_prompt is empty or None!")
                full_prompt = f"System: {system_prompt}\n\nUser: {prompt_text}\n\n[Image: base64 encoded]"
            
            return description, full_prompt
            
        except json.JSONDecodeError as e:
            logger.error(f"Error parsing structured JSON response: {str(e)}")
            # Fallback to plain text if structured parsing fails
            logger.warning("Falling back to plain text generation")
            description, full_prompt = self._generate_plain_text_fallback(input_image, retrieved_documents, input_type)
            return description, full_prompt
        except Exception as e:
            logger.error(f"Error generating description with GPT-4o: {str(e)}")
            # Try to return prompt even on error if it was built
            try:
                prompt_text = self._build_prompt(retrieved_documents, input_type)
                system_prompt = self._build_system_prompt(clear_context)
                full_prompt = f"System: {system_prompt}\n\nUser: {prompt_text}\n\n[Image: base64 encoded]"
                raise  # Re-raise the original exception
            except:
                raise  # Re-raise if prompt building also fails
    
    def _generate_plain_text_fallback(
        self,
        input_image: Image.Image,
        retrieved_documents: List[Dict[str, Any]],
        input_type: str
    ) -> tuple[str, str]:
        """Fallback method for plain text generation if structured output fails."""
        input_image_b64 = self._image_to_base64(input_image)
        prompt_text = self._build_prompt(retrieved_documents, input_type)
        
        content = [
            {"type": "text", "text": prompt_text},
            {
                "type": "image_url",
                "image_url": {"url": f"data:image/png;base64,{input_image_b64}"}
            }
        ]
        
        system_prompt = self._build_system_prompt()
        full_prompt = f"System: {system_prompt}\n\nUser: {prompt_text}\n\n[Image: base64 encoded]"
        
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": system_prompt
                },
                {"role": "user", "content": content}
            ],
            max_tokens=2000,
            temperature=0.7
        )
        
        return response.choices[0].message.content, full_prompt
    
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
        prompt = """You are assisting licensed radiologists. Describe observable radiographic findings only; do not provide diagnoses, clinical decisions, or treatment advice. Use "Insufficient visual information to describe findings." only if the image is unreadable (missing/blank/corrupted). Otherwise, provide the best concise observable description, even if findings are normal. Generate a structured report using ONLY the specific numbered or bullet-point format shown in the examples below. Do not add extra commentary, explanations, or unstructured text.

IMPORTANT INSTRUCTIONS:
- DO NOT USE MARKDOWN format, only use plain text.
- DO NOT REFER TO THE CASES IN THIS PROMPT, only use them to formulate a new description.

"""
        
        if retrieved_documents:
            prompt += f"Retrieved similar chest X-rays for reference ({len(retrieved_documents)} documents):\n\n"
            
            for i, doc in enumerate(retrieved_documents, 1):
                prompt += f"""[Document {i}]
Image: {doc.get('image_path', 'N/A')}
Short description: {doc.get('short_description', 'N/A')}
Full description: {doc.get('full_description', 'N/A')}

"""
        
        prompt += """New chest X-ray to analyze:
[Upload the new image here]

EXACT FORMAT REQUIREMENTS - Follow these examples precisely:

Example 1:
"1. Chest X-ray, PA and lateral projection. 2. Lung fields without distinct infiltrative changes, with minor scar-fibrotic changes. 3. Hilum shadows on both sides are not enlarged. 4. Heart silhouette is not enlarged. 5. Atherosclerotic aorta, not enlarged in the arch. 6. Diaphragm domes are clear. 7. Costophrenic angles and posterior recesses are clear. 8. Degenerative changes in the thoracic spine. 9. Shadow of internal stabilization of the upper segment of the visible section of the spine."

Example 2:
"Chest X-ray, PA and lateral projection. Lung fields without infiltrative changes. Hilar shadows on both sides are not enlarged. Heart silhouette is not enlarged. Aorta is not enlarged in the arch. Diaphragm domes are clear. Costophrenic angles and posterior recesses are clear. Degenerative and productive changes in the thoracic spine."

Example 3:
"Chest X-ray in PA projection. Lung fields without infiltrative changes. Hilar shadows on both sides are not enlarged. Heart silhouette is not enlarged. Aorta is not enlarged in the arch. Diaphragm domes are clear. Costophrenic angles are clear. Status post pacemaker implantation. The chamber projects onto the left middle lung field."

Key elements to always include in order:

Projection type (PA, lateral, etc.)

Lung fields status

Hilum/hilar shadows

Heart silhouette

Aorta/arch status

Diaphragm domes

Costophrenic angles/posterior recesses

Spine/bone changes

Any devices/interventions/unique findings

Use concise medical terminology matching the example style. Number items if multiple findings, or use period-separated sentences if brief normal findings.

Output ONLY the formatted report - nothing else."""
        
        return prompt
    
    def generate_with_retrieved_images(
        self,
        input_image: Image.Image,
        retrieved_documents: List[Dict[str, Any]],
        retrieved_images: List[Image.Image],
        clear_context: bool = False,
        use_structured_output: bool = True
    ) -> tuple[str, str]:
        """
        Generate description with both input and retrieved images visible to the model.
        
        Args:
            input_image: PIL Image of the input scan
            retrieved_documents: List of retrieved documents with descriptions
            retrieved_images: List of PIL Images from retrieved documents
            clear_context: If True, start a fresh conversation (no influence from previous queries)
            use_structured_output: If True, use structured output format
            
        Returns:
            Tuple of (generated_description, full_prompt)
        """
        try:
            # Build prompt text
            prompt_text = self._build_prompt_with_images(retrieved_documents)
            logger.debug(f"Built prompt with images (length: {len(prompt_text)}): {prompt_text[:300]}...")
            
            # Prepare API call parameters
            system_prompt = self._build_system_prompt(clear_context)
            
            # Build full prompt for return (includes system prompt and user prompt)
            full_prompt = f"System: {system_prompt}\n\nUser: {prompt_text}\n\n[Images: {len(retrieved_images) + 1} images - input image + {len(retrieved_images)} reference images, all base64 encoded]"
            logger.info(f"Full prompt with images built (length: {len(full_prompt)})")
            
            # Build content with multiple images (always include retrieved images if provided)
            content = [
                {
                    "type": "text",
                    "text": prompt_text
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
            
            # Log the actual prompt being sent (first 500 chars for debugging)
            logger.info(f"Sending prompt with images to GPT-4o. User message text preview: {prompt_text[:500]}...")
            logger.debug(f"System prompt: {system_prompt}")
            logger.debug(f"Full prompt text contains 'DO NOT USE MARKDOWN': {'DO NOT USE MARKDOWN' in prompt_text}")
            logger.debug(f"Full prompt text contains 'DO NOT REFER TO THE CASES': {'DO NOT REFER TO THE CASES' in prompt_text}")
            
            api_params = {
                "model": self.model,
                "messages": [
                    {
                        "role": "system",
                        "content": system_prompt
                    },
                    {
                        "role": "user",
                        "content": content
                    }
                ],
                "max_tokens": 2000,
                "temperature": 0.7
            }
            
            # Note: Structured output disabled for this prompt format as it requires specific text format
            # The prompt explicitly requests plain text output in a numbered/bullet format
            
            # Call GPT-4o
            response = self.client.chat.completions.create(**api_params)
            
            # Use plain text response (prompt requires specific text format, not JSON)
            description = response.choices[0].message.content
            logger.info("Generated description with retrieved images successfully")
            logger.debug(f"Prompt used (length: {len(full_prompt) if full_prompt else 0}): {full_prompt[:200] if full_prompt else 'None'}...")
            
            if not full_prompt:
                logger.error("full_prompt is empty or None!")
                full_prompt = f"System: {system_prompt}\n\nUser: {prompt_text}\n\n[Images: {len(retrieved_images) + 1} images - input image + {len(retrieved_images)} reference images, all base64 encoded]"
            
            return description, full_prompt
            
        except json.JSONDecodeError as e:
            logger.error(f"Error parsing structured JSON response: {str(e)}")
            # Fallback to plain text
            logger.warning("Falling back to plain text generation")
            return response.choices[0].message.content, full_prompt
        except Exception as e:
            logger.error(f"Error generating description with images: {str(e)}")
            # Try to return prompt even on error if it was built
            try:
                prompt_text = self._build_prompt_with_images(retrieved_documents)
                system_prompt = self._build_system_prompt(clear_context)
                full_prompt = f"System: {system_prompt}\n\nUser: {prompt_text}\n\n[Images: {len(retrieved_images) + 1} images - input image + {len(retrieved_images)} reference images, all base64 encoded]"
                raise  # Re-raise the original exception
            except:
                raise  # Re-raise if prompt building also fails
    
    def _build_prompt_with_images(
        self,
        retrieved_documents: List[Dict[str, Any]]
    ) -> str:
        """Build prompt when images are also provided."""
        prompt = """You are assisting licensed radiologists. Describe observable radiographic findings only; do not provide diagnoses, clinical decisions, or treatment advice. Use "Insufficient visual information to describe findings." only if the image is unreadable (missing/blank/corrupted). Otherwise, provide the best concise observable description, even if findings are normal. Generate a structured report using ONLY the specific numbered or bullet-point format shown in the examples below. Do not add extra commentary, explanations, or unstructured text.

IMPORTANT INSTRUCTIONS:
- DO NOT USE MARKDOWN format, only use plain text.
- DO NOT REFER TO THE CASES IN THIS PROMPT, only use them to formulate a new description.

"""
        
        if retrieved_documents:
            prompt += f"Retrieved similar chest X-rays for reference ({len(retrieved_documents)} documents):\n\n"
            
            for i, doc in enumerate(retrieved_documents, 1):
                prompt += f"""[Document {i}]
Image: {doc.get('image_path', 'N/A')}
Short description: {doc.get('short_description', 'N/A')}
Full description: {doc.get('full_description', 'N/A')}

"""
        
        prompt += """The first image is the new chest X-ray to analyze. The following images are the retrieved similar reference cases.

EXACT FORMAT REQUIREMENTS - Follow these examples precisely:

Example 1:
"1. Chest X-ray, PA and lateral projection. 2. Lung fields without distinct infiltrative changes, with minor scar-fibrotic changes. 3. Hilum shadows on both sides are not enlarged. 4. Heart silhouette is not enlarged. 5. Atherosclerotic aorta, not enlarged in the arch. 6. Diaphragm domes are clear. 7. Costophrenic angles and posterior recesses are clear. 8. Degenerative changes in the thoracic spine. 9. Shadow of internal stabilization of the upper segment of the visible section of the spine."

Example 2:
"Chest X-ray, PA and lateral projection. Lung fields without infiltrative changes. Hilar shadows on both sides are not enlarged. Heart silhouette is not enlarged. Aorta is not enlarged in the arch. Diaphragm domes are clear. Costophrenic angles and posterior recesses are clear. Degenerative and productive changes in the thoracic spine."

Example 3:
"Chest X-ray in PA projection. Lung fields without infiltrative changes. Hilar shadows on both sides are not enlarged. Heart silhouette is not enlarged. Aorta is not enlarged in the arch. Diaphragm domes are clear. Costophrenic angles are clear. Status post pacemaker implantation. The chamber projects onto the left middle lung field."

Key elements to always include in order:

Projection type (PA, lateral, etc.)

Lung fields status

Hilum/hilar shadows

Heart silhouette

Aorta/arch status

Diaphragm domes

Costophrenic angles/posterior recesses

Spine/bone changes

Any devices/interventions/unique findings

Use concise medical terminology matching the example style. Number items if multiple findings, or use period-separated sentences if brief normal findings.

Output ONLY the formatted report - nothing else.
"""
        
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

