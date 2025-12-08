# RAG Workflow Application with OpenSearch

A complete RAG (Retrieval-Augmented Generation) workflow application for medical RTG (X-ray) scans using OpenSearch for vector storage and GPT-4o for generation.

## Features

- **DICOM Processing**: Extract images from DICOM files
- **Embedding Generation**: Use CLIP model trained specifically on RTG scans
- **Vector Search**: OpenSearch with k-NN for similarity search
- **RAG Pipeline**: Retrieve similar scans and generate descriptions using GPT-4o
- **AI-as-Judge**: Quality validation of generated descriptions
- **Web Interface**: User-friendly web UI for querying and visualization
- **Local Application**: Option to run as local desktop application

## Prerequisites

- Python 3.9+
- Docker and Docker Compose
- OpenAI API key
- DICOM files and JSON metadata file

## Setup Instructions

### 1. Clone and Navigate

```bash
cd masters
```

### 2. Set Up Environment Variables

```bash
cd backend
cp .env.example .env
```

Edit `.env` and fill in:
- `OPENAI_API_KEY`: Your OpenAI API key
- `OPENSEARCH_HOST`: OpenSearch host (default: localhost)
- `OPENSEARCH_PORT`: OpenSearch port (default: 9200)
- `DICOM_DATA_PATH`: Path to your DICOM files folder
- `JSON_METADATA_PATH`: Path to your JSON metadata file

### 3. Start OpenSearch

```bash
cd ../docker
docker-compose up -d
```

Wait for OpenSearch to be ready (check logs: `docker-compose logs -f`)

### 4. Install Python Dependencies

```bash
cd ../backend
pip install -r requirements.txt
```

### 5. Index Your Data

Place your DICOM files in the `data/` folder and ensure your JSON metadata file is at the specified path.

The JSON file should have the following structure:
```json
[
  {
    "image_path": "path/to/file1.dcm",
    "short_description": "Brief description",
    "full_description": "Detailed description"
  },
  ...
]
```

Run the indexing script:
```bash
python scripts/index_data.py
```

### 6. Start the Backend API

```bash
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at `http://localhost:8000`

### 7. Open the Web Interface

Open `frontend/web/index.html` in your web browser, or serve it using a local web server:

```bash
cd frontend/web
python -m http.server 8080
```

Then navigate to `http://localhost:8080`

## API Endpoints

### Health Check
- `GET /health` - Check API health
- `GET /opensearch/status` - Check OpenSearch connection

### Indexing
- `POST /index/batch` - Index DICOM files from folder (uses JSON metadata)

### Querying
- `POST /query` - Query with DICOM/image file
  - Body: multipart/form-data with `file` field
  - Returns: Generated description and retrieved similar scans
- `POST /query/regenerate` - Regenerate answer for a query
  - Body: JSON with `query_id` and `file` (optional)

## Project Structure

```
masters/
├── backend/
│   ├── app/              # Application code
│   ├── requirements.txt  # Python dependencies
│   └── .env.example      # Environment template
├── frontend/
│   ├── web/              # Web interface
│   └── local/            # Local app instructions
├── docker/
│   └── docker-compose.yml # OpenSearch setup
├── scripts/
│   └── index_data.py     # Batch indexing script
└── data/                 # Your DICOM files and JSON
```

## Usage

1. **Index Data**: Run `scripts/index_data.py` to index all DICOM files
2. **Query**: Upload a DICOM or image file through the web interface
3. **Review**: Check the generated description and similar scans
4. **Regenerate**: If quality is low, use the regenerate button

## Local Application

See `frontend/local/README.md` for instructions on running as a local desktop application.

## Troubleshooting

- **OpenSearch connection errors**: Ensure Docker container is running (`docker ps`)
- **Model download issues**: The CLIP model will download on first use (may take time)
- **API key errors**: Verify your OpenAI API key in `.env`
- **DICOM reading errors**: Ensure DICOM files are valid and accessible

## License

MIT

