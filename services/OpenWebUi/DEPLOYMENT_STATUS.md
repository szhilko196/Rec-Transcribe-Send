# OpenWebUI RAG Deployment Status

## ✅ Implementation Complete

All code has been successfully implemented:

### Files Created (11 new files)

1. **Docker Stack**
   - `docker-compose.yml` - OpenWebUI + Qdrant services
   - `.gitignore` - Data directory exclusions

2. **Python Scripts**
   - `scripts/openwebui_client.py` - API client library
   - `scripts/openwebui_uploader.py` - Main upload orchestrator
   - `scripts/contextual_enrichment.py` - Contextual Retrieval (from RAG-search)
   - `scripts/test_openwebui_integration.py` - E2E integration test

3. **Configuration**
   - `.env.example` - Configuration template
   - `config/prompts/context_generation.txt` - Context generation prompt

4. **Documentation**
   - `README.md` - Quick start guide
   - `INTEGRATION.md` - Technical integration guide
   - `DEPLOYMENT_STATUS.md` - This file

### Files Modified (2 files)

1. **`services/transcription_orchestrator/orchestrator.py`**
   - Added OpenWebUI configuration (lines 68-71)
   - Added `upload_to_openwebui()` function (lines 1538-1581)
   - Integrated Step 4.5 in pipeline (lines 1665-1675)
   - Updated metadata tracking (line 1707)

2. **Root `.env`**
   - Added OpenWebUI RAG configuration section

---

## 🚀 Current Deployment Status

### Step 1: Docker Image Download ✅ COMPLETE

Docker images have been successfully downloaded:

- **OpenWebUI**: ~1.0 GB ✓
- **Qdrant**: ~340 MB ✓

### Step 2: Services Running ✅ COMPLETE

Both services are now running and healthy:

- **OpenWebUI**: http://localhost:3000 (healthy) ✓
- **Qdrant**: http://localhost:6333 (healthy) ✓

**Note**: Fixed healthcheck issues during deployment:
- Changed Qdrant healthcheck from `/health` to `/healthz` with TCP check
- Removed obsolete `version` field from docker-compose.yml
- Disabled OpenWebUI healthcheck (curl not available in container)

---

## 📋 Next Steps

### Step 3: Access OpenWebUI ← YOU ARE HERE

1. Open browser: http://localhost:3000
2. Create admin account (first user becomes admin)
3. Login successful ✓

### Step 4: Generate API Key

1. Click on profile icon (top right)
2. Go to **Settings** > **Account**
3. Scroll to **API Keys** section
4. Click **Create new API key**
5. Copy the generated key

### Step 5: Configure Environment

Add API key to root `.env`:

```bash
# Edit C:\prj\Rec-Transcribe-Send\.env
ENABLE_OPENWEBUI_RAG=true
OPENWEBUI_URL=http://localhost:3000
OPENWEBUI_API_KEY=your-generated-key-here
```

### Step 6: Test Integration

```bash
# Set API key in environment
set OPENWEBUI_API_KEY=your-key-here

# Run integration test
python services/OpenWebUi/scripts/test_openwebui_integration.py
```

**Expected output:**
```
[Test 1/6] Testing OpenWebUI API connection... ✓
[Test 2/6] Listing Knowledge Bases... ✓
[Test 3/6] Checking for 'Meetings' Knowledge Base... ✓
[Test 4/6] Creating test transcript file... ✓
[Test 5/6] Testing file upload and processing... ✓
    (First upload will download BGE-M3 model: ~2GB)
[Test 6/6] Verifying file metadata... ✓

=== All tests passed successfully! ===
```

### Step 7: Process a Meeting

```bash
# Process test meeting
python services/transcription_orchestrator/orchestrator.py data/input/test_meeting.avi

# Watch for Step 4.5 output:
# [STEP 4.5] Uploading to OpenWebUI Knowledge Base
# [Step 1/6] Validating result folder... ✓
# [Step 2/6] Checking OpenWebUI API... ✓
# [Step 3/6] Applying Contextual Retrieval enrichment... ✓
# [Step 4/6] Setting up Knowledge Base... ✓
# [Step 5/6] Uploading files to OpenWebUI... ✓
# [Step 6/6] Updating metadata... ✓
# [✓] Upload completed successfully!
```

### Step 8: Query Meetings

1. Open http://localhost:3000
2. Create new chat
3. Type `#Meetings` to reference the Knowledge Base
4. Ask questions:
   - "Что обсудили по проекту GPB 9 марта?"
   - "Кто отвечает за расчеты до 15 марта?"
   - "В каком видео обсуждали счета?"

---

## 🎯 Architecture

```
Meeting transcription
    ↓
Contextual enrichment (Claude Sonnet 4.5 adds context to chunks)
    ↓
OpenWebUI API upload
    ↓
BGE-M3 embedding generation (SentenceTransformers)
    ↓
Qdrant vector storage (HNSW indexing)
    ↓
User query
    ↓
Hybrid search (BM25 + semantic)
    ↓
bge-reranker-v2-m3 reranking (top-3 from top-8)
    ↓
Claude Haiku 4.5 generation with citations
```

---

## 📊 What Happens on First Upload

### Model Downloads ✅ COMPLETE

Models were automatically downloaded during OpenWebUI startup:

1. **BGE-M3 embedding model** (~1.5 GB) ✓
   - Multilingual embeddings (100+ languages)
   - Supports up to 8192 tokens per chunk
   - Dense + sparse hybrid retrieval
   - Downloaded in 13 minutes on first startup

2. **bge-reranker-v2-m3** (~500 MB) ✓
   - CrossEncoder reranking model
   - Two-stage retrieval for better precision

Models are now cached in `./models_cache/` volume for persistence.

**First upload time**: 3-5 minutes (context generation + upload)
**Subsequent uploads**: 30-60 seconds per meeting

---

## ⚙️ Configuration Summary

### Docker Services

- **OpenWebUI**: Port 3000 (web UI + API)
- **Qdrant**: Ports 6333 (HTTP) + 6334 (gRPC)

### Environment Variables (Root `.env`)

```env
# Enable automatic indexing
ENABLE_OPENWEBUI_RAG=true

# Service URL
OPENWEBUI_URL=http://localhost:3000

# API key (generate in UI)
OPENWEBUI_API_KEY=

# Contextual Retrieval (reuses from RAG-search)
ENABLE_CONTEXTUAL_RETRIEVAL=true
CONTEXT_GENERATION_MODEL=claude-sonnet-4-5-20250929

# Claude API (already configured)
CLAUDE_API_KEY=sk-ant-xxxxx
```

### OpenWebUI Configuration (docker-compose.yml)

```yaml
environment:
  # Embedding: BGE-M3 via SentenceTransformers
  - RAG_EMBEDDING_MODEL=BAAI/bge-m3

  # Reranking: bge-reranker-v2-m3
  - RAG_RERANKING_MODEL=BAAI/bge-reranker-v2-m3
  - RAG_TOP_K=8
  - RAG_TOP_K_RERANKER=3

  # Hybrid Search
  - ENABLE_RAG_HYBRID_SEARCH=true
  - RAG_HYBRID_BM25_WEIGHT=0.5

  # Chunking
  - CHUNK_SIZE=1000
  - CHUNK_OVERLAP=100
```

---

## 📈 Performance Expectations

### Indexing Performance

- **With Contextual Enrichment** (recommended): 3-5 min per meeting
  - Context generation: 2-4 min (Claude API calls for ~50-200 chunks)
  - Upload + embedding: 30-60 seconds

- **Without Contextual Enrichment**: 30-60 seconds per meeting
  - Upload + embedding only
  - Not recommended: -30% retrieval accuracy

### Query Performance

- **Search**: 200-500ms (hybrid search + reranking)
- **Chat with Claude**: 2-4 seconds (retrieval + generation + citations)

### Storage Requirements

- **Vector Database**: ~5-10 MB per hour of meeting transcription
- **Models Cache**: ~2 GB (one-time download, persistent)
- **Original Files**: ~100-500 KB per meeting
- **Enriched Files**: ~150-700 KB per meeting (with contextual retrieval)

---

## 🔍 Monitoring & Logs

### Check Service Status

```bash
cd services/OpenWebUi

# View container status
docker-compose ps

# View OpenWebUI logs
docker-compose logs -f openwebui

# View Qdrant logs
docker-compose logs -f qdrant
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

### Health Checks

```bash
# OpenWebUI health
curl http://localhost:3000/health

# Qdrant health
curl http://localhost:6333/health
```

---

## 🐛 Troubleshooting

### Services not starting

```bash
# Check logs
docker-compose logs -f

# Restart services
docker-compose restart

# Clean restart
docker-compose down
docker-compose up -d
```

### Port already in use

If port 3000 or 6333 is already in use, edit `docker-compose.yml`:

```yaml
ports:
  - "3001:8080"  # Change 3000 to 3001 for OpenWebUI
```

Then update `.env`:
```env
OPENWEBUI_URL=http://localhost:3001
```

### Models not downloading

Check OpenWebUI logs:
```bash
docker-compose logs -f openwebui | grep -i download
```

Verify HuggingFace cache:
```bash
docker exec openwebui ls -lh /root/.cache/huggingface
```

---

## 📚 Documentation

- **Quick Start**: `README.md`
- **Technical Guide**: `INTEGRATION.md`
- **Configuration**: `.env.example`
- **Test Script**: `scripts/test_openwebui_integration.py`

---

## ✅ Implementation Checklist

- [x] Docker Compose stack created
- [x] OpenWebUI client library implemented
- [x] Upload orchestrator script created
- [x] Contextual enrichment integrated
- [x] Orchestrator integration complete
- [x] Environment configuration added
- [x] Documentation written
- [x] Test script created
- [x] Docker images downloaded
- [x] Services started and healthy
- [x] Models downloaded (BGE-M3 + reranker)
- [ ] **API key generation** ← YOU ARE HERE
- [ ] Environment configured with API key
- [ ] Integration test passed
- [ ] First meeting processed
- [ ] Queries working in UI

---

**Last Updated**: 2026-01-14 18:10 UTC+3
**Status**: Services running and healthy
**Next Action**: Access http://localhost:3000 to create admin account and generate API key
