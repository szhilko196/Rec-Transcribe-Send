"""
Manual merging of transcription results for long video
"""
import json
from pathlib import Path

# File paths
chunk_0_path = Path("data/transcripts/9b83cd21-6cf8-42a2-bee7-b9c3e0969687_full_transcript.json")
chunk_1_path = Path("data/transcripts/27e13429-6a1e-4734-93c7-19ad38b9eaf8_full_transcript.json")
output_path = Path("data/results/Встреча в Телемосте 21.10.25 14-50-34 — запись_20251021_224838/transcript_full.json")

# Chunk duration
CHUNK_DURATION = 1800  # 30 minutes

# Read chunks
with open(chunk_0_path, 'r', encoding='utf-8') as f:
    chunk_0 = json.load(f)

with open(chunk_1_path, 'r', encoding='utf-8') as f:
    chunk_1 = json.load(f)

# Merge segments
merged_segments = []

# First chunk without changes
for segment in chunk_0['transcript']:
    merged_segments.append(segment)

# Second chunk with time offset
for segment in chunk_1['transcript']:
    merged_segment = segment.copy()
    merged_segment['start'] += CHUNK_DURATION
    merged_segment['end'] += CHUNK_DURATION
    merged_segments.append(merged_segment)

# Create final result
merged_result = {
    "metadata": {
        "original_filename": "Встреча в Телемосте 21.10.25 14-50-34 — запись.webm",
        "duration_seconds": chunk_0['metadata']['duration_seconds'] + chunk_1['metadata']['duration_seconds'],
        "num_speakers": max(chunk_0['metadata']['num_speakers'], chunk_1['metadata']['num_speakers']),
        "language": "ru",
        "processed_at": chunk_1['metadata']['processed_at']
    },
    "transcript": merged_segments,
    "num_segments": len(merged_segments)
}

# Save
output_path.parent.mkdir(parents=True, exist_ok=True)
with open(output_path, 'w', encoding='utf-8') as f:
    json.dump(merged_result, f, ensure_ascii=False, indent=2)

print(f"[OK] Transcript merged!")
print(f"   File: {output_path}")
print(f"   Segments: {len(merged_segments)}")
print(f"   Duration: {merged_result['metadata']['duration_seconds']:.1f}s")
print(f"   Speakers: {merged_result['metadata']['num_speakers']}")
