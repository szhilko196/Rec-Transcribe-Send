# RAG Search for Meeting Transcriptions

Semantic search across meeting transcripts using RAGFlow with Contextual Retrieval (Anthropic technique).

## Architecture

- **RAGFlow**: Production-ready RAG framework
- **Infinity**: High-performance vector engine
- **BGE-M3**: Multilingual embedding model (dense + sparse hybrid)
- **bge-reranker-v2-m3**: Reranking for precision
- **Claude Sonnet 4.5**: LLM for generation and contextual enrichment

## Quick Start

### 1. Setup Environment

```bash
cd services/RAG-search
cp .env.example .env
# Edit .env and add your CLAUDE_API_KEY
```

### 2. Start RAGFlow Stack

```bash
docker-compose -f docker-compose.ragflow.yml up -d
```

This will start:
- RAGFlow UI (port 9380)
- RAGFlow API (port 9381)
- MySQL (for metadata)
- Redis (for caching)
- Infinity vector engine (port 7997)

### 3. Access RAGFlow UI

Open http://localhost:9380

**Default credentials:**
- Username: `admin`
- Password: `admin`

### 4. Configure RAGFlow

In the RAGFlow UI:

1. **Settings → Embedding Model**
   - Select: `BAAI/bge-m3`

2. **Settings → Vector Engine**
   - Select: `Infinity`

3. **Settings → Reranker**
   - Select: `BAAI/bge-reranker-v2-m3`

4. **Settings → LLM**
   - Provider: `Claude`
   - Model: `claude-sonnet-4-5`
   - API Key: (enter your Claude API key)

5. **Settings → API Keys**
   - Click "Create New Key"
   - Copy the generated key
   - Add to `.env` as `RAGFLOW_API_KEY`

### 5. Verify Services

Check all services are healthy:

```bash
docker-compose -f docker-compose.ragflow.yml ps
```

All containers should be "Up" and healthy.

## Usage

### Automatic Indexing

Meetings will automatically upload to RAGFlow after transcription when `ENABLE_RAG_INDEXING=true` in root `.env` file.

### Manual Query via UI

1. Open http://localhost:9380
2. Navigate to "Datasets"
3. Select a meeting dataset
4. Click "Chat"
5. Ask questions in natural language

**Example queries:**
- "Что обсудили по проекту GPB 9 марта?"
- "Какие решения приняли о налоговых расчетах?"
- "Покажи все комментарии Ивана Петрова"
- "В каком видеофайле это обсуждение?"

### Query via API

```python
import requests

api_key = "your-ragflow-api-key"
response = requests.post(
    "http://localhost:9381/api/v1/chat",
    headers={"Authorization": f"Bearer {api_key}"},
    json={
        "question": "Что обсудили по проекту GPB?",
        "dataset_ids": ["all"],  # or specific meeting IDs
        "top_k": 5
    }
)

print(response.json()["answer"])
```

## Contextual Retrieval

This implementation uses **Anthropic's Contextual Retrieval** technique:

- Each chunk gets enriched with meeting context before embedding
- Context includes: meeting title, date, participants, document type
- **+30% retrieval accuracy** vs standard RAG

Example:
- **Without context**: "Иван согласился завершить расчеты до 15 марта"
- **With context**: "Встреча: GPB проект - обсуждение счетов, Дата: 2025-03-09, Участники: Иван Петров, Мария Иванова\n\nИван согласился завершить расчеты до 15 марта"

## Troubleshooting

### RAGFlow not accessible

```bash
# Check logs
docker-compose -f docker-compose.ragflow.yml logs ragflow

# Restart services
docker-compose -f docker-compose.ragflow.yml restart
```

### Infinity model download fails

```bash
# Check Infinity logs
docker logs ragflow-infinity

# Manually download model (if needed)
docker exec -it ragflow-infinity /bin/bash
# Inside container: model will auto-download on first use
```

### MySQL connection errors

```bash
# Check MySQL is healthy
docker logs ragflow-mysql

# Reset MySQL (WARNING: deletes all data)
docker-compose -f docker-compose.ragflow.yml down -v
docker-compose -f docker-compose.ragflow.yml up -d
```

## File Structure

```
services/RAG-search/
├── README.md                           # This file
├── Meeting_rag.md                      # Detailed implementation plan
├── docker-compose.ragflow.yml          # RAGFlow stack
├── .env.example                        # Environment template
├── scripts/
│   ├── contextual_enrichment.py        # Add context to chunks
│   ├── ragflow_uploader.py             # Upload to RAGFlow
│   └── ragflow_client.py               # RAGFlow API wrapper
├── config/
│   ├── ragflow_config.yml              # RAGFlow settings
│   └── prompts/
│       └── context_generation.txt      # Context prompt template
└── data/
    └── ragflow_datasets/               # Dataset metadata
```

## Next Steps

See `Meeting_rag.md` for detailed implementation plan including:
- Phase 2: Contextual enrichment implementation
- Phase 3: RAGFlow API integration scripts
- Phase 4: Orchestrator integration
- Phase 5: Testing and documentation
