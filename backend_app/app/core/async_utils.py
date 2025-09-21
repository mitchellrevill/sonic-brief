import asyncio
from typing import Callable, TypeVar, Any

T = TypeVar("T")


async def run_sync(fn: Callable[..., T], *args, **kwargs) -> T:
    """Run a blocking function in the default threadpool and return result.

    Use this from async FastAPI endpoints when calling libraries that perform
    blocking I/O (like the synchronous Cosmos SDK) to avoid blocking the
    event loop.
    """
    return await asyncio.to_thread(fn, *args, **kwargs)
