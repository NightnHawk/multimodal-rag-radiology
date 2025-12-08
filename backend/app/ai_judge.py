"""AI-as-Judge for quality validation of generated descriptions."""
from openai import OpenAI
from typing import Dict, Any
import logging
from app.config import settings

logger = logging.getLogger(__name__)


class AIJudge:
    """AI-as-Judge for evaluating description quality."""
    
    def __init__(self):
        """Initialize AI Judge."""
        self.client = OpenAI(api_key=settings.openai_api_key)
        self.model = "gpt-4o"
    
    def evaluate_quality(
        self,
        generated_description: str,
        input_type: str = "dicom",
        retrieved_documents: list = None
    ) -> Dict[str, Any]:
        """
        Evaluate the quality of a generated description.
        
        Args:
            generated_description: The generated description to evaluate
            input_type: Type of input ("dicom", "png", "jpg")
            retrieved_documents: Optional list of retrieved reference documents
            
        Returns:
            Dictionary with quality_score (0-1), approved (bool), and feedback (str)
        """
        try:
            # Build evaluation prompt
            evaluation_prompt = self._build_evaluation_prompt(
                generated_description,
                retrieved_documents
            )
            
            # Call GPT-4o for evaluation
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert evaluator of medical imaging descriptions. Evaluate descriptions for accuracy, completeness, medical correctness, and clarity. Provide a score from 0.0 to 1.0 and a brief justification."
                    },
                    {
                        "role": "user",
                        "content": evaluation_prompt
                    }
                ],
                max_tokens=500,
                temperature=0.3  # Lower temperature for more consistent evaluation
            )
            
            evaluation_text = response.choices[0].message.content
            
            # Parse the response to extract score and decision
            result = self._parse_evaluation(evaluation_text)
            
            logger.info(f"AI Judge evaluation: score={result['quality_score']}, approved={result['approved']}")
            return result
            
        except Exception as e:
            logger.error(f"Error in AI Judge evaluation: {str(e)}")
            # Default to approved if evaluation fails
            return {
                "quality_score": 0.5,
                "approved": True,
                "feedback": f"Evaluation error: {str(e)}. Defaulting to approved."
            }
    
    def _build_evaluation_prompt(
        self,
        generated_description: str,
        retrieved_documents: list = None
    ) -> str:
        """
        Build prompt for quality evaluation.
        
        Args:
            generated_description: The description to evaluate
            retrieved_documents: Optional retrieved reference documents
            
        Returns:
            Evaluation prompt string
        """
        prompt = f"""Evaluate the quality of the following RTG scan description:

DESCRIPTION TO EVALUATE:
{generated_description}

"""
        
        if retrieved_documents:
            prompt += "REFERENCE CONTEXT (for comparison):\n"
            for i, doc in enumerate(retrieved_documents[:3], 1):  # Use top 3 for context
                prompt += f"""
Reference {i}:
- Short: {doc.get('short_description', 'N/A')}
- Full: {doc.get('full_description', 'N/A')}
"""
            prompt += "\n"
        
        prompt += """EVALUATION CRITERIA:
1. Medical Accuracy: Is the description medically accurate and appropriate?
2. Completeness: Does it cover key findings and observations?
3. Clarity: Is it well-structured and easy to understand?
4. Relevance: Does it appropriately reference the image content?
5. Professionalism: Is the language appropriate for medical documentation?

Please provide:
1. A quality score from 0.0 to 1.0 (where 1.0 is excellent)
2. A decision: "APPROVED" if score >= 0.7, "REJECTED" if score < 0.7
3. Brief feedback explaining the score and any issues

Format your response as:
SCORE: [0.0-1.0]
DECISION: [APPROVED/REJECTED]
FEEDBACK: [your feedback here]"""
        
        return prompt
    
    def _parse_evaluation(self, evaluation_text: str) -> Dict[str, Any]:
        """
        Parse AI Judge evaluation response.
        
        Args:
            evaluation_text: Raw evaluation text from GPT
            
        Returns:
            Dictionary with quality_score, approved, and feedback
        """
        try:
            # Default values
            quality_score = 0.5
            approved = True
            feedback = evaluation_text
            
            # Try to extract score
            lines = evaluation_text.split('\n')
            for line in lines:
                line_upper = line.upper()
                if 'SCORE:' in line_upper:
                    try:
                        # Extract number from line
                        import re
                        score_match = re.search(r'(\d+\.?\d*)', line)
                        if score_match:
                            quality_score = float(score_match.group(1))
                            # Ensure score is between 0 and 1
                            if quality_score > 1.0:
                                quality_score = quality_score / 100.0
                            quality_score = max(0.0, min(1.0, quality_score))
                    except:
                        pass
                
                if 'DECISION:' in line_upper:
                    if 'REJECTED' in line_upper:
                        approved = False
                    elif 'APPROVED' in line_upper:
                        approved = True
            
            # Override decision based on score if not explicitly found
            if quality_score < 0.7:
                approved = False
            elif quality_score >= 0.7:
                approved = True
            
            return {
                "quality_score": quality_score,
                "approved": approved,
                "feedback": feedback
            }
            
        except Exception as e:
            logger.warning(f"Error parsing evaluation: {str(e)}")
            return {
                "quality_score": 0.5,
                "approved": True,
                "feedback": evaluation_text
            }


# Global AI Judge instance
_ai_judge: AIJudge = None


def get_ai_judge() -> AIJudge:
    """
    Get or create the global AI Judge instance.
    
    Returns:
        AIJudge instance
    """
    global _ai_judge
    if _ai_judge is None:
        _ai_judge = AIJudge()
    return _ai_judge

