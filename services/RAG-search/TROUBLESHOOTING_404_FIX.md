# RAGFlow 404 Error Fix - Documentation

## Problem
When accessing http://localhost:9380, the browser displayed:
```json
{"error":"Not Found","message":"The requested URL / was not found"}
```

## Root Cause
The docker-compose configuration had an incorrect port mapping and was missing nginx configuration files.

### Issues Found:
1. **Wrong port mapping**: `9380:9380` mapped host port 9380 directly to the Flask API (port 9380 in container), bypassing nginx
2. **Missing nginx configuration**: No nginx config files were mounted to serve the React web UI
3. **Default nginx config**: The container's default nginx config served from `/var/www/html` instead of `/ragflow/web/dist`

### Architecture Understanding:
- RAGFlow uses a **two-tier architecture**:
  - **Nginx** (port 80 inside container): Serves React UI and proxies API requests
  - **Flask API** (port 9380 inside container): Backend API server
  - **Admin API** (port 9381 inside container): Admin endpoints

The correct flow:
```
Browser → localhost:9380 → Container port 80 (nginx) → Serves UI or proxies to port 9380 (Flask)
```

The incorrect flow we had:
```
Browser → localhost:9380 → Container port 9380 (Flask API directly) → 404 error
```

## Solution

### 1. Created Nginx Configuration Files

**`services/RAG-search/nginx/ragflow.conf`**:
- Listens on port 80
- Serves web UI from `/ragflow/web/dist`
- Proxies `/api` and `/v1` to `localhost:9380` (Flask)
- Proxies `/api/v1/admin` to `localhost:9381` (Admin API)
- Configures static asset caching

**`services/RAG-search/nginx/nginx.conf`**:
- Main nginx configuration
- Sets worker processes, logging, upload limits
- Includes ragflow.conf

**`services/RAG-search/nginx/proxy.conf`**:
- Proxy headers configuration
- Timeouts and buffer sizes

### 2. Updated docker-compose.ragflow.yml

Changed:
```yaml
ports:
  - "9380:9380"  # WRONG - maps to Flask API directly
```

To:
```yaml
ports:
  - "9380:80"    # CORRECT - maps to nginx
  - "9381:9381"  # Admin API (unchanged)
```

Added volume mounts:
```yaml
volumes:
  # ... existing volumes ...
  # Nginx configuration
  - ./nginx/ragflow.conf:/etc/nginx/conf.d/ragflow.conf:ro
  - ./nginx/proxy.conf:/etc/nginx/proxy.conf:ro
  - ./nginx/nginx.conf:/etc/nginx/nginx.conf:ro
```

### 3. Recreated Container

Important: Restarting wasn't enough - the container needed to be recreated to mount new volumes:

```bash
cd services/RAG-search
docker-compose -f docker-compose.ragflow.yml down ragflow
docker-compose -f docker-compose.ragflow.yml up -d ragflow
```

## Verification

After the fix, accessing http://localhost:9380 returns the proper RAGFlow React UI:

```html
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>RAGFlow</title>
<link rel="stylesheet" href="/umi.e1d2ffa6.css">
...
```

## Key Learnings

1. **Read official docker-compose carefully**: The official RAGFlow docker-compose uses nginx config mounts that we initially missed
2. **Port mappings matter**: Understand which internal port serves what (nginx vs. API)
3. **Container recreation required**: Volume changes require `down` + `up`, not just `restart`
4. **Check official examples**: When in doubt, reference the official RAGFlow repository for proper configuration

## Related Issues

- [GitHub Issue #3143](https://github.com/infiniflow/ragflow/issues/3143) - 404 not found when opening RAGFlow page
- [GitHub Issue #5250](https://github.com/infiniflow/ragflow/issues/5250) - 404 Not Found errors
- [GitHub Issue #7058](https://github.com/infiniflow/ragflow/issues/7058) - How to deploy web server on custom domain

## Testing Checklist

- [x] Web UI accessible at http://localhost:9380
- [x] Returns HTML with title "RAGFlow"
- [x] Static assets (CSS, JS) loading correctly
- [ ] Login page appears (next step: create API key)
- [ ] API endpoints work via nginx proxy

---

**Fixed**: 2026-01-10
**Time to fix**: ~30 minutes
**Status**: ✅ Resolved - Web UI now accessible
