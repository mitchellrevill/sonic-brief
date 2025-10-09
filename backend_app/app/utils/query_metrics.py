"""
Query metrics logging for Cosmos DB operations.
Tracks RU consumption and query performance.
"""
import logging
import time
from typing import Any, Dict, List, Optional, Callable
from functools import wraps
from azure.cosmos import exceptions

logger = logging.getLogger(__name__)


def log_query_metrics(query: str, ru_charge: float, item_count: int, duration_ms: float, **kwargs):
    """
    Log query execution metrics for monitoring and optimization.
    
    Args:
        query: The SQL query executed
        ru_charge: Request Units consumed
        item_count: Number of items returned
        duration_ms: Query execution time in milliseconds
        **kwargs: Additional context (partition_key, user_id, etc.)
    """
    # Truncate query for logging
    query_preview = query[:200] if len(query) > 200 else query
    query_preview = ' '.join(query_preview.split())  # Normalize whitespace
    
    # Classify query cost
    cost_level = "LOW"
    if ru_charge > 100:
        cost_level = "CRITICAL"
    elif ru_charge > 50:
        cost_level = "HIGH"
    elif ru_charge > 10:
        cost_level = "MEDIUM"
    
    log_level = logging.WARNING if cost_level in ["HIGH", "CRITICAL"] else logging.INFO
    
    logger.log(
        log_level,
        f"[{cost_level}] Cosmos DB Query executed",
        extra={
            "query_preview": query_preview,
            "ru_charge": round(ru_charge, 2),
            "item_count": item_count,
            "duration_ms": round(duration_ms, 2),
            "ru_per_item": round(ru_charge / item_count, 2) if item_count > 0 else 0,
            "cost_level": cost_level,
            **kwargs
        }
    )


def execute_query_with_metrics(
    container,
    query: str,
    parameters: Optional[List[Dict[str, Any]]] = None,
    **query_kwargs
) -> List[Dict[str, Any]]:
    """
    Execute a Cosmos DB query and log performance metrics.
    
    Args:
        container: Cosmos DB container instance
        query: SQL query string
        parameters: Query parameters
        **query_kwargs: Additional query options (enable_cross_partition_query, etc.)
    
    Returns:
        List of query results
        
    Raises:
        CosmosHttpResponseError: If query fails
    """
    start_time = time.time()
    ru_charge = 0.0
    items = []
    
    try:
        response = container.query_items(
            query=query,
            parameters=parameters or [],
            **query_kwargs
        )
        
        # Consume the iterator and capture RU charge
        items = list(response)
        ru_charge = float(response.response_headers.get('x-ms-request-charge', 0))
        
        duration_ms = (time.time() - start_time) * 1000
        
        # Log metrics
        log_query_metrics(
            query=query,
            ru_charge=ru_charge,
            item_count=len(items),
            duration_ms=duration_ms,
            partition_key=query_kwargs.get('partition_key'),
            cross_partition=query_kwargs.get('enable_cross_partition_query', False)
        )
        
        return items
        
    except exceptions.CosmosHttpResponseError as e:
        duration_ms = (time.time() - start_time) * 1000
        logger.error(
            f"Cosmos DB query failed: {e.message}",
            extra={
                "query": query[:200],
                "status_code": e.status_code,
                "duration_ms": round(duration_ms, 2),
                "error": str(e)
            },
            exc_info=True
        )
        raise


async def execute_query_with_metrics_async(
    container,
    query: str,
    parameters: Optional[List[Dict[str, Any]]] = None,
    run_sync: Optional[Callable] = None,
    **query_kwargs
) -> List[Dict[str, Any]]:
    """
    Async version of execute_query_with_metrics.
    
    Args:
        container: Cosmos DB container instance
        query: SQL query string
        parameters: Query parameters
        run_sync: Optional async wrapper function
        **query_kwargs: Additional query options
    
    Returns:
        List of query results
    """
    start_time = time.time()
    ru_charge = 0.0
    items = []
    
    try:
        if run_sync:
            # Use provided async wrapper
            response = container.query_items(
                query=query,
                parameters=parameters or [],
                **query_kwargs
            )
            items = await run_sync(lambda: list(response))
            ru_charge = float(response.response_headers.get('x-ms-request-charge', 0))
        else:
            # Direct execution
            response = container.query_items(
                query=query,
                parameters=parameters or [],
                **query_kwargs
            )
            items = list(response)
            ru_charge = float(response.response_headers.get('x-ms-request-charge', 0))
        
        duration_ms = (time.time() - start_time) * 1000
        
        # Log metrics
        log_query_metrics(
            query=query,
            ru_charge=ru_charge,
            item_count=len(items),
            duration_ms=duration_ms,
            partition_key=query_kwargs.get('partition_key'),
            cross_partition=query_kwargs.get('enable_cross_partition_query', False)
        )
        
        return items
        
    except exceptions.CosmosHttpResponseError as e:
        duration_ms = (time.time() - start_time) * 1000
        logger.error(
            f"Cosmos DB query failed: {e.message}",
            extra={
                "query": query[:200],
                "status_code": e.status_code,
                "duration_ms": round(duration_ms, 2),
                "error": str(e)
            },
            exc_info=True
        )
        raise


def query_metrics_decorator(func):
    """
    Decorator to add query metrics logging to methods that execute Cosmos DB queries.
    
    Usage:
        @query_metrics_decorator
        def my_query_method(self, ...):
            # Your query code here
            pass
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        try:
            result = func(*args, **kwargs)
            duration_ms = (time.time() - start_time) * 1000
            
            logger.debug(
                f"Query method '{func.__name__}' completed",
                extra={
                    "method": func.__name__,
                    "duration_ms": round(duration_ms, 2)
                }
            )
            
            return result
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            logger.error(
                f"Query method '{func.__name__}' failed",
                extra={
                    "method": func.__name__,
                    "duration_ms": round(duration_ms, 2),
                    "error": str(e)
                },
                exc_info=True
            )
            raise
    
    return wrapper
