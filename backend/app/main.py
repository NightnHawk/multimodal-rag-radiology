"""FastAPI application with endpoints for RAG workflow."""
from fastapi import FastAPI, File, UploadFile, HTTPException, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging
import json
import os
from typing import Optional

from app.models import (
    QueryResponse,
    HealthResponse,
    OpenSearchStatusResponse,
    IndexRequest
)
from app.rag_pipeline import get_rag_pipeline
from app.opensearch_client import get_opensearch_client
from app.embedding import get_embedding_service
from app.dicom_processor import load_image, load_image_from_bytes
from app.config import settings
import base64
import io

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="RAG Workflow API",
    description="RAG workflow for RTG scans with OpenSearch and GPT-4o",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify actual origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", response_model=HealthResponse)
async def root():
    """Root endpoint."""
    return HealthResponse(
        status="ok",
        message="RAG Workflow API is running"
    )


@app.get("/health", response_model=HealthResponse)
async def health():
    """Health check endpoint."""
    return HealthResponse(
        status="ok",
        message="Service is healthy"
    )


@app.get("/test-prompt")
async def test_prompt():
    """Test endpoint to verify prompt format."""
    try:
        from app.gpt_client import get_gpt_client
        
        gpt_client = get_gpt_client()
        
        # Test with empty documents
        test_docs = []
        prompt = gpt_client._build_prompt(test_docs, "dicom")
        
        # Check if instructions are present
        has_markdown_instruction = "DO NOT USE MARKDOWN" in prompt
        has_cases_instruction = "DO NOT REFER TO THE CASES" in prompt
        
        return {
            "status": "ok",
            "prompt_preview": prompt[:500],
            "prompt_length": len(prompt),
            "has_markdown_instruction": has_markdown_instruction,
            "has_cases_instruction": has_cases_instruction,
            "full_prompt": prompt
        }
    except Exception as e:
        logger.error(f"Error in test-prompt endpoint: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error testing prompt: {str(e)}"
        )


@app.get("/opensearch/status", response_model=OpenSearchStatusResponse)
async def opensearch_status():
    """Check OpenSearch connection and index status."""
    try:
        opensearch_client = get_opensearch_client()
        connected = opensearch_client.client.ping()
        index_exists = opensearch_client.index_exists()
        doc_count = None
        
        if index_exists:
            doc_count = opensearch_client.get_document_count()
        
        return OpenSearchStatusResponse(
            connected=connected,
            index_exists=index_exists,
            document_count=doc_count,
            message="OpenSearch is connected" if connected else "OpenSearch connection failed"
        )
    except Exception as e:
        logger.error(f"Error checking OpenSearch status: {str(e)}")
        return OpenSearchStatusResponse(
            connected=False,
            index_exists=False,
            document_count=None,
            message=f"Error: {str(e)}"
        )


@app.post("/index/batch")
async def index_batch(request: IndexRequest = None):
    """
    Index DICOM files from JSON metadata file.
    
    This endpoint triggers the batch indexing process.
    For actual indexing, use the scripts/index_data.py script.
    """
    try:
        json_path = request.json_path if request else None
        json_path = json_path or settings.json_metadata_path
        
        if not os.path.exists(json_path):
            raise HTTPException(
                status_code=404,
                detail=f"JSON metadata file not found: {json_path}"
            )
        
        # Read JSON file
        with open(json_path, 'r', encoding='utf-8') as f:
            metadata = json.load(f)
        
        if not isinstance(metadata, list):
            raise HTTPException(
                status_code=400,
                detail="JSON file must contain an array of objects"
            )
        
        opensearch_client = get_opensearch_client()
        embedding_service = get_embedding_service()
        
        # Ensure index exists
        if not opensearch_client.index_exists():
            opensearch_client.create_index()
        
        indexed_count = 0
        errors = []
        
        for i, item in enumerate(metadata):
            try:
                image_path = item.get('image_path', '')
                short_desc = item.get('short_description', '')
                full_desc = item.get('full_description', '')
                
                if not image_path:
                    errors.append(f"Item {i}: Missing image_path")
                    continue
                
                # Resolve full path
                if not os.path.isabs(image_path):
                    base_path = request.dicom_folder if request and request.dicom_folder else settings.dicom_data_path
                    full_image_path = os.path.join(base_path, image_path)
                else:
                    full_image_path = image_path
                
                if not os.path.exists(full_image_path):
                    errors.append(f"Item {i}: Image file not found: {full_image_path}")
                    continue
                
                # Load and embed image
                image = load_image(full_image_path)
                embedding = embedding_service.embed_image(image)
                
                # Index document
                opensearch_client.index_document(
                    embedding=embedding.tolist(),
                    image_path=image_path,
                    short_description=short_desc,
                    full_description=full_desc
                )
                
                indexed_count += 1
                logger.info(f"Indexed {indexed_count}/{len(metadata)}: {image_path}")
                
            except Exception as e:
                error_msg = f"Item {i}: {str(e)}"
                errors.append(error_msg)
                logger.error(error_msg)
        
        return {
            "status": "completed",
            "total_items": len(metadata),
            "indexed_count": indexed_count,
            "error_count": len(errors),
            "errors": errors[:10]  # Return first 10 errors
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in batch indexing: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error indexing batch: {str(e)}"
        )


@app.post("/query", response_model=QueryResponse)
async def query(
    file: UploadFile = File(...),
    use_retrieved_images: bool = Form(False),
    clear_context: bool = Form(False)
):
    """
    Query endpoint: Process a DICOM or image file and generate description.
    
    Args:
        file: Uploaded file (DICOM, PNG, or JPG)
        use_retrieved_images: Whether to include retrieved images in GPT prompt
        clear_context: If True, ignore retrieved documents and analyze only the input image
        
    Returns:
        QueryResponse with generated description and retrieved documents
    """
    try:
        # Read file bytes
        file_bytes = await file.read()
        filename = file.filename or "unknown"
        
        # Process through RAG pipeline
        rag_pipeline = get_rag_pipeline()
        result = rag_pipeline.process_query(
            file_bytes,
            filename,
            use_retrieved_images=use_retrieved_images,
            clear_context=clear_context
        )
        
        return QueryResponse(**result)
        
    except Exception as e:
        logger.error(f"Error in query endpoint: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error processing query: {str(e)}"
        )


@app.post("/query/regenerate", response_model=QueryResponse)
async def regenerate_query(
    query_id: str = Form(...),
    file: Optional[UploadFile] = File(None),
    use_same_retrieval: bool = Form(True)
):
    """
    Regenerate answer for a query.
    
    Args:
        query_id: Original query ID
        file: Optional new file (if provided, re-processes)
        use_same_retrieval: Whether to use same retrieval
        
    Returns:
        QueryResponse with regenerated description
    """
    try:
        rag_pipeline = get_rag_pipeline()
        
        file_bytes = None
        filename = None
        
        if file:
            file_bytes = await file.read()
            filename = file.filename or "unknown"
        
        result = rag_pipeline.regenerate_query(
            query_id,
            file_bytes,
            filename,
            use_same_retrieval
        )
        
        return QueryResponse(**result)
        
    except Exception as e:
        logger.error(f"Error in regenerate endpoint: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error regenerating query: {str(e)}"
        )


@app.post("/preview")
async def preview_image(file: UploadFile = File(...)):
    """
    Preview endpoint: Convert DICOM or image file to displayable PNG format.
    
    Args:
        file: Uploaded file (DICOM, PNG, or JPG)
        
    Returns:
        JSON with base64-encoded PNG image
    """
    try:
        # Read file bytes
        file_bytes = await file.read()
        filename = file.filename or "unknown"
        
        # Load image (handles both DICOM and regular images)
        image = load_image_from_bytes(file_bytes, filename)
        
        # Convert to PNG bytes
        buffered = io.BytesIO()
        image.save(buffered, format="PNG")
        img_bytes = buffered.getvalue()
        
        # Encode to base64
        img_base64 = base64.b64encode(img_bytes).decode()
        
        return {
            "image": f"data:image/png;base64,{img_base64}",
            "format": "png"
        }
        
    except Exception as e:
        logger.error(f"Error in preview endpoint: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error generating preview: {str(e)}"
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

