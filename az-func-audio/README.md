# ...existing code...

---

## Session Cleanup Timer Trigger

A timer-triggered Azure Function is now implemented to auto-close stale sessions in CosmosDB every 5 minutes.

- **Location:** `services/session_cleanup.py`
- **Registration:** See the bottom of `function_app.py`
- **Schedule:** Every 5 minutes (`0 */5 * * * *`)
- **Logic:** Marks sessions as closed if no heartbeat in the last 15 minutes.

### How it works
- Queries CosmosDB for sessions with status 'open' and a stale heartbeat.
- Updates those sessions to 'closed' and sets `closed_at` timestamp.

### Configuration
- Edit `STALE_MINUTES` in `session_cleanup.py` to change the inactivity threshold.
- Ensure `azure-functions` and `azure-cosmos` are present in `requirements.txt` (already included).

### Deployment
- Azure automatically detects timer triggers in Python Function Apps.
- No manual registration needed beyond code changes.

### Testing Locally
- You can manually invoke `session_cleanup.main()` for local testing.

---
For questions or changes, see `session_cleanup.py` and `function_app.py`.