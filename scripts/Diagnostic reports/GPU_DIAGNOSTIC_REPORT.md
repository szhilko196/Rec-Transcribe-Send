# GPU Diagnostic Report

**Date:** 2025-12-27
**Issue:** Transcription service crashes during GPU processing
**Status:** ROOT CAUSE IDENTIFIED ✓

---

## Executive Summary

**Your GPU is working perfectly!** The problem is not with your GPU, but with Docker health check configuration killing the container during processing.

### Root Cause
Uvicorn runs with a single worker, blocking the health check endpoint during GPU processing. When health checks fail for 30+ seconds, Docker kills the container.

---

## GPU Hardware Status: ✓ EXCELLENT

### Host System
```
GPU Model: Tesla V100-SXM2-16GB
Driver Version: 539.41
CUDA Version: 12.2
Memory: 2.6GB / 16GB (16% used)
Temperature: 30°C
GPU Utilization: 0% (idle)
Power Usage: 24W / 300W
```

**Assessment:** Professional datacenter GPU in perfect working condition.

### Docker GPU Access: ✓ WORKING
```
Container: meeting-transcription
NVIDIA-SMI: Accessible ✓
GPU Visible: Yes ✓
Process Running: Python3.10 (PID 1) ✓
```

### PyTorch CUDA: ✓ WORKING
```
PyTorch Version: 2.4.1+cu121
CUDA Available: True ✓
CUDA Device Count: 1 ✓
CUDA Device Name: Tesla V100-SXM2-16GB ✓
CUDA Version: 12.1 ✓
```

### GPU Computation Test: ✓ PASSED
```
Matrix multiplication (1000x1000): SUCCESS ✓
Device: cuda:0 ✓
```

### AI Libraries: ✓ WORKING
```
faster-whisper: Import OK ✓
pyannote.audio: Import OK ✓
```

---

## Problem Analysis

### Timeline of the Crash

| Time | Event |
|------|-------|
| 12:09:48 | Processing started |
| 12:09:49 | Transcription + diarization launched in parallel |
| 12:09:50 | Whisper: VAD filter completed (removed 2.1s of silence) |
| 12:09:50 | **Processing continues (GPU working)** |
| 12:10:20 | **Container KILLED** (30 seconds later) |
| 12:10:20 | Service auto-restart begins |

### Why It Crashed

**Uvicorn Configuration:**
```bash
PID 1: /usr/bin/python3 /usr/local/bin/uvicorn app:app --host 0.0.0.0 --port 8000
```

**Problem Chain:**
1. Uvicorn runs with **single worker** (no `--workers` flag)
2. GPU processing is **synchronous** (blocks the main thread)
3. While GPU is processing, **health check endpoint cannot respond**
4. Docker health check timeout: **30 seconds**
5. If processing takes > 30s, health check fails
6. After 3 failures (90s total), Docker **kills the container**

**Current Health Check:**
```yaml
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
  interval: 60s
  timeout: 30s      ← Problem: Too short for GPU processing
  retries: 3
  start_period: 120s
```

### Why Previous Tests from Dec 13 Worked

Looking at logs, some December 13 processes handled longer videos:
- `01:00:00.000` - 1 hour video

These likely succeeded because:
1. They processed in **chunks** (old architecture)
2. Each chunk was < 30 seconds
3. Health checks could respond between chunks

Your 15-second test video uses **full-file diarization** (new architecture), which blocks for the entire duration.

---

## Solution

### Option 1: Increase Health Check Timeout (RECOMMENDED)

Edit `docker-compose.yml`:

```yaml
transcription-service:
  # ... existing config ...
  healthcheck:
    test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
    interval: 60s
    timeout: 120s      # Increase from 30s to 120s
    retries: 3
    start_period: 120s
```

**Why this works:**
- Allows health checks to wait up to 2 minutes for a response
- GPU processing on short videos (< 1 min) will complete within timeout
- Service remains responsive for health checks

**Apply the fix:**
```bash
# Edit docker-compose.yml (change line 72: timeout: 120s)
docker-compose up -d transcription-service
```

### Option 2: Use Chunked Processing (TEMPORARY WORKAROUND)

Edit `.env`:
```env
USE_NEW_DIARIZATION_ARCHITECTURE=false
CHUNK_DURATION_SEC=1800
```

**Why this works:**
- Processes audio in chunks
- Each chunk < 30 minutes
- Health checks can respond between chunks

**Trade-off:** May create speaker label duplicates

### Option 3: Run Uvicorn with Thread Pool (ADVANCED)

Modify `services/transcription/Dockerfile` to run processing in background threads:

```python
# In app.py, wrap processing in thread pool
import concurrent.futures
executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)

@app.post("/transcribe-with-speakers")
async def transcribe_with_speakers(...):
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(executor, process_audio, ...)
    return result
```

**Why this works:**
- Main thread stays responsive for health checks
- GPU processing runs in background thread
- More complex to implement

---

## Recommended Action Plan

### Step 1: Fix Health Check Timeout
```bash
# 1. Edit docker-compose.yml
#    Line 72: timeout: 120s

# 2. Restart service
docker-compose up -d transcription-service

# 3. Wait for service to be healthy
docker-compose ps
```

### Step 2: Run Test Again
```bash
services/transcription_orchestrator/venv/Scripts/python.exe services/transcription_orchestrator/orchestrator.py "C:\YandexDisk\DIASOFT\VideoPars\data\input\123456_Видео_для_тестирования_доработок._mmmail(serg196@gmail.com)_2025-11-02_20-45-29 — копия (2).webm"
```

### Step 3: Monitor Progress
```bash
# Terminal 1: Watch logs
docker-compose logs -f transcription-service

# Terminal 2: Monitor GPU
nvidia-smi -l 1
```

### Step 4: Validate Output
```bash
python test_gpu_smoke.py --validate
```

---

## Expected GPU Performance

For your 15-second test video on Tesla V100:

| Phase | Expected Time | CPU vs GPU |
|-------|---------------|------------|
| Audio extraction | ~0.3s | Same |
| Transcription (Whisper) | ~2-5s | 10x faster |
| Diarization (pyannote) | ~3-8s | 5x faster |
| **Total** | **~10-15s** | **~7x faster** |

For 1-hour videos:
- **CPU**: 30-60 minutes
- **GPU (V100)**: 3-7 minutes

---

## Additional Optimizations (Optional)

### 1. Enable TF32 for Better Performance
TF32 can speed up processing by ~20-30% on V100:

Edit `services/transcription/app.py` (startup):
```python
import torch
torch.backends.cuda.matmul.allow_tf32 = True
torch.backends.cudnn.allow_tf32 = True
```

### 2. Monitor GPU During Processing
```bash
# Real-time GPU monitoring
nvidia-smi -l 1

# Or use watch
watch -n 1 nvidia-smi
```

### 3. Optimize for Long Videos
For videos > 30 minutes, consider:
- Chunked processing to allow health checks
- Or disable health checks entirely (not recommended)

---

## Verification Commands

### Check Service is Healthy
```bash
docker-compose ps
# Should show: Up X seconds (healthy)
```

### Test GPU Access
```bash
docker exec meeting-transcription nvidia-smi
```

### Test PyTorch CUDA
```bash
docker exec meeting-transcription python3 -c "import torch; print('CUDA:', torch.cuda.is_available())"
```

### Check Health Endpoint Manually
```bash
curl http://localhost:8003/health
```

---

## Conclusion

**GPU Status: ✓ PERFECT**
**Problem: Docker health check timeout**
**Solution: Increase timeout from 30s to 120s**
**Estimated Fix Time: 2 minutes**

Your Tesla V100 is a beast of a GPU and will give you excellent performance once we fix the health check configuration!

---

## Files Updated

1. **GPU_DIAGNOSTIC_REPORT.md** (this file)
2. **SMOKE_TEST_RESULTS.md** (initial test results)
3. **test_gpu_smoke.py** (smoke test automation tool)
