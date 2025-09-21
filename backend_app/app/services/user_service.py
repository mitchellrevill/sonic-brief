"""Thin user service wrapper around the project's Cosmos DB helper.

Keep the router code thin and centralize sanitization and common queries here.
This file intentionally stays lightweight and delegates to the existing CosmosDB
wrapper returned by `get_cosmos_db_cached`.
"""
from typing import Any, Dict, List, Optional

from ..core.config import get_app_config, get_cosmos_db_cached
from ..core.async_utils import run_sync


class UserService:
    def __init__(self, cosmos_db=None):
        # Accept an injected cosmos_db for easier testing; otherwise resolve one
        if cosmos_db is None:
            config = get_app_config()
            cosmos_db = get_cosmos_db_cached(config)
        self.cosmos = cosmos_db

    async def get_user_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        return await self.cosmos.get_user_by_id(user_id)

    async def update_user(self, user_id: str, update_data: Dict[str, Any]) -> Dict[str, Any]:
        return await self.cosmos.update_user(user_id, update_data)

    async def query_users_by_permission(self, permission_level: str) -> List[Dict[str, Any]]:
        # Simple helper that matches the previous inline query
        query = "SELECT * FROM c WHERE c.type = 'user' AND c.permission = @permission"
        parameters = [{"name": "@permission", "value": permission_level}]
        items = await run_sync(lambda: list(
            self.cosmos.users_container.query_items(
                query=query,
                parameters=parameters,
                enable_cross_partition_query=True,
            )
        ))
        # Sanitize sensitive fields
        for u in items:
            u.pop("hashed_password", None)
        return items

    def sanitize(self, user: Dict[str, Any]) -> Dict[str, Any]:
        if not user:
            return user
        user.pop("hashed_password", None)
        return user

    def close(self):
        # no-op close for compatibility with DI lifecycle
        return


def get_user_service(cosmos_db=None) -> UserService:
    return UserService(cosmos_db)
