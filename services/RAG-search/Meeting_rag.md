# RAG Search Service Implementation Plan

## Overview

Create a RAG (Retrieval Augmented Generation) service for semantic search across meeting transcriptions using **RAGFlow** framework with **Contextual Retrieval** (Anthropic approach). The service will automatically index meetings after orchestrator.py completes, enabling Claude to answer natural language queries like "What did we discuss about GPB project on March 9?" and "Which video file contains this discussion?"

## Architecture Stack

**RAGFlow-Based Architecture:**

```
┌─────────────────────────────────────────────────────┐
│              RAGFlow UI                             │
│  (chunking config, document upload, chat interface) │
├─────────────────────────────────────────────────────┤
│              DeepDoc Engine                         │
│  (OCR, layout recognition, table extraction)        │
├─────────────────────────────────────────────────────┤
│          Embedding: BGE-M3                          │
│     (dense + sparse hybrid retrieval)               │
├─────────────────────────────────────────────────────┤
│      Vector DB: Infinity Engine                     │
│        (HNSW index, filtering)                      │
├─────────────────────────────────────────────────────┤
│        Reranker: bge-reranker-v2-m3                 │
│         (top-20 → top-5 filtering)                  │
├─────────────────────────────────────────────────────┤
│          LLM: Claude Sonnet 4.5 API                 │
│            (generation layer)                       │
└─────────────────────────────────────────────────────┘
```

**Technology Stack:**
- **RAGFlow** - Open-source RAG framework (UI + orchestration)
- **DeepDoc** - Document parsing engine (built into RAGFlow)
- **BGE-M3** - Embedding model (1024-dim, multilingual, hybrid retrieval)
- **Infinity** - High-performance vector engine (HNSW index)
- **bge-reranker-v2-m3** - Reranking model for precision
- **Claude Sonnet 4.5 API** - LLM for generation
- **Contextual Retrieval** - Anthropic's technique for context-enhanced chunks
- Docker containerization

**Data Flow with Contextual Retrieval:**

```
Orchestrator completes → metadata.json saved (line 1649)
    ↓
Python script: Auto-upload to RAGFlow via API
    ↓
RAGFlow ingestion pipeline:
  1. Load meeting files (transcript, summary, protocol)
  2. Chunk documents with meeting context
  3. CONTEXTUAL RETRIEVAL: Add context to each chunk using Claude API
     - Generate chunk context: "This is from meeting {title} on {date} with {speakers}"
     - Prepend context to chunk before embedding
  4. DeepDoc: Parse structure (tables, lists, sections)
  5. BGE-M3: Generate hybrid embeddings (dense + sparse)
  6. Infinity: Store vectors with HNSW index
    ↓
Update metadata.json: rag_indexed=true, ragflow_dataset_id
    ↓
User query → RAGFlow UI or API:
  1. Embed query with BGE-M3
  2. Retrieve top-20 candidates from Infinity
  3. Rerank with bge-reranker-v2-m3 → top-5
  4. Send to Claude Sonnet 4.5 with context
  5. Generate answer with citations
```

**Why This Stack?**

1. **RAGFlow**: Production-ready framework, no need to build UI/chunking from scratch
2. **Contextual Retrieval**: Anthropic's technique - adds document context to chunks before embedding, significantly improves retrieval accuracy
3. **BGE-M3 Hybrid**: Dense + sparse vectors = better multilingual retrieval
4. **Infinity**: High-performance vector engine optimized for fast embedding serving
5. **Reranker**: Second-stage filtering improves precision (removes false positives)
6. **Claude Sonnet 4.5**: Latest model with 200K context window

## Contextual Retrieval Explained

**Anthropic's Contextual Retrieval Technique:**

Traditional RAG systems embed chunks in isolation, losing document context. Contextual Retrieval solves this by prepending context to each chunk before embedding.

**Example:**

*Without Context:*
- Chunk: "Иван согласился завершить расчеты до 15 марта"
- Embedding lacks meeting context
- Poor retrieval: doesn't know which meeting, which project

*With Context (Contextual Retrieval):*
- Context: "Встреча: GPB проект - обсуждение счетов, Дата: 2025-03-09, Участники: Иван Петров, Мария Иванова"
- Chunk: "Иван согласился завершить расчеты до 15 марта"
- **Combined for embedding:** "{context}\n\n{chunk}"
- Better retrieval: knows meeting context, can filter by date/participants

**Implementation:**
1. For each chunk, call Claude API with prompt: "Provide brief context for this chunk from the meeting metadata"
2. Claude generates 1-2 sentence context based on meeting title, date, speakers
3. Prepend context to chunk text
4. Embed the combined text with BGE-M3
5. Store in Infinity with original chunk + context as metadata

**Benefits:**
- +30% retrieval accuracy (Anthropic benchmark)
- Better cross-meeting queries
- Implicit metadata filtering through semantic search

## Key Design Decisions

1. **Use RAGFlow Framework:** Don't build from scratch
   - RAGFlow provides UI, chunking, API, chat interface
   - DeepDoc engine handles complex document parsing
   - Built-in support for multiple vector DBs and LLMs

2. **Contextual Retrieval Implementation:**
   - Pre-processing step before RAGFlow ingestion
   - Python script enriches chunks with context using Claude API
   - OR configure RAGFlow's chunking to add metadata context

3. **Hybrid Retrieval (BGE-M3):**
   - Dense vectors: semantic similarity
   - Sparse vectors: keyword matching (important for Russian)
   - Combined retrieval: best of both worlds

4. **Two-Stage Retrieval:**
   - Stage 1: Infinity retrieves top-20 candidates (fast)
   - Stage 2: Reranker filters to top-5 (precise)
   - Reduces LLM context size and improves answer quality

5. **Automatic Indexing:** Orchestrator triggers Python upload script
   - Non-blocking: errors don't break orchestrator
   - Upload to RAGFlow dataset via API
   - Track dataset_id in metadata.json

## File Structure

```
services/RAG-search/
├── Meeting_rag.md                       # This implementation plan
├── docker-compose.ragflow.yml           # RAGFlow + Infinity + Reranker stack
├── scripts/
│   ├── contextual_enrichment.py         # Add context to chunks (Anthropic technique)
│   ├── ragflow_uploader.py              # Upload meetings to RAGFlow via API
│   ├── ragflow_client.py                # RAGFlow API client wrapper
│   └── test_contextual_retrieval.py     # Test retrieval quality
├── config/
│   ├── ragflow_config.yml               # RAGFlow configuration
│   ├── chunking_strategy.json           # Chunking parameters for meetings
│   └── prompts/
│       └── context_generation.txt       # Prompt for generating chunk context
└── data/
    └── ragflow_datasets/                # RAGFlow dataset metadata
```

**Note:** RAGFlow itself is deployed as a separate Docker stack. We create integration scripts to automatically upload meetings from orchestrator.

## RAGFlow Configuration

**Dataset Structure:**

Each meeting will be uploaded as a separate "dataset" in RAGFlow with rich metadata:

```yaml
# config/ragflow_config.yml

embedding_model: BAAI/bge-m3
vector_engine: infinity
reranker_model: bge-reranker-v2-m3
llm_model: claude-sonnet-4-5
chunk_size: 512
chunk_overlap: 50
enable_contextual_retrieval: true

# Meeting-specific chunking
meeting_chunk_strategy:
  transcript:
    method: "speaker_turn"  # Chunk by speaker utterances
    max_tokens: 400
    preserve_speaker_labels: true

  protocol:
    method: "section"  # Chunk by markdown sections
    section_headers: ["УЧАСТНИКИ", "РЕШЕНИЯ", "ОБЯЗАТЕЛЬСТВА"]

  summary:
    method: "whole_document"  # Keep summary as single chunk
```

**Contextual Enrichment Prompt:**

```python
# config/prompts/context_generation.txt

Given the following meeting metadata and a text chunk, generate a brief 1-2 sentence context that will be prepended to the chunk before embedding.

Meeting Metadata:
- Title: {meeting_title}
- Date: {meeting_date}
- Duration: {duration_minutes} minutes
- Participants: {speaker_list}
- Document Type: {doc_type}

Chunk:
{chunk_text}

Context (1-2 sentences in Russian, mentioning meeting topic, date, and key participants):
```

**Meeting Metadata Fields (Stored in RAGFlow):**

```python
{
    "meeting_id": "uuid",
    "meeting_title": "GPB - Обсуждение счетов - 2025-03-09",
    "meeting_date": "2025-03-09",
    "video_filename": "meeting.avi",
    "result_folder": "/path/to/results",
    "duration_seconds": 3467.5,
    "num_speakers": 3,
    "recognized_speakers": ["Иван Петров", "Мария Иванова"],
    "doc_type": "transcript|summary|protocol",
    "speaker": "Иван Петров",  # For transcript chunks
    "start_time": 125.3,        # For transcript chunks
    "end_time": 142.7,          # For transcript chunks
    "protocol_section": "COMMITMENTS"  # For protocol chunks
}
```

## RAGFlow API Integration

**RAGFlow API Endpoints (we'll use):**

```python
# Dataset management
POST   /api/v1/datasets                    # Create dataset for meeting
GET    /api/v1/datasets                    # List all datasets
DELETE /api/v1/datasets/{dataset_id}       # Delete meeting dataset

# Document upload
POST   /api/v1/datasets/{id}/documents     # Upload meeting files
GET    /api/v1/datasets/{id}/documents     # List documents in dataset

# Parsing & Chunking
POST   /api/v1/documents/{id}/chunks       # Trigger chunking
GET    /api/v1/documents/{id}/chunks       # Get chunks

# Search & Retrieval
POST   /api/v1/datasets/{id}/retrieval     # Query the dataset
POST   /api/v1/chat                        # Chat with Claude

# Health
GET    /api/v1/health                      # Health check
```

**Our Integration Scripts:**

```python
# scripts/ragflow_uploader.py
def upload_meeting_to_ragflow(result_folder: Path) -> str:
    """
    Upload a meeting to RAGFlow with contextual enrichment
    Returns: dataset_id
    """
    # 1. Create dataset
    dataset_id = ragflow_client.create_dataset(
        name=folder_name,
        metadata=extract_meeting_metadata(result_folder)
    )

    # 2. Load meeting files
    files = {
        "transcript": result_folder / "transcript_readable.txt",
        "summary": result_folder / "summary.md",
        "protocol": result_folder / "protocol.md"
    }

    # 3. Apply contextual enrichment
    enriched_files = contextual_enrichment.enrich_files(
        files,
        meeting_metadata=metadata
    )

    # 4. Upload to RAGFlow
    for file_path in enriched_files:
        ragflow_client.upload_document(dataset_id, file_path)

    # 5. Trigger parsing & chunking
    ragflow_client.parse_documents(dataset_id)

    return dataset_id
```

## Critical Files to Create/Modify

### New Files (RAGFlow Integration)

**services/RAG-search/Meeting_rag.md** - This implementation plan document

**services/RAG-search/docker-compose.ragflow.yml** - RAGFlow + Infinity + Reranker Docker stack

**services/RAG-search/scripts/contextual_enrichment.py** - Implement Contextual Retrieval:
- Load meeting metadata (from metadata.json)
- Chunk documents (transcript, summary, protocol)
- For each chunk, call Claude API to generate context
- Prepend context to chunk before saving

**services/RAG-search/scripts/ragflow_uploader.py** - Upload to RAGFlow:
- Create dataset in RAGFlow
- Upload enriched files
- Trigger parsing & chunking
- Return dataset_id

**services/RAG-search/scripts/ragflow_client.py** - RAGFlow API wrapper:
- HTTP client for RAGFlow REST API
- Methods: create_dataset, upload_document, parse_documents, search, chat

**services/RAG-search/scripts/test_contextual_retrieval.py** - Test retrieval quality:
- Compare retrieval with/without contextual enrichment
- Benchmark accuracy improvements

**services/RAG-search/config/ragflow_config.yml** - RAGFlow configuration:
- Embedding model: BGE-M3
- Vector engine: Infinity
- Reranker: bge-reranker-v2-m3
- LLM: Claude Sonnet 4.5
- Chunking strategies

**services/RAG-search/config/prompts/context_generation.txt** - Prompt for context generation

**services/RAG-search/config/chunking_strategy.json** - Meeting-specific chunking rules

### Files to Modify

**services/transcription_orchestrator/orchestrator.py**
- Add RAG integration hook after line 1652
- Add `upload_to_ragflow()` function (calls ragflow_uploader.py)
- Add configuration: RAGFLOW_URL, ENABLE_RAG_INDEXING

**.env.example**
- Add RAGFlow configuration variables

**CLAUDE.md**
- Document RAGFlow integration and usage

## Integration Point in orchestrator.py

**Location:** After line 1652 (after "All files saved in one folder!")

**Add this code:**

```python
# Line 1652: print("\n[OK] All files saved in one folder!")

# NEW: Step 4.5 - Upload to RAGFlow (if enabled)
if ENABLE_RAG_INDEXING:
    dataset_id = upload_to_ragflow(result_folder)
    result["rag_indexed"] = dataset_id is not None
    if dataset_id:
        result["rag_indexed_at"] = datetime.utcnow().isoformat()
        result["ragflow_dataset_id"] = dataset_id
else:
    result["rag_indexed"] = False

# Update metadata.json with RAG status
with open(metadata_path, 'w', encoding='utf-8') as f:
    json.dump(result, f, ensure_ascii=False, indent=2)

# Line 1654: Step 5: Send email (if email found in filename)
```

**Add helper function (around line 66, after configuration):**

```python
# RAGFlow configuration
RAGFLOW_URL = os.getenv("RAGFLOW_URL", "http://localhost:9380")
ENABLE_RAG_INDEXING = os.getenv("ENABLE_RAG_INDEXING", "false").lower() == "true"
RAGFLOW_UPLOADER_SCRIPT = Path(__file__).parent.parent / "RAG-search" / "scripts" / "ragflow_uploader.py"

def upload_to_ragflow(result_folder: Path) -> Optional[str]:
    """
    Upload meeting to RAGFlow with contextual enrichment
    Returns dataset_id if successful, None otherwise
    """
    print(f"\n[STEP 4.5] Uploading to RAGFlow...")

    try:
        # Call the RAGFlow uploader script
        import subprocess
        result = subprocess.run(
            [sys.executable, str(RAGFLOW_UPLOADER_SCRIPT), str(result_folder)],
            capture_output=True,
            text=True,
            timeout=300  # 5 minutes (includes contextual enrichment via Claude API)
        )

        if result.returncode == 0:
            dataset_id = result.stdout.strip()
            print(f"[OK] RAGFlow indexed: dataset_id={dataset_id}")
            return dataset_id
        else:
            print(f"[WARNING] RAGFlow upload failed: {result.stderr}")
            return None

    except Exception as e:
        print(f"[WARNING] RAGFlow upload error: {e}")
        return None
```

## Environment Variables

Add to `.env.example`:

```env
# ============================================================
# RAGFlow RAG SYSTEM
# ============================================================

# Enable automatic RAGFlow upload after transcription
ENABLE_RAG_INDEXING=false

# RAGFlow service URL (default port: 9380)
RAGFLOW_URL=http://localhost:9380

# RAGFlow API Key (get from RAGFlow UI: Settings → API Keys)
RAGFLOW_API_KEY=your-ragflow-api-key-here

# Contextual Retrieval (Anthropic technique)
ENABLE_CONTEXTUAL_RETRIEVAL=true
CONTEXT_GENERATION_MODEL=claude-sonnet-4-5

# Claude API for contextual enrichment and LLM generation
CLAUDE_API_KEY=sk-ant-xxxxx  # Already exists for summary/protocol generation

# Infinity vector engine (embedded in RAGFlow, no config needed)
# BGE-M3 embedding model (configured in RAGFlow UI)
# bge-reranker-v2-m3 (configured in RAGFlow UI)
```

## Docker Configuration (RAGFlow)

### RAGFlow Docker Compose (services/RAG-search/docker-compose.ragflow.yml)

RAGFlow provides an official Docker Compose stack. We'll deploy it with custom configuration for our meeting transcription use case:

```yaml
# docker-compose.ragflow.yml
version: '3.8'

services:
  ragflow:
    image: infiniflow/ragflow:latest
    container_name: ragflow
    ports:
      - "9380:9380"  # Web UI
      - "9381:9381"  # API
    volumes:
      - ./ragflow_data:/ragflow/data
      - ./ragflow_logs:/ragflow/logs
      - C:/YandexDisk/DIASOFT/VideoPars/data:/ragflow/upload
    environment:
      - EMBEDDING_MODEL=BAAI/bge-m3
      - VECTOR_ENGINE=infinity
      - RERANKER_MODEL=bge-reranker-v2-m3
      - CLAUDE_API_KEY=${CLAUDE_API_KEY}
      - CLAUDE_MODEL=claude-sonnet-4-5-20250929
    depends_on:
      - ragflow-mysql
      - ragflow-redis
      - infinity
    restart: unless-stopped
    networks:
      - ragflow-net

  ragflow-mysql:
    image: mysql:8.0
    container_name: ragflow-mysql
    environment:
      - MYSQL_ROOT_PASSWORD=infiniflow
      - MYSQL_DATABASE=ragflow
    volumes:
      - ./mysql_data:/var/lib/mysql
    networks:
      - ragflow-net

  ragflow-redis:
    image: redis:7-alpine
    container_name: ragflow-redis
    command: redis-server --requirepass infiniflow
    networks:
      - ragflow-net

  infinity:
    image: michaelf34/infinity:latest
    container_name: ragflow-infinity
    ports:
      - "7997:7997"
    environment:
      - MODEL_ID=BAAI/bge-m3
      - DEVICE=cpu
    volumes:
      - ./infinity_models:/app/models
    networks:
      - ragflow-net

networks:
  ragflow-net:
    driver: bridge
```

### Start RAGFlow

```bash
cd services/RAG-search
docker-compose -f docker-compose.ragflow.yml up -d
# Access UI: http://localhost:9380 (admin/admin)
```

## Implementation Steps (Simplified with RAGFlow)

### Phase 1: Deploy RAGFlow (Day 1)

1. **Create git branch and folder structure**
   ```bash
   git checkout -b feature/RAG-search
   mkdir -p services/RAG-search/{scripts,config/prompts,data/ragflow_datasets}
   ```

2. **Deploy RAGFlow stack**
   - Create `docker-compose.ragflow.yml` (copy from Docker Configuration section above)
   - Start stack: `docker-compose -f docker-compose.ragflow.yml up -d`
   - Access UI: http://localhost:9380 (login: admin/admin)

3. **Configure RAGFlow via UI**
   - Settings → Embedding Model: Select "BAAI/bge-m3"
   - Settings → Vector Engine: Select "Infinity"
   - Settings → Reranker: Select "bge-reranker-v2-m3"
   - Settings → LLM: Add Claude API key, select "claude-sonnet-4-5"
   - Settings → API Keys: Generate API key for script integration

### Phase 2: Implement Contextual Retrieval (Day 2)

4. **Create contextual enrichment script**
   - `scripts/contextual_enrichment.py`:
     - Read meeting metadata.json
     - Chunk transcript/summary/protocol files
     - For each chunk, call Claude API with context generation prompt
     - Prepend generated context to chunk
     - Save enriched files

5. **Create context generation prompt**
   - `config/prompts/context_generation.txt`:
     - Template for Claude to generate 1-2 sentence context
     - Include meeting title, date, participants, doc type

6. **Test contextual enrichment**
   - Run on sample meeting
   - Verify chunks have context prepended
   - Compare retrieval quality with/without context

### Phase 3: RAGFlow Integration Scripts (Day 3)

7. **Implement RAGFlow API client**
   - `scripts/ragflow_client.py`:
     - HTTP client for RAGFlow REST API
     - Methods: create_dataset(), upload_document(), parse_documents(), search(), chat()

8. **Implement uploader script**
   - `scripts/ragflow_uploader.py`:
     - Main script called by orchestrator
     - Load meeting files and metadata
     - Call contextual_enrichment.py
     - Upload to RAGFlow via API
     - Return dataset_id

### Phase 4: Orchestrator Integration (Day 4)

9. **Update orchestrator.py**
   - Add RAGFlow configuration variables (line ~66)
   - Add `upload_to_ragflow()` function
   - Add hook after line 1652 (call upload script)
   - Update metadata.json with rag_indexed, ragflow_dataset_id

10. **Update .env.example**
    - Add all RAGFlow variables (see Environment Variables section)

11. **Test end-to-end**
    - Process a meeting with `ENABLE_RAG_INDEXING=true`
    - Verify upload to RAGFlow
    - Check dataset in RAGFlow UI
    - Test search via RAGFlow chat interface

### Phase 5: Testing & Documentation (Day 5)

12. **Quality testing**
    - Test retrieval accuracy (with vs without contextual enrichment)
    - Test cross-meeting queries
    - Test metadata filtering (date, speakers)
    - Test reranking quality

13. **Documentation**
    - Create this `Meeting_rag.md` plan document
    - Update `CLAUDE.md` with RAGFlow usage instructions
    - Document configuration in `config/ragflow_config.yml`

14. **Final verification**
    - Process 10+ meetings
    - Verify all indexed correctly
    - Test various query types
    - Measure retrieval performance

## Quick Start Summary

**After implementation, to use the RAG system:**

1. **Start RAGFlow**: `cd services/RAG-search && docker-compose -f docker-compose.ragflow.yml up -d`

2. **Process meetings**: Meetings will auto-upload to RAGFlow if `ENABLE_RAG_INDEXING=true` in `.env`

3. **Query via RAGFlow UI**:
   - Open http://localhost:9380
   - Select dataset (meeting)
   - Ask questions in natural language
   - Get answers with source citations

4. **Query via API**:
   ```python
   import requests
   response = requests.post(
       "http://localhost:9381/api/v1/chat",
       headers={"Authorization": f"Bearer {api_key}"},
       json={
           "question": "Что обсудили по проекту GPB 9 марта?",
           "dataset_ids": ["all"],  # or specific meeting IDs
           "top_k": 5
       }
   )
   print(response.json()["answer"])
   ```

## Success Criteria

- ✅ RAGFlow deployed and accessible
- ✅ BGE-M3, Infinity, Reranker, Claude configured
- ✅ Contextual enrichment working (context prepended to chunks)
- ✅ Auto-upload from orchestrator functional
- ✅ Can query meetings via RAGFlow UI
- ✅ Retrieval accuracy >70% (vs <50% without context)
- ✅ Cross-meeting queries work
- ✅ Source citations include video filename and timestamp

## Benefits of RAGFlow Approach

1. **No custom code for UI, chunking, search** - RAGFlow provides all of this
2. **Production-ready** - Battle-tested framework used by many companies
3. **Contextual Retrieval** - Anthropic's technique for +30% accuracy
4. **Hybrid retrieval** - BGE-M3 combines dense + sparse vectors
5. **Reranking** - Second-stage filtering improves precision
6. **Built-in chat** - Can chat with meetings directly in UI
7. **Faster implementation** - ~5 days vs ~2-3 weeks for custom solution

---

**END OF PLAN**

This plan uses RAGFlow with Infinity vector engine (NOT Qdrant) and implements Anthropic's Contextual Retrieval technique for superior meeting search and question-answering capabilities.
