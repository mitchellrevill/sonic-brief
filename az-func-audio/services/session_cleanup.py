import datetime
import logging
import azure.functions as func


# CONFIGURE THESE VALUES TO MATCH YOUR SESSION DOCUMENT SCHEMA
# Default container name; allow override via AppConfig or environment variable
SESSION_CONTAINER = "user_sessions"  # CosmosDB container name
HEARTBEAT_FIELD = "last_heartbeat"   # Field storing last heartbeat timestamp (ISO8601 string)
SESSION_STATUS_FIELD = "status"      # Field storing session status ('active', 'expired', 'closed')
SESSION_TYPE_FIELD = "type"          # Field for document type ('session')
PARTITION_KEY_FIELD = "partition_key"    # Field for partition key (user_id)
STALE_MINUTES = 15  # Mark sessions as expired if no heartbeat in 15 minutes

# Timer trigger entry point
def main(mytimer: func.TimerRequest) -> None:
    utc_now = datetime.datetime.utcnow()
    logging.info(f"Session cleanup function started at {utc_now}")

    # Import get_cosmos_client lazily to avoid import-time errors (e.g., circular imports
    # or missing dependencies) while the Functions host indexes modules.
    try:
        from .cosmos_service import get_cosmos_client
    except Exception as imp_err:
        logging.error(f"Failed to import get_cosmos_client: {imp_err}")
        return

    client = get_cosmos_client()
    # CosmosClient does not expose get_container_client directly; obtain the
    # database client first, then get the container client from the database.
    try:
        from config import AppConfig

        config = AppConfig()
        # Allow container name override from config or environment variable
        container_name = getattr(config, "cosmos_sessions_container", None) or SESSION_CONTAINER
        database = client.get_database_client(config.cosmos_database)
        logging.info(f"Resolved Cosmos DB database='{config.cosmos_database}', container='{container_name}'")
        container = database.get_container_client(container_name)
    except Exception as e:
        # If CosmosResourceNotFoundError, provide a clearer actionable log
        try:
            from azure.cosmos.exceptions import CosmosResourceNotFoundError
        except Exception:
            CosmosResourceNotFoundError = None

        if CosmosResourceNotFoundError and isinstance(e, CosmosResourceNotFoundError):
            logging.error(
                f"Cosmos resource not found: database='{config.cosmos_database}' container='{container_name}'. "
                "Verify the database and container exist and the function's identity has permission.",
                exc_info=True,
            )
        else:
            logging.error(f"Failed to obtain Cosmos DB container client: {e}", exc_info=True)
        return

    # Query for sessions that are active, type 'session', and have a stale heartbeat
    query = (
        f"SELECT * FROM c WHERE c.{SESSION_STATUS_FIELD} = 'active' "
        f"AND c.{SESSION_TYPE_FIELD} = 'session' "
        f"AND c.{HEARTBEAT_FIELD} < @stale_time"
    )
    stale_time = (utc_now - datetime.timedelta(minutes=STALE_MINUTES)).isoformat()
    params = [{"name": "@stale_time", "value": stale_time}]

    logging.debug(f"Session cleanup query: {query} params: {params}")
    expired_count = 0
    
    for item in container.query_items(query=query, parameters=params, enable_cross_partition_query=True):
        # Mark session as expired instead of closed to distinguish from user-initiated logout
        item[SESSION_STATUS_FIELD] = "expired"
        item["expired_at"] = utc_now.isoformat()
        item["expiry_reason"] = "heartbeat_timeout"
        
        # Calculate session duration for analytics
        try:
            created_at = datetime.datetime.fromisoformat(item.get("created_at", "").replace('Z', '+00:00'))
            session_duration = (utc_now - created_at).total_seconds()
            item["session_duration_seconds"] = session_duration
        except Exception as e:
            logging.warning(f"Could not calculate session duration for session {item.get('id')}: {e}")
            item["session_duration_seconds"] = 0
        
        # Preserve activity metrics for analytics
        item["final_activity_count"] = item.get("activity_count", 0)
        item["final_endpoints_accessed"] = item.get("endpoints_accessed", [])
        
        # Optionally, add cleanup metadata
        item["cleanup_metadata"] = {
            "cleanup_timestamp": utc_now.isoformat(),
            "cleanup_function": "session_cleanup_azure_function",
            "stale_threshold_minutes": STALE_MINUTES
        }
        
        container.upsert_item(item)
        expired_count += 1
        logging.info(f"Expired stale session: {item.get('id')} for user {item.get('user_id')}")

    # Also clean up old expired sessions (older than 30 days) to prevent container bloat
    cleanup_cutoff = (utc_now - datetime.timedelta(days=30)).isoformat()
    cleanup_query = (
        f"SELECT c.id, c.{PARTITION_KEY_FIELD} FROM c WHERE c.{SESSION_STATUS_FIELD} IN ('expired', 'closed') "
        f"AND c.{SESSION_TYPE_FIELD} = 'session' "
        f"AND c.{HEARTBEAT_FIELD} < @cleanup_cutoff"
    )
    cleanup_params = [{"name": "@cleanup_cutoff", "value": cleanup_cutoff}]
    
    deleted_count = 0
    for item in container.query_items(query=cleanup_query, parameters=cleanup_params, enable_cross_partition_query=True):
        try:
            container.delete_item(item=item["id"], partition_key=item[PARTITION_KEY_FIELD])
            deleted_count += 1
            logging.debug(f"Deleted old session: {item['id']}")
        except Exception as e:
            logging.warning(f"Failed to delete old session {item['id']}: {e}")

    # Summary logging
    if expired_count == 0 and deleted_count == 0:
        logging.info("Session cleanup: no stale sessions found to expire or delete.")
    else:
        logging.info(f"Session cleanup completed: expired {expired_count} stale session(s), deleted {deleted_count} old session(s).")

    logging.info("Session cleanup function completed.")
