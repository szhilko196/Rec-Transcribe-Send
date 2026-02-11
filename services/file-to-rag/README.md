# FileToRag Service

Monitors `data/FileToRag/` folder for `.md` files, chunks them intelligently, and uploads to OpenWebUI Knowledge Base for RAG search.

## Features

- **Automatic file monitoring**: Watches folder for new markdown files
- **Intelligent chunking**: Splits by H2 headers (preserving context) or by lines
- **Duplicate detection**: Tracks processed files by hash to avoid re-uploads
- **Retry logic**: Exponential backoff for failed uploads
- **Startup scan**: Processes existing files on startup

## Quick Start

1. **Start OpenWebUI** (if not running):
   ```bash
   cd services/OpenWebUi
   docker-compose up -d
   ```

2. **Get API key** from OpenWebUI:
   - Open http://localhost:3000
   - Go to Settings > Account > API Keys
   - Create new key and copy it

3. **Configure the service**:
   ```bash
   cd services/file-to-rag
   copy config\.env.example .env
   # Edit .env and set OPENWEBUI_API_KEY
   ```

4. **Run the service**:
   ```bash
   # From project root:
   start_file-to-rag.bat

   # Or manually:
   cd services/file-to-rag
   python -m venv venv
   venv\Scripts\activate
   pip install -r requirements.txt
   python -m src.main
   ```

5. **Test it**:
   - Copy any `.md` file to `data/FileToRag/`
   - Watch the logs for chunking and upload progress
   - In OpenWebUI chat, type `#MyFiles` to see the Knowledge Base

## Configuration

Edit `.env` or set environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `OPENWEBUI_URL` | `http://localhost:3000` | OpenWebUI server URL |
| `OPENWEBUI_API_KEY` | (required) | API key from OpenWebUI |
| `FILETORAG_KB_NAME` | `MyFiles` | Knowledge Base name |
| `FILETORAG_WATCH_FOLDER` | `data/FileToRag` | Folder to monitor |
| `FILETORAG_CHUNK_BY_HEADERS` | `true` | Split by ## headers |
| `FILETORAG_CHUNK_SIZE_LINES` | `150` | Max lines per chunk |
| `FILETORAG_PARALLEL_UPLOADS` | `4` | Parallel upload workers |
| `FILETORAG_LOG_LEVEL` | `INFO` | Logging level |

## Chunking Strategies

### By Headers (default)

Splits on `## ` (H2) headers, keeping each section with its header:

```markdown
## Introduction       --> Chunk 1
Content here...

## Methods            --> Chunk 2
Content here...
```

- Small sections (<20 lines) are merged with the next section
- Large sections exceeding `CHUNK_SIZE_LINES` are split further

### By Lines (fallback)

Used for unstructured text without headers:

- Splits every N lines (default: 150)
- Each chunk gets a metadata comment

### Metadata

Each chunk includes a metadata comment:

```markdown
<!-- File: document.md | Chunk: 1/5 -->

## Introduction
...
```

## File Structure

```
services/file-to-rag/
├── src/
│   ├── __init__.py
│   ├── main.py              # Entry point and monitoring
│   ├── config.py            # Configuration loading
│   ├── markdown_chunker.py  # Chunking logic
│   ├── openwebui_client.py  # OpenWebUI API client
│   └── rag_uploader.py      # Upload to KB
├── config/
│   └── .env.example         # Config template
├── data/
│   └── processed_files.json # Tracking database
├── requirements.txt
└── README.md

data/FileToRag/              # Watch folder
```

## Processed Files Database

Tracks processed files in `data/processed_files.json`:

```json
{
  "abc123...": {
    "file_name": "document.md",
    "file_hash": "abc123...",
    "processed_at": "2025-02-04T10:30:00",
    "status": "success",
    "file_ids": ["file-1", "file-2"]
  }
}
```

- Uses SHA256 hash to detect duplicate content
- Skips files that have already been processed
- Failed files can be reprocessed by removing from database

## Usage in OpenWebUI

After files are uploaded, use the Knowledge Base in chat:

```
#MyFiles What is the main topic of my documents?
```

Or select "MyFiles" from the Knowledge Base selector in the chat interface.

## Performance

The service uploads chunks in parallel to maximize GPU utilization during embedding generation.

**Parallel workers** (`FILETORAG_PARALLEL_UPLOADS`):
- Default: 4 workers
- Higher values = faster upload, but more GPU/API load
- Recommended: 4-8 for most setups
- If you have a powerful GPU, try increasing to 8-10

**Example**: 90 chunks with 4 workers ≈ 2-3 minutes (vs 10+ minutes sequential)

## Troubleshooting

### "Cannot connect to OpenWebUI"
- Ensure OpenWebUI is running: `docker-compose ps` in `services/OpenWebUi`
- Check the URL in `.env`

### "OPENWEBUI_API_KEY is not set"
- Get key from OpenWebUI: Settings > Account > API Keys
- Set it in `.env`

### File not being processed
- Check if it's a `.md` file
- Check `data/processed_files.json` - file may already be processed
- Delete entry from database to reprocess

### Upload failures
- Check OpenWebUI logs: `docker-compose logs -f open-webui`
- Increase `FILETORAG_LOG_LEVEL=DEBUG` for more details
