# Audio Processing Prototype

This is an HTTP Server for audio processing API built with FastAPI.

## Getting Started

### Features

- Upload and manage audio files with metadata (title, artist, description, tags, file size, timestamps)
- Tag-based file organization and filtering
- Individual file operations (download, delete, info)
- Bulk download as ZIP with metadata

### Prerequisites
- Python 3.12
- Docker

### Project Structure

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
├── requirements.txt     # Production dependencies
└── docker/
    ├── Dockerfile
    └── docker-compose.yaml
```

### Quick build and Start with Docker
```bash
git clone https://github.com/bsababu/HTTP-Server-for-audio-processing.git
cd audio-api
docker compose -f docker/docker-compose.yaml -p audio-api up -d --build
```
API will be available at http://localhost:5001

### Local Development Setup
```bash
# Clone repository
git clone https://github.com/bsababu/HTTP-Server-for-audio-processing.git
cd audio-api

# Create virtual environment
python -m venv .venv
source ../.venv/bin/activate  # this is on macOS/Linux, you can use `.venv\Scripts\activate` on Windows
pip install -r requirements.txt # install dependencies

# Run server
python -m uvicorn app.main:app --reload --port 5000
```

### API Documentation
Interactive API documentation: http://127.0.0.1:5000/docs

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

## CI/CD with GitHub workflows
The CI-CD can be found in .github/workflows/ci.yml

- **Test**: Runs pytest on Python 3.12
- **Docker**: Builds and tests Docker containers
- **Integration**: End-to-end API testing

