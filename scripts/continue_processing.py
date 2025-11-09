"""
Continue processing after merging transcripts
"""
import json
import sys
from pathlib import Path

# Add path to orchestrator
sys.path.append(str(Path(__file__).parent))

from orchestrator import generate_summary_and_protocol, generate_formatted_transcript, organize_files

# Path to merged transcript
result_folder = Path("data/results/Встреча в Телемосте 21.10.25 14-50-34 — запись_20251021_224838")
transcript_path = result_folder / "transcript_full.json"
video_path = Path("data/input/Встреча в Телемосте 21.10.25 14-50-34 — запись.webm")

# Read transcript
print(f"Loading transcript: {transcript_path}")
with open(transcript_path, 'r', encoding='utf-8') as f:
    full_transcript = json.load(f)

print(f"  Segments: {len(full_transcript['transcript'])}")
print(f"  Speakers: {full_transcript['metadata']['num_speakers']}")

# Create readable version
print("\nCreating readable version of transcript...")
formatted_transcript = generate_formatted_transcript(full_transcript)
readable_path = result_folder / "transcript_readable.txt"
with open(readable_path, 'w', encoding='utf-8') as f:
    f.write(formatted_transcript)
print(f"  Saved: {readable_path}")

# Generate summary and protocol through Claude
print("\n[STEP 3] Generating summary and protocol through Claude API...")
print("  WARNING: This may take 5-10 minutes!")

claude_info = generate_summary_and_protocol(full_transcript, result_folder)

print(f"\n[OK] Documents generated:")
print(f"  Summary: {claude_info['summary_path']}")
print(f"  Protocol: {claude_info['protocol_path']}")

# Copy video
print(f"\n[STEP 4] Copying source video...")
dest_video = result_folder / f"original_{video_path.name}"
if not dest_video.exists():
    import shutil
    shutil.copy2(video_path, dest_video)
    print(f"[OK] Video copied: {dest_video.name}")
else:
    print(f"[OK] Video already copied")

# Delete temporary chunk files
print(f"\nCleaning up temporary files...")
for chunk_file in result_folder.glob("audio_chunk_*.wav"):
    chunk_file.unlink()
    print(f"  Deleted: {chunk_file.name}")

print(f"\n" + "="*80)
print(f"[SUCCESS] Processing completed!")
print(f"  Results folder: {result_folder}")
print(f"="*80)
