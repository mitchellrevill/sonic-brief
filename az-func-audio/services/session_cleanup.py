import datetime
import logging
import azure.functions as func


# CONFIGURE THESE VALUES TO MATCH YOUR SESSION DOCUMENT SCHEMA
# Default container name; allow override via AppConfig or environment variable
SESSION_CONTAINER = "user_sessions"  # CosmosDB container name
HEARTBEAT_FIELD = "last_heartbeat"   # Field storing last heartbeat timestamp (ISO8601 string)
SESSION_STATUS_FIELD = "status"      # Field storing session status ('open', 'closed')
SESSION_EVENT_TYPE_FIELD = "event_type"  # Field for event type ('session_start', etc.)
PARTITION_KEY_FIELD = "partition_key"    # Field for partition key (user_id)
STALE_MINUTES = 15  # Mark sessions as closed if no heartbeat in 15 minutes

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


    # Query for sessions that are open, event_type 'session_start', and have a stale heartbeat
    query = (
        f"SELECT * FROM c WHERE c.{SESSION_STATUS_FIELD} = 'open' "
        f"AND c.{SESSION_EVENT_TYPE_FIELD} = 'session_start' "
        f"AND c.{HEARTBEAT_FIELD} < @stale_time"
    )
    stale_time = (utc_now - datetime.timedelta(minutes=STALE_MINUTES)).isoformat()
    params = [{"name": "@stale_time", "value": stale_time}]

    logging.debug(f"Session cleanup query: {query} params: {params}")
    closed_count = 0
    for item in container.query_items(query=query, parameters=params, enable_cross_partition_query=True):
        # Mark session as closed
        item[SESSION_STATUS_FIELD] = "closed"
        item["closed_at"] = utc_now.isoformat()
        # Optionally, add an audit entry or update metadata
        container.upsert_item(item)
        closed_count += 1
        logging.info(f"Closed stale session: {item.get('id')}")

    if closed_count == 0:
        logging.info("Session cleanup: no stale sessions found to close.")
    else:
        logging.info(f"Session cleanup: closed {closed_count} stale session(s).")

    logging.info("Session cleanup function completed.")
