@echo off
echo ======================================
echo OpenWebUI RAG Activity Monitor
echo ======================================
echo.
echo Watching for RAG queries in real-time...
echo Press Ctrl+C to stop
echo.

cd /d "%~dp0"
docker-compose logs -f --tail 0 openwebui | findstr /I "retrieval hybrid_search query_collection vector embedding rag"
