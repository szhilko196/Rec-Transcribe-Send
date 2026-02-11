# Bank-Specific Knowledge Bases (v1.5.0)

Automatically organize meeting transcripts into separate Knowledge Bases per bank for targeted semantic search.

## Overview

The Bank KB feature extracts bank names from meeting video filenames and creates dedicated Knowledge Bases in OpenWebUI for each bank. This enables:

- **Isolated search**: Query only relevant bank meetings
- **Better organization**: Separate transcripts by client/bank
- **Telegram bot support**: Use `/kb BANKNAME` to switch context
- **Auto-detection**: No manual tagging required

## Quick Start

### 1. Enable the Feature

Ensure `ENABLE_BANK_SPECIFIC_KBS=true` in `.env`:

```bash
# .env
ENABLE_BANK_SPECIFIC_KBS=true
```

### 2. Name Your Video Files

Use bank prefix in video filenames:

```
ГПБ_Архитектурные_вопросы.avi          → KB: GPB
СБЕРБАНК_Старт_работ.avi                → KB: SBERBANK
ПСБ_Встреча_команды.avi                 → KB: PSB
meeting_without_prefix.avi              → KB: Meetings (fallback)
```

### 3. Process the Video

```bash
# Copy video to input folder
cp ГПБ_Архитектурные_вопросы.avi data/input/

# Orchestrator auto-detects and processes
# Result: data/results/ГПБ_Архитектурные_вопросы_20250115_143022/
```

### 4. Query in OpenWebUI

```
Open: http://localhost:3000
Type: #GPB What were the action items?
```

### 5. Query via Telegram Bot

```
/kb GPB
What were the architectural decisions?
```

## How It Works

### Architecture

```
Video Filename
  ↓
Result Folder: BANKNAME_Description_YYYYMMDD_HHMMSS
  ↓
Bank KB Resolver (bank_kb_resolver.py)
  ├─ Extract bank prefix from folder name
  ├─ Normalize Cyrillic → Latin (ГПБ → GPB)
  ├─ Lookup in bank_kb_mapping.json
  └─ Return KB name + metadata
  ↓
OpenWebUI Uploader (openwebui_uploader.py)
  ├─ Create/use Knowledge Base
  ├─ Upload files to KB
  └─ Save bank info to metadata.json
  ↓
OpenWebUI RAG
  └─ Query with #BANKNAME filter
```

### Bank Name Resolution

1. **Folder name pattern**: `{video_name}_{YYYYMMDD_HHMMSS}`
2. **Extract prefix**: First segment before underscore
3. **Normalize**: Convert to uppercase (ГПБ, гпб → GPB)
4. **Lookup**: Check `bank_kb_mapping.json` for mapping
5. **Fallback**: Unknown banks → "Meetings" KB

### Examples

| Video Filename | Result Folder | KB Name | Query |
|----------------|---------------|---------|-------|
| `ГПБ_meeting.avi` | `ГПБ_meeting_20250115_143022` | GPB | `#GPB` |
| `ГАЗПРОМБАНК_test.avi` | `ГАЗПРОМБАНК_test_20250115_143022` | GPB (alias) | `#GPB` |
| `СБЕРБАНК_call.avi` | `СБЕРБАНК_call_20250115_143022` | SBERBANK | `#SBERBANK` |
| `СБЕР_sync.avi` | `СБЕР_sync_20250115_143022` | SBERBANK (alias) | `#SBERBANK` |
| `ПСБ_review.avi` | `ПСБ_review_20250115_143022` | PSB | `#PSB` |
| `meeting.avi` | `meeting_20250115_143022` | Meetings | `#Meetings` |

## Configuration

### Bank Mapping File

**Location**: `services/OpenWebUi/scripts/bank_kb_mapping.json`

```json
{
  "enabled": true,
  "fallback_kb": "Meetings",
  "mappings": {
    "ГПБ": {
      "kb_name": "GPB",
      "full_name": "Газпромбанк",
      "description": "Meeting transcripts for Gazprombank"
    },
    "ГАЗПРОМБАНК": {
      "kb_name": "GPB",
      "full_name": "Газпромбанк",
      "description": "Meeting transcripts for Gazprombank"
    },
    "СБЕРБАНК": {
      "kb_name": "SBERBANK",
      "full_name": "Сбербанк",
      "description": "Meeting transcripts for Sberbank"
    },
    "СБЕР": {
      "kb_name": "SBERBANK",
      "full_name": "Сбербанк",
      "description": "Meeting transcripts for Sberbank"
    },
    "ПСБ": {
      "kb_name": "PSB",
      "full_name": "ПСБанк",
      "description": "Meeting transcripts for PSBank"
    }
  }
}
```

### Configuration Fields

- **`enabled`**: Enable/disable bank KB feature (boolean)
- **`fallback_kb`**: Default KB name for unrecognized banks (string)
- **`mappings`**: Dictionary of bank prefix → KB info
  - **Key**: Bank prefix (Cyrillic or Latin, case-insensitive)
  - **Value**: Object with:
    - `kb_name`: Normalized KB name (e.g., "GPB")
    - `full_name`: Full bank name in Russian (e.g., "Газпромбанк")
    - `description`: KB description for OpenWebUI

### Adding New Banks

**Step 1**: Edit `bank_kb_mapping.json`

```json
"АЛЬФАБАНК": {
  "kb_name": "ALFABANK",
  "full_name": "Альфа-Банк",
  "description": "Meeting transcripts for Alfa Bank"
}
```

**Step 2**: Process a video with the new prefix

```bash
cp АЛЬФАБАНК_meeting.avi data/input/
```

**Step 3**: Verify KB was created

```bash
# Check OpenWebUI UI for "ALFABANK" Knowledge Base
# Or query: #ALFABANK test query
```

No code changes or restarts required!

### Multiple Aliases

Map multiple prefixes to the same KB:

```json
"ГПБ": {
  "kb_name": "GPB",
  "full_name": "Газпромбанк",
  "description": "Meeting transcripts for Gazprombank"
},
"ГАЗПРОМБАНК": {
  "kb_name": "GPB",
  "full_name": "Газпромбанк",
  "description": "Meeting transcripts for Gazprombank"
},
"GPB": {
  "kb_name": "GPB",
  "full_name": "Gazprombank",
  "description": "Meeting transcripts for Gazprombank"
}
```

All three prefixes → same "GPB" Knowledge Base.

## Testing

### Unit Tests

Test bank name extraction and normalization:

```bash
cd services/OpenWebUi/scripts
python test_bank_kb_resolver.py
```

**Expected output**:
```
=== Testing Bank KB Resolver ===

Test 1: Extract Cyrillic bank prefix
[PASS] ГПБ_Архитектурные_вопросы_20250115_143022 -> ГПБ
[PASS] СБЕРБАНК_Старт_работ_20250115_143022 -> СБЕРБАНК
...

=== All tests passed! ===
```

### Integration Tests

Test folder → KB resolution:

```bash
python test_bank_integration.py
```

**Expected output**:
```
[PASS] ГПБ_meeting_20250115_143022
       → KB: 'GPB' (Bank: Газпромбанк)
[PASS] meeting_20250115_143022
       → KB: 'Meetings' (No bank detected)
...
```

### Dry-Run Test

Simulate uploader without OpenWebUI:

```bash
python test_uploader_dryrun.py
```

**Expected output**:
```
[Step 2/7] Resolving Knowledge Base...
Result folder: ГПБ_meeting_20250115_143022
[INFO] Bank detected: Газпромбанк → KB: 'GPB'
[✓] Knowledge Base resolved: 'GPB'
...
```

### End-to-End Test

1. **Create test video** with bank prefix:
```bash
cp test_video.avi data/input/ГПБ_test_meeting.avi
```

2. **Wait for processing** (orchestrator auto-detects)

3. **Check result folder**:
```bash
ls data/results/ГПБ_test_meeting_*/
# Should contain: metadata.json with bank info
```

4. **Verify metadata**:
```bash
cat data/results/ГПБ_test_meeting_*/metadata.json | grep bank
```

**Expected**:
```json
"bank_name": "GPB",
"bank_full_name": "Газпромбанк",
"bank_detected_from": "folder_name",
"openwebui_knowledge_base_name": "GPB"
```

5. **Query in OpenWebUI**:
```
#GPB What was discussed in the test meeting?
```

6. **Query via Telegram**:
```
/kb GPB
What was discussed?
```

## Troubleshooting

### Bank Not Recognized

**Symptom**: Video with bank prefix goes to "Meetings" KB instead of bank-specific KB.

**Causes**:
1. Bank not in `bank_kb_mapping.json`
2. Feature disabled (`ENABLE_BANK_SPECIFIC_KBS=false`)
3. Typo in bank prefix

**Solution**:
1. Check `.env`: `ENABLE_BANK_SPECIFIC_KBS=true`
2. Check `bank_kb_mapping.json` contains the bank prefix
3. Verify case-insensitive match (ГПБ = гпб = GPB)
4. Check orchestrator logs for bank detection message

### KB Not Created

**Symptom**: OpenWebUI doesn't show the bank-specific KB.

**Causes**:
1. OpenWebUI API not accessible
2. API key missing/invalid
3. Upload failed

**Solution**:
1. Check OpenWebUI is running: `http://localhost:3000`
2. Verify `OPENWEBUI_API_KEY` in `.env`
3. Check uploader logs: `grep "Knowledge Base" data/results/*/logs/*.log`

### Wrong KB Assigned

**Symptom**: Meeting went to wrong KB.

**Causes**:
1. Filename prefix doesn't match exactly
2. Alias mapping incorrect

**Solution**:
1. Check exact filename pattern: `BANKNAME_Description.avi`
2. Verify aliases in `bank_kb_mapping.json`
3. Use test script: `python test_bank_kb_resolver.py`

### Metadata Not Updated

**Symptom**: `metadata.json` missing bank fields.

**Causes**:
1. Old version of uploader
2. Feature disabled

**Solution**:
1. Check uploader version includes bank KB logic
2. Verify `ENABLE_BANK_SPECIFIC_KBS=true`
3. Re-run upload: `python openwebui_uploader.py data/results/folder_name/`

## Telegram Bot Usage

### List Available KBs

```
/kb
```

**Response**:
```
Available Knowledge Bases:
- Meetings
- GPB
- SBERBANK
- PSB
```

### Switch to Bank KB

```
/kb GPB
```

**Response**:
```
Knowledge Base set to: GPB
Now searching only GPB meetings
```

### Query Bank KB

```
What were the action items in yesterday's meeting?
```

**Response**: (searches only GPB meetings)

### Switch Back to Default

```
/kb Meetings
```

## Advanced Usage

### Programmatic Access

```python
from bank_kb_resolver import BankKBResolver

# Initialize resolver
resolver = BankKBResolver()

# Resolve KB from folder name
folder_name = "ГПБ_meeting_20250115_143022"
kb_name, bank_info = resolver.resolve_kb_name(folder_name)

print(f"KB: {kb_name}")  # "GPB"
print(f"Bank: {bank_info['full_name']}")  # "Газпромбанк"
print(f"Description: {bank_info['description']}")
```

### Custom Resolver Path

```python
from pathlib import Path
from bank_kb_resolver import BankKBResolver

# Use custom config file
config_path = Path("/path/to/custom_bank_kb_mapping.json")
resolver = BankKBResolver(config_path=config_path)
```

### Get All Banks

```python
resolver = BankKBResolver()
all_banks = resolver.get_all_banks()

for prefix, info in all_banks.items():
    print(f"{prefix} → {info['kb_name']} ({info['full_name']})")
```

## Implementation Details

### File Structure

```
services/OpenWebUi/scripts/
├── bank_kb_mapping.json              # Bank → KB configuration
├── bank_kb_resolver.py                # Bank name extraction/normalization
├── openwebui_uploader.py              # Upload logic (modified)
├── test_bank_kb_resolver.py           # Unit tests
├── test_bank_integration.py           # Integration tests
├── test_uploader_dryrun.py            # Dry-run tests
└── README_BANK_KB.md                  # This file
```

### Metadata Fields

`metadata.json` includes:

```json
{
  "openwebui_knowledge_base_name": "GPB",
  "bank_name": "GPB",
  "bank_full_name": "Газпромбанк",
  "bank_detected_from": "folder_name"
}
```

### Qdrant Collection

- All KBs share **one Qdrant collection**: `open-webui_knowledge`
- Filtering via **metadata** in OpenWebUI
- No separate collections per bank (simpler architecture)

## Backward Compatibility

### Existing Meetings

- Old meetings remain in "Meetings" KB
- No migration required
- New bank-prefixed meetings go to bank KBs

### Disabling the Feature

Set in `.env`:
```env
ENABLE_BANK_SPECIFIC_KBS=false
```

All meetings will use "Meetings" KB.

### Fallback Behavior

Videos without recognized bank prefix automatically use "Meetings" KB.

## Performance

### Impact

- **Negligible overhead**: Simple string operations
- **Config cached**: Loaded once at startup
- **KB creation**: Only once per bank
- **Qdrant**: Shared collection with metadata filtering

### Scalability

- ✅ Supports unlimited banks (limited by JSON file size)
- ✅ Case-insensitive matching with normalization
- ✅ Multiple aliases per bank
- ✅ No code changes for new banks

## Security

### Validation

- Bank name validation: alphanumeric only
- KB name sanitization: prevent injection
- Config file: read-only permissions

### Best Practices

- Use descriptive KB names (avoid special characters)
- Limit config file access (read-only for non-admins)
- Validate aliases to prevent collisions

## Future Enhancements

### Planned Features

1. **Auto-detection from email domain**: Extract bank from sender
2. **Department-level KBs**: `GPB_RETAIL`, `GPB_CORPORATE`
3. **Migration script**: Move existing meetings to bank KBs
4. **Admin UI**: Manage bank mappings via web interface
5. **Analytics per bank**: Track meeting counts, query stats

### Contributions

To contribute bank mappings or features:

1. Edit `bank_kb_mapping.json` for new banks
2. Submit PR with test cases
3. Update this README with examples

## References

- **OpenWebUI Docs**: https://docs.openwebui.com/
- **Qdrant Docs**: https://qdrant.tech/documentation/
- **Telegram Bot**: `services/telegram-rag-bot/README.md`
- **Main Documentation**: `CLAUDE.md`

## Support

For issues or questions:

1. Check troubleshooting section above
2. Run test scripts to verify configuration
3. Check orchestrator logs for error messages
4. Open issue on GitHub with test results

---

**Version**: 1.5.0
**Last Updated**: 2025-02-04
**Maintainer**: Meeting Transcriber Project
