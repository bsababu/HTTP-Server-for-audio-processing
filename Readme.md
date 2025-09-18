# Audio Processing Prototype

This is an HTTP Server for audio processing API built with FastAPI.

### Features

- Upload and manage audio files with metadata (title, artist, description, tags, file size, timestamps)
- Tag-based file organization and filtering
- Individual file operations (download, delete, info)
- Bulk download as ZIP with metadata

## Getting Started

### Prerequisites
- Python 3.12
- Docker

## Project Structure

```
audio-api/
├── app/
│   ├── main.py          # FastAPI application
│   ├── storage.py       # File storage logic
│   └── schema.py        # models
├── tests/
│   └── test_main.py     # Test suite
├── .github/workflows/
│   └── ci.yml          # CI/CD pipeline
├── requirements.txt     # dependencies
├── Dockerfile
└── docker-compose.yaml
```

### Quick Start with Docker
```bash
git clone <repository-url>
cd audio-api
docker-compose up -d
```
API will be available at http://localhost:5000

### Local Development Setup
```bash
# Clone repository
git clone <repository-url>
cd audio-api

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # this is on macOS/Linux, you can use `.venv\Scripts\activate` on Windows
# Install dependencies
pip install -r requirements-dev.txt

# Run server
python -m uvicorn app.main:app --reload --port 5000
```

### API Documentation
Interactive API docs: http://localhost:5000/docs

## API Endpoints

- `POST /upload` - Upload audio files with metadata (in form-data)
- `GET /list` - List user files with optional tag filtering
- `GET /download` - Download all user files as ZIP (with -0 compression)
- `GET /files/{file_id}` - Download individual file
- `GET /files/{file_id}/info` - Get file metadata
- `GET /health` - Health check

## Development

### Testing
```bash
# Run all tests
pytest tests/ -v

# Run specific test
pytest tests/test_main.py::test_health -v
```

## CI/CD with github workflows
the ci-cd can be found in .github/workflows/ci.yml

- **Test**: Runs pytest on Python 3.12
- **Docker**: Builds and tests Docker container
- **Integration**: End-to-end API testing

