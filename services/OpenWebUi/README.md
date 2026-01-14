# OpenWebUI RAG Search

Semantic search across meeting transcriptions using OpenWebUI with Contextual Retrieval (Anthropic's technique for +30% retrieval accuracy).

## Architecture

```
Meeting transcription → Contextual enrichment (Claude Sonnet 4.5)
    → OpenWebUI API upload → Async processing
    → BGE-M3 embedding (SentenceTransformers) → Qdrant vector storage
    → User query → Hybrid search (BM25 + semantic)
    → bge-reranker-v2-m3 reranking → Claude Haiku 4.5 generation
```

## Technology Stack

- **UI/Orchestration**: OpenWebUI (ghcr.io/open-webui/open-webui:main)
- **Embedding Model**: BGE-M3 (via SentenceTransformers built-in)
- **Vector Database**: Qdrant
- **Reranker**: bge-reranker-v2-m3
- **LLM**: Claude Haiku 4.5 API
- **Contextual Retrieval**: Claude Sonnet 4.5 for context generation

## Quick Start

### 1. Start OpenWebUI Stack

```bash
cd services/OpenWebUi
docker-compose up -d

# Wait for services to be ready (~30 seconds)
docker-compose logs -f openwebui
# BGE-M3 and reranker models will download automatically on first use
```

### 2. Configure OpenWebUI

1. Open http://localhost:3000
2. Create admin account (first user becomes admin)
3. Go to Settings > Account > API Keys
4. Generate API key and copy it
5. Add to root `.env`: `OPENWEBUI_API_KEY=your-key-here`

### 3. Enable in Orchestrator

Edit root `.env`:
```env
ENABLE_OPENWEBUI_RAG=true
OPENWEBUI_URL=http://localhost:3000
OPENWEBUI_API_KEY=your-key-here
ENABLE_CONTEXTUAL_RETRIEVAL=true
```

### 4. Process Meetings

Meetings will automatically index to OpenWebUI:

```bash
# Manual processing
python services/transcription_orchestrator/orchestrator.py data/input/meeting.avi

# Or use auto-processing
# Just place videos in data/input/ folder
```

## Querying Meetings

### Via OpenWebUI UI

1. Open http://localhost:3000
2. In chat, type `#Meetings` to reference the Knowledge Base
3. Ask questions like:
   - "Что обсудили по проекту GPB 9 марта?"
   - "Кто отвечает за расчеты до 15 марта?"
   - "В каком видео обсуждали счета?"

### Via API

```python
from scripts.openwebui_client import OpenWebUIClient

client = OpenWebUIClient(
    base_url="http://localhost:3000",
    api_key="your-api-key"
)

# Check health
if client.health_check():
    print("✓ OpenWebUI accessible")

# List knowledge bases
kbs = client.list_knowledge_bases()
for kb in kbs:
    print(f"  - {kb['name']} (ID: {kb['id']})")
```

## Configuration

See `.env.example` for all available options.

### Key Environment Variables

- **ENABLE_OPENWEBUI_RAG**: Enable/disable automatic indexing (default: `false`)
- **OPENWEBUI_URL**: OpenWebUI service URL (default: `http://localhost:3000`)
- **OPENWEBUI_API_KEY**: API key for authentication (generate in UI)
- **ENABLE_CONTEXTUAL_RETRIEVAL**: Enable contextual enrichment (default: `true`)
- **CONTEXT_GENERATION_MODEL**: Claude model for context generation

### Contextual Retrieval

Contextual Retrieval prepends meeting context to each chunk before embedding:

**Without context:**
```
"Иван согласился завершить расчеты до 15 марта"
```

**With context (Anthropic's technique):**
```
Встреча: meeting_20250309_143022, дата: 2025-03-09, участники: Иван Петров, Мария Иванова

Иван согласился завершить расчеты до 15 марта
```

**Benefits:**
- +30% retrieval accuracy (Anthropic benchmark)
- Better cross-meeting queries
- Implicit metadata filtering through semantic search

**Cost:**
- Adds ~2-5 minutes per meeting (Claude API calls)
- Can be disabled: `ENABLE_CONTEXTUAL_RETRIEVAL=false`

## Troubleshooting

### OpenWebUI not accessible

- Check containers: `docker-compose ps`
- View logs: `docker-compose logs -f openwebui`
- Wait 30s for startup

### Upload fails with "401 Unauthorized"

- Generate API key in OpenWebUI UI
- Add to `.env`: `OPENWEBUI_API_KEY=your-key-here`

### BGE-M3 model not downloading

- Model downloads automatically on first file upload
- Check logs: `docker-compose logs -f openwebui`
- Check HuggingFace cache: `docker exec openwebui ls -lh /root/.cache/huggingface`
- Model size: ~2GB, may take 5-10 minutes on first upload

### Poor retrieval quality

- Enable contextual retrieval: `ENABLE_CONTEXTUAL_RETRIEVAL=true`
- Adjust relevance threshold (lower = more results)
- Check hybrid search is enabled
- Verify reranker model is loaded

### Slow indexing

- Contextual enrichment calls Claude API (~2-5 min per meeting)
- Disable for faster indexing: `ENABLE_CONTEXTUAL_RETRIEVAL=false` (not recommended)
- Model download on first upload: ~5-10 min (one-time)

### Docker containers consuming too many resources

- OpenWebUI stack requires ~4GB RAM minimum
- BGE-M3 embedding model: ~2GB disk space (first run download)
- Qdrant vector database: ~5-10MB per hour of meeting transcription
- Adjust Docker Desktop memory limit: Settings → Resources → Memory

## Performance Expectations

### Indexing Performance

- **With Contextual Enrichment**: 3-5 min per meeting
  - Context generation: 2-4 min (Claude API calls)
  - Upload + embedding: 1 min
- **Without Enrichment**: 30-60 seconds per meeting
  - Upload + embedding only

### Query Performance

- **Search**: 200-500ms (hybrid search + reranking)
- **Chat** (with Claude Haiku): 2-4 seconds (retrieval + generation)

### Storage

- **Vector DB**: ~5-10MB per hour of meeting transcription
- **Original files**: ~100-500KB per meeting
- **Enriched files**: ~150-700KB per meeting (30-40% larger)

## Docker Commands

```bash
# Start stack
docker-compose up -d

# Stop stack
docker-compose down

# View logs
docker-compose logs -f openwebui
docker-compose logs -f qdrant

# Restart service
docker-compose restart openwebui

# Check status
docker-compose ps

# Clean rebuild
docker-compose down
docker volume rm openwebui_openwebui_data openwebui_qdrant_data openwebui_models_cache
docker-compose up -d --build
```

## Data Persistence

All data is stored in Docker volumes:

- `./openwebui_data/` - OpenWebUI application data
- `./qdrant_data/` - Qdrant vector storage
- `./models_cache/` - BGE-M3 and reranker models

**Backup:**
```bash
# Backup volumes
docker-compose down
tar -czf openwebui_backup_$(date +%Y%m%d).tar.gz openwebui_data/ qdrant_data/ models_cache/

# Restore from backup
tar -xzf openwebui_backup_20250115.tar.gz
docker-compose up -d
```

## Additional Resources

- [OpenWebUI Documentation](https://docs.openwebui.com/)
- [OpenWebUI RAG Features](https://docs.openwebui.com/features/rag/)
- [Qdrant Documentation](https://qdrant.tech/documentation/)
- [BGE-M3 Model Card](https://huggingface.co/BAAI/bge-m3)
- [Contextual Retrieval (Anthropic)](https://www.anthropic.com/news/contextual-retrieval)

## Support

For issues or questions:
- Check troubleshooting section above
- Review logs: `docker-compose logs -f`
- See `INTEGRATION.md` for detailed integration guide
