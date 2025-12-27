# GPU-Enabled Transcription Service - Smoke Test Results

**Date:** 2025-12-27
**Test Video:** `123456_Видео_для_тестирования_доработок._mmmail(serg196@gmail.com)_2025-11-02_20-45-29 — копия (2).webm`
**Video Size:** 1.35 MB
**Video Duration:** 15.36 seconds

## Test Summary

### Status: PARTIAL SUCCESS ⚠

GPU configuration is correct, but the service crashed during processing of the first test run.

---

## Pre-Check Results

### 1. Docker Services: ✓ PASS
- **FFmpeg Service**: Healthy (Port 8002)
- **Transcription Service**: Healthy (Port 8003)

### 2. GPU Configuration: ✓ PASS
```json
{
  "whisper": {
    "model_size": "medium",
    "device": "cuda",       ← GPU Enabled ✓
    "compute_type": "float16",
    "framework": "faster-whisper"
  },
  "pyannote": {
    "framework": "pyannote.audio",
    "device": "cuda"        ← GPU Enabled ✓
  }
}
```

**Verification:** Both Whisper and pyannote are configured to use CUDA (GPU)

### 3. Test Video File: ✓ PASS
- Location: `C:\YandexDisk\DIASOFT\VideoPars\data\input\`
- Size: 1.35 MB
- Format: WebM

---

## Processing Results

### Step 1: Audio Extraction - ✓ SUCCESS
- Service: FFmpeg
- Output: `8bee670e-bb29-4dba-9d8b-fcf102e070ed.wav`
- Duration: 15.36 seconds
- Sample Rate: 16000 Hz
- Channels: 1 (mono)
- Processing Time: 0.29 seconds

### Step 2: Transcription & Diarization - ✗ FAILED

**Error:**
```
Exception: Transcription error: ('Connection aborted.', RemoteDisconnected('Remote end closed connection without response'))
```

**What Happened:**
1. Processing started successfully at 12:09:48
2. Both transcription and diarization launched in parallel
3. Whisper began processing (15.36s audio, VAD removed 2.13s)
4. Service restarted at 12:10:20 (approximately 32 seconds later)
5. No error message in logs - suggests container crash/kill

**Evidence of GPU Usage:**
- Logs show: `Processing audio with duration 00:15.360`
- TensorFloat-32 warning (confirms CUDA is active)
- No explicit error before restart

**Docker Configuration:**
- Health check interval: 60s
- Health check timeout: 30s
- Memory limit: 32GB (usage was only 2.3GB - no memory issue)
- Restart policy: `unless-stopped`

---

## Root Cause Analysis

### Most Likely Causes:

1. **Service Crash During First GPU Inference**
   - First time GPU processing after service start
   - CUDA initialization might have failed
   - No error logged (sudden termination)

2. **Possible Health Check Interference**
   - Health check timeout: 30s
   - If processing blocks the health endpoint for > 30s, Docker may kill the container
   - However, logs don't show failed health checks

3. **CUDA/GPU Driver Issue**
   - First actual GPU computation after service start
   - Driver compatibility or initialization problem
   - Silent failure causing process termination

### What We Know:
- GPU is available and configured correctly
- Models loaded successfully (Whisper + pyannote on CUDA)
- Audio extraction worked (FFmpeg)
- Processing started (transcription + diarization began)
- Service died approximately 32 seconds into processing
- Service auto-restarted successfully (restart policy working)

---

## Recommendations

### Immediate Actions:

1. **Run Test Again**
   - Service has restarted and models are loaded
   - Second attempt may succeed (if it was a first-run initialization issue)
   - Command:
     ```bash
     services/transcription_orchestrator/venv/Scripts/python.exe services/transcription_orchestrator/orchestrator.py "C:\YandexDisk\DIASOFT\VideoPars\data\input\123456_Видео_для_тестирования_доработок._mmmail(serg196@gmail.com)_2025-11-02_20-45-29 — копия (2).webm"
     ```

2. **Monitor Logs in Real-Time**
   ```bash
   docker-compose logs -f transcription-service
   ```
   Look for:
   - CUDA errors
   - Out of memory messages
   - Health check failures

3. **Check GPU Usage**
   ```bash
   nvidia-smi
   ```
   While processing is running to verify GPU utilization

### If Problem Persists:

1. **Increase Health Check Timeout**
   Edit `docker-compose.yml`:
   ```yaml
   healthcheck:
     timeout: 60s  # Increase from 30s
   ```

2. **Add Debug Logging**
   Enable verbose logging in transcription service to catch errors

3. **Test GPU Directly**
   Execute test inside container:
   ```bash
   docker exec -it meeting-transcription python -c "import torch; print(torch.cuda.is_available())"
   ```

4. **Check Service Logs File**
   ```bash
   type services\transcription\logs\transcription.log
   ```

5. **Fallback to CPU**
   If GPU continues to fail, temporarily switch to CPU:
   - Edit `.env`: `DEVICE=cpu`
   - Restart: `docker-compose restart transcription-service`

---

## Testing Checklist

- [x] Docker services healthy
- [x] GPU configuration verified
- [x] Test file verified
- [x] Audio extraction successful
- [ ] Transcription completed
- [ ] Diarization completed
- [ ] Speaker recognition (if enabled)
- [ ] Summary generation
- [ ] Protocol generation
- [ ] Output files validated

---

## Next Steps

1. **Retry the test** - Second attempt may succeed now that service has restarted
2. **Monitor GPU usage** with `nvidia-smi` during processing
3. **Check Docker logs** for any CUDA-related errors
4. If test succeeds, compare performance (GPU vs previous CPU times)
5. If test fails again, investigate CUDA/driver compatibility

---

## Automated Smoke Test Tool

Created: `test_gpu_smoke.py`

**Usage:**
```bash
# Run pre-checks and get command to execute
python test_gpu_smoke.py

# After processing, validate outputs
python test_gpu_smoke.py --validate
```

**Features:**
- Checks Docker service health
- Verifies GPU configuration
- Validates test file existence
- Cleans previous outputs
- Provides monitoring instructions
- Validates final outputs

---

## Appendix: Docker Container Info

**Container:** `meeting-transcription`
**Image:** `sha256:7ab95f8c1033df0e7f85afd36b8b46014ac05092ad89f5b8644a89cf006d2a42`
**Base Image:** `nvidia/cuda:12.2.2-cudnn8-runtime-ubuntu22.04`
**CUDA Version:** 12.2.2
**Memory Usage:** 2.3GB / 15.3GB (15.22%)
**CPU Usage:** 0.25%

**GPU Reservation:**
```yaml
devices:
  - driver: nvidia
    count: 1
    capabilities: [gpu]
```
