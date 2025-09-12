# Session GUID Backfill Script

This script updates existing session documents to use canonical GUIDs instead of email addresses in the `user_id` field.

## Problem

Session documents were originally stored with email addresses in the `user_id` field. This causes issues when:
- Frontend queries analytics by GUID but sessions are stored with email as `user_id`
- Analytics queries return empty results for GUID-based requests
- User session data is not properly aggregated

## Solution

This backfill script:
1. Scans all session documents in the `user_sessions` container
2. Identifies sessions where `user_id` is not a valid GUID format
3. Resolves the canonical GUID for each email using the `auth` container
4. Updates session documents with:
   - `user_id`: canonical GUID (for analytics queries to work)
   - `user_email`: original email address (for backwards compatibility)
   - `user_id_original`: original value from `user_id` field (for audit trail)
   - `backfill_updated_at`: timestamp of when the backfill was applied

## Usage

### Prerequisites

1. Ensure you have the required environment variables set:
   ```bash
   AZURE_COSMOS_ENDPOINT=<your-cosmos-endpoint>
   AZURE_COSMOS_KEY=<your-cosmos-key>
   COSMOS_DATABASE_NAME=<your-database-name>
   ```

2. Install dependencies (if not already installed):
   ```bash
   pip install -r requirements.txt
   ```

### Dry Run (Recommended First)

Always run a dry-run first to see what changes would be made:

```bash
cd backend_app/scripts
python session_guid_backfill.py --dry-run
```

This will show:
- How many sessions need updating
- What the changes would be for each session
- No actual changes are made

### Apply Changes

Once you're satisfied with the dry-run output:

```bash
python session_guid_backfill.py
```

### Batch Processing

For large datasets, you can control batch size:

```bash
python session_guid_backfill.py --batch-size 25
```

## Example Output

```
2025-08-24 14:30:00 - INFO - 🚀 Starting session GUID backfill process
2025-08-24 14:30:00 - INFO -    - Dry run: False
2025-08-24 14:30:00 - INFO -    - Batch size: 50
2025-08-24 14:30:01 - INFO - 🔍 Scanning for sessions that need GUID updates...
2025-08-24 14:30:02 - INFO - 📊 Found 15 sessions needing GUID updates out of 20 total
2025-08-24 14:30:02 - INFO - 📦 Processing batch 1/1 (15 sessions)
2025-08-24 14:30:03 - INFO - ✅ Updated session fb0d56a7-8b74-4453-be01-2ff2ae3df1c6: MitchellRevill@barnsley.gov.uk → ee661ad6-af09-4ae0-8502-ee78ca3febf7
2025-08-24 14:30:03 - INFO - ✅ Updated session f6a5b68b-d9d7-484e-a6a0-024a7a0183fb: MitchellRevill@barnsley.gov.uk → ee661ad6-af09-4ae0-8502-ee78ca3febf7
...
2025-08-24 14:30:05 - INFO - 📦 Batch 1 complete: 15 updated, 0 failed
2025-08-24 14:30:05 - INFO - 🎉 Backfill process complete!
2025-08-24 14:30:05 - INFO -    - Total sessions processed: 15
2025-08-24 14:30:05 - INFO -    - Successfully updated: 15
2025-08-24 14:30:05 - INFO -    - Failed: 0
```

## Verification

After running the backfill, verify the results:

1. **Check session documents**:
   ```bash
   curl -H "Authorization: Bearer <token>" \
        "https://your-app.azurewebsites.net/api/analytics/debug/sessions"
   ```
   
   Sessions should now show GUID values in `user_id` field.

2. **Test GUID-based analytics**:
   ```bash
   curl -H "Authorization: Bearer <token>" \
        "https://your-app.azurewebsites.net/api/analytics/users/<GUID>/session-summary"
   ```
   
   This should now return populated data instead of empty results.

3. **Test email-based analytics** (should still work):
   ```bash
   curl -H "Authorization: Bearer <token>" \
        "https://your-app.azurewebsites.net/api/analytics/users/<EMAIL>/session-summary"
   ```

## Safety Features

- **Dry-run mode**: Preview changes without applying them
- **Batch processing**: Process documents in small batches to avoid timeouts
- **Comprehensive logging**: Detailed logs of all operations
- **Backup fields**: Original values preserved in `user_email` and `user_id_original`
- **Error handling**: Failed updates are logged but don't stop the process
- **Idempotent**: Safe to run multiple times (skips sessions that already have GUIDs)

## Rollback

If needed, you can rollback changes by:
1. Updating `user_id` back to the value in `user_id_original`
2. Removing the `user_email`, `user_id_original`, and `backfill_updated_at` fields

## Monitoring

Monitor the script execution:
- Watch for warnings about unresolvable email addresses
- Check that the success rate is high (close to 100%)
- Verify that analytics endpoints work with GUIDs after completion

## Troubleshooting

**"No auth record found for email"**: Some session documents may reference users that no longer exist in the auth container. These will be skipped.

**"Auth record ID is not a valid GUID"**: The auth container might have inconsistent ID formats. Check your auth data.

**Connection timeouts**: Reduce batch size with `--batch-size` parameter.
