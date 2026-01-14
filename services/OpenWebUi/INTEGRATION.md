# OpenWebUI Integration Guide

Technical guide for integrating OpenWebUI RAG into the meeting transcription pipeline.

## Integration Points

### 1. Orchestrator Integration

**File**: `services/transcription_orchestrator/orchestrator.py`

**Configuration** (lines ~68-71):
```python
ENABLE_OPENWEBUI_RAG = os.getenv("ENABLE_OPENWEBUI_RAG", "false").lower() == "true"
OPENWEBUI_URL = os.getenv("OPENWEBUI_URL", "http://localhost:3000")
OPENWEBUI_UPLOADER_SCRIPT = SCRIPT_DIR / "OpenWebUi" / "scripts" / "openwebui_uploader.py"
```

**Upload Function** (lines ~1538-1581):
```python
def upload_to_openwebui(result_folder: Path) -> bool:
    """Upload meeting to OpenWebUI Knowledge Base"""
    # Calls openwebui_uploader.py via subprocess
    # Returns True if successful, False otherwise
```

**Pipeline Integration** (lines ~1665-1675):
```python
# Step 4.5: Upload to OpenWebUI (if enabled)
openwebui_rag_indexed = False
if ENABLE_OPENWEBUI_RAG:
    success = upload_to_openwebui(result_folder)
    openwebui_rag_indexed = success
```

**Metadata Tracking** (line ~1707):
```python
result = {
    # ... other fields ...
    "openwebui_rag_indexed": openwebui_rag_indexed
}
```

### 2. Upload Script

**File**: `services/OpenWebUi/scripts/openwebui_uploader.py`

**Main Function**: `upload_meeting_to_openwebui(result_folder: Path) -> bool`

**Steps**:
1. Validate result folder (transcript, summary, protocol files)
2. Check OpenWebUI API accessibility
3. Apply contextual enrichment (if enabled)
4. Get or create shared Knowledge Base ("Meetings")
5. Upload files (transcript, summary, protocol)
6. Update metadata.json with RAG status

### 3. Client Library

**File**: `services/OpenWebUi/scripts/openwebui_client.py`

**Key Methods**:

```python
class OpenWebUIClient:
    def health_check(self) -> bool
        """Check if API is accessible"""

    def upload_file(self, file_path: Path) -> str
        """Upload file, returns file_id"""

    def wait_for_processing(self, file_id: str, timeout: int = 180) -> bool
        """Wait for async embedding generation"""

    def create_knowledge_base(self, name: str, description: str = "") -> str
        """Create KB, returns kb_id"""

    def get_knowledge_base_by_name(self, name: str) -> Optional[Dict]
        """Find KB by name"""

    def add_file_to_knowledge_base(self, knowledge_id: str, file_id: str)
        """Add processed file to KB"""
```

### 4. Contextual Enrichment

**File**: `services/OpenWebUi/scripts/contextual_enrichment.py`

**Reused from RAGFlow implementation** - no OpenWebUI-specific changes needed.

**Process**:
1. Parse meeting metadata (date, speakers, duration)
2. Read transcript, summary, protocol
3. Chunk documents (CHUNK_SIZE=1000)
4. For each chunk, call Claude API to generate context
5. Prepend context: `{context}\n\n{chunk}`
6. Save enriched files to `result_folder/enriched/`

**Claude API Call**:
- Model: `CONTEXT_GENERATION_MODEL` (default: claude-sonnet-4-5-20250929)
- Prompt template: `config/prompts/context_generation.txt`
- ~50-200 chunks per meeting
- ~2-5 minutes total

## API Endpoints Used

### OpenWebUI API

**Base URL**: `http://localhost:3000/api/v1`

**Authentication**: Bearer token (generate in UI: Settings > Account > API Keys)

**Endpoints**:

1. **Upload File**
   ```
   POST /files/
   Content-Type: multipart/form-data

   Returns: {"id": "file-abc123", ...}
   ```

2. **Check Processing Status**
   ```
   GET /files/{file_id}/process/status

   Returns: {"status": "completed" | "processing" | "failed"}
   ```

3. **Create Knowledge Base**
   ```
   POST /knowledge/
   Body: {"name": "Meetings", "description": "..."}

   Returns: {"id": "kb-def456", ...}
   ```

4. **List Knowledge Bases**
   ```
   GET /knowledge/

   Returns: [{"id": "kb-def456", "name": "Meetings", ...}]
   ```

5. **Add File to Knowledge Base**
   ```
   POST /knowledge/{kb_id}/file/add
   Body: {"file_id": "file-abc123"}
   ```

## Data Flow

```
orchestrator.py (main pipeline)
    ↓
    Step 4.5: upload_to_openwebui(result_folder)
    ↓
subprocess.run([python, openwebui_uploader.py, result_folder])
    ↓
    1. Validate files exist
    ↓
    2. OpenWebUIClient.health_check()
    ↓
    3. ContextualEnricher.enrich_meeting_folder() [if enabled]
       ↓ Calls Claude API for each chunk
       ↓ Saves to result_folder/enriched/
    ↓
    4. Get or create Knowledge Base "Meetings"
    ↓
    5. For each file (transcript, summary, protocol):
       ↓ client.upload_file() → file_id
       ↓ client.wait_for_processing(file_id) [polls every 5s]
       ↓ client.add_file_to_knowledge_base(kb_id, file_id)
    ↓
    6. Update metadata.json with:
       - openwebui_rag_indexed: true
       - openwebui_indexed_at: "2025-01-15T14:30:00Z"
       - openwebui_knowledge_base_id: "kb-def456"
       - openwebui_knowledge_base_name: "Meetings"
       - openwebui_files: [{type, file_id, filename}, ...]
       - contextual_enrichment_applied: true/false
    ↓
    Returns success/failure to orchestrator
    ↓
orchestrator updates result dict with openwebui_rag_indexed
```

## Error Handling

### Graceful Degradation

1. **OpenWebUI unavailable**: Log warning, continue pipeline
2. **Contextual enrichment fails**: Fall back to original files
3. **Upload fails**: Meeting still processable locally
4. **File processing timeout**: Configurable timeout (180s per file)

### Error Messages

```python
# OpenWebUI not accessible
"[ERROR] OpenWebUI API not accessible at http://localhost:3000"
"[INFO] Make sure OpenWebUI is running: cd services/OpenWebUi && docker-compose up -d"

# API key not set
"[ERROR] OPENWEBUI_API_KEY environment variable not set"
"[INFO] Generate API key in OpenWebUI UI: Settings > Account > API Keys"

# Upload timeout
"[ERROR] OpenWebUI upload timed out (300s)"

# Processing timeout
"[ERROR] File processing timeout after 180s"
```

## Knowledge Base Structure

### Single Shared Knowledge Base

**Name**: "Meetings"

**Benefits**:
- Simpler management (one KB vs hundreds)
- Cross-meeting search by default
- No need to specify KB when querying

**File Naming**:
- `meeting_20250115_143022_transcript.json`
- `meeting_20250115_143022_summary.md`
- `meeting_20250115_143022_protocol.md`

**Metadata Tracking**:
Each file includes meeting ID in filename, allowing queries like "March 9" to retrieve relevant chunks.

## Async Processing Pattern

**Critical**: OpenWebUI processes files asynchronously (embedding generation).

```python
# Upload file
file_id = client.upload_file(file_path)

# Wait for processing to complete
client.wait_for_processing(file_id, timeout=180)
# Polls /api/v1/files/{file_id}/process/status every 5s

# Only then add to Knowledge Base
client.add_file_to_knowledge_base(kb_id, file_id)
```

**If added before processing completes**: 400 error (no content)

## Configuration Variables

### Required

- `OPENWEBUI_API_KEY`: API key (generate in UI)
- `CLAUDE_API_KEY`: For contextual enrichment (if enabled)

### Optional

- `ENABLE_OPENWEBUI_RAG`: Enable/disable (default: `false`)
- `OPENWEBUI_URL`: Service URL (default: `http://localhost:3000`)
- `ENABLE_CONTEXTUAL_RETRIEVAL`: Enable enrichment (default: `true`)
- `CONTEXT_GENERATION_MODEL`: Claude model (default: `claude-sonnet-4-5-20250929`)

## Testing

### Unit Test

```bash
# Test OpenWebUI client
cd services/OpenWebUi/scripts
python openwebui_client.py

# Expected output:
# Testing connection to http://localhost:3000...
# ✓ OpenWebUI API is accessible
# Knowledge Bases:
#   - Meetings (ID: kb-def456)
```

### Integration Test

```bash
# Test end-to-end upload
python services/OpenWebUi/scripts/test_openwebui_integration.py

# Expected output:
# [1/5] Testing OpenWebUI API connection... ✓
# [2/5] Checking for 'Meetings' Knowledge Base... ✓
# [3/5] Testing file upload... ✓
# [4/5] Waiting for file processing... ✓
# [5/5] Adding file to Knowledge Base... ✓
# === All tests passed! ===
```

### Manual Test

```bash
# Process test meeting
python services/transcription_orchestrator/orchestrator.py data/input/test_meeting.avi

# Check logs for:
# [STEP 4.5] Uploading to OpenWebUI Knowledge Base
# [Step 3/6] Applying Contextual Retrieval enrichment...
# [✓] Upload completed successfully!

# Verify in metadata.json
cat data/results/test_meeting_*/metadata.json | grep openwebui_rag_indexed
# Should show: "openwebui_rag_indexed": true
```

## Monitoring

### Docker Logs

```bash
# OpenWebUI logs
docker-compose -f services/OpenWebUi/docker-compose.yml logs -f openwebui

# Watch for:
# - "Downloading model BAAI/bge-m3..." (first upload)
# - "Processing file {file_id}..."
# - "Embedding generation completed"

# Qdrant logs
docker-compose -f services/OpenWebUi/docker-compose.yml logs -f qdrant
```

### Health Checks

```bash
# OpenWebUI
curl http://localhost:3000/health

# Qdrant
curl http://localhost:6333/health
```

### Storage Usage

```bash
# Check vector database size
du -sh services/OpenWebUi/qdrant_data/

# Check models cache size
du -sh services/OpenWebUi/models_cache/

# Check OpenWebUI data size
du -sh services/OpenWebUi/openwebui_data/
```

## Troubleshooting Integration Issues

### Orchestrator doesn't call uploader

- Check: `ENABLE_OPENWEBUI_RAG=true` in root `.env`
- Verify: `OPENWEBUI_UPLOADER_SCRIPT` path is correct
- Check logs: orchestrator should print "Uploading to OpenWebUI Knowledge Base"

### Uploader script fails

- Check: `OPENWEBUI_API_KEY` is set in `.env`
- Verify: OpenWebUI is running (`docker-compose ps`)
- Test: Run uploader manually with test folder

### Files not appearing in Knowledge Base

- Check: Processing completed (`wait_for_processing` didn't timeout)
- Verify: File added to KB without errors
- UI: Refresh Knowledge Base page in OpenWebUI

### Contextual enrichment not working

- Check: `ENABLE_CONTEXTUAL_RETRIEVAL=true`
- Verify: `CLAUDE_API_KEY` is set and valid
- Check logs: Should see "Applying Contextual Retrieval enrichment..."

## Performance Optimization

### Reduce Indexing Time

1. **Disable contextual enrichment** (not recommended):
   ```env
   ENABLE_CONTEXTUAL_RETRIEVAL=false
   ```

2. **Use faster Claude model** (lower quality):
   ```env
   CONTEXT_GENERATION_MODEL=claude-haiku-3-5-20241022
   ```

### Reduce Storage Usage

1. **Increase chunk size** (fewer chunks, less vectors):
   ```yaml
   environment:
     - CHUNK_SIZE=2000  # Default: 1000
   ```

2. **Disable reranker** (saves model cache space):
   ```yaml
   environment:
     - RAG_RERANKING_MODEL=  # Empty
   ```

## Claude API Integration

OpenWebUI supports Claude via OpenAI-compatible endpoint:

**docker-compose.yml**:
```yaml
environment:
  - OPENAI_API_BASE_URLS=https://api.anthropic.com/v1
  - OPENAI_API_KEYS=${CLAUDE_API_KEY}
```

**In UI**:
1. Settings > Connections > Add Connection
2. OpenAI API URL: `https://api.anthropic.com/v1`
3. API Key: `${CLAUDE_API_KEY}`
4. Models appear as: `claude-sonnet-4-5`, `claude-haiku-4-5`

## Additional Notes

- **No breaking changes**: Existing orchestrator pipeline continues if OpenWebUI disabled
- **Parallel with RAGFlow**: Can run both RAGFlow and OpenWebUI simultaneously
- **Shared context generation**: Reuses same contextual enrichment code
- **Independent deployment**: OpenWebUI stack can be deployed separately
