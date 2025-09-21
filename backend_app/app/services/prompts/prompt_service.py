"""
Prompt Service

Encapsulates all Cosmos DB access for prompt categories and subcategories.
Provides a singleton instance optimized to reuse the cached Cosmos client.
"""
from typing import List, Dict, Any, Optional
import logging
from datetime import datetime, timezone
import uuid

from ...core.config import AppConfig, get_cosmos_db_cached
from ...core.async_utils import run_sync

logger = logging.getLogger(__name__)


class PromptService:
    def __init__(self):
        self.logger = logger

    def _get_db(self):
        cfg = AppConfig()
        return get_cosmos_db_cached(cfg)

    # Category operations
    def create_category(self, name: str, parent_category_id: Optional[str] = None) -> Dict[str, Any]:
        cosmos_db = self._get_db()
        timestamp = int(datetime.now(timezone.utc).timestamp() * 1000)
        category_id = f"category_{timestamp}"
        category_data = {
            "id": category_id,
            "type": "prompt_category",
            "name": name,
            "created_at": timestamp,
            "updated_at": timestamp,
            "parent_category_id": parent_category_id,
        }
        return cosmos_db.prompts_container.create_item(body=category_data)

    async def async_create_category(self, name: str, parent_category_id: Optional[str] = None) -> Dict[str, Any]:
        return await run_sync(lambda: self.create_category(name, parent_category_id))

    def list_categories(self) -> List[Dict[str, Any]]:
        cosmos_db = self._get_db()
        query = "SELECT * FROM c WHERE c.type = 'prompt_category'"
        return list(cosmos_db.prompts_container.query_items(query=query, enable_cross_partition_query=True))

    async def async_list_categories(self) -> List[Dict[str, Any]]:
        return await run_sync(lambda: self.list_categories())

    def get_category(self, category_id: str) -> Optional[Dict[str, Any]]:
        cosmos_db = self._get_db()
        query = {
            "query": "SELECT * FROM c WHERE c.type = 'prompt_category' AND c.id = @id",
            "parameters": [{"name": "@id", "value": category_id}],
        }
        items = list(cosmos_db.prompts_container.query_items(query=query["query"], parameters=query["parameters"], enable_cross_partition_query=True))
        return items[0] if items else None

    async def async_get_category(self, category_id: str) -> Optional[Dict[str, Any]]:
        return await run_sync(lambda: self.get_category(category_id))

    def update_category(self, category_id: str, name: str, parent_category_id: Optional[str] = None) -> Dict[str, Any]:
        cosmos_db = self._get_db()
        existing = self.get_category(category_id)
        if not existing:
            return None
        existing["name"] = name
        # update parent if provided (allow setting to None)
        if parent_category_id is not None:
            existing["parent_category_id"] = parent_category_id
        existing["updated_at"] = int(datetime.now(timezone.utc).timestamp() * 1000)
        return cosmos_db.prompts_container.upsert_item(body=existing)

    async def async_update_category(self, category_id: str, name: str, parent_category_id: Optional[str] = None) -> Dict[str, Any]:
        return await run_sync(lambda: self.update_category(category_id, name, parent_category_id))

    def delete_category_and_subcategories(self, category_id: str) -> None:
        cosmos_db = self._get_db()
        # Delete subcategories
        subq = {
            "query": "SELECT * FROM c WHERE c.type = 'prompt_subcategory' AND c.category_id = @category_id",
            "parameters": [{"name": "@category_id", "value": category_id}],
        }
        subs = list(cosmos_db.prompts_container.query_items(query=subq["query"], parameters=subq["parameters"], enable_cross_partition_query=True))
        for s in subs:
            cosmos_db.prompts_container.delete_item(item=s["id"], partition_key=s["id"])

        # Delete category
        cosmos_db.prompts_container.delete_item(item=category_id, partition_key=category_id)

    async def async_delete_category_and_subcategories(self, category_id: str) -> None:
        return await run_sync(lambda: self.delete_category_and_subcategories(category_id))

    # Subcategory operations
    def create_subcategory(self, category_id: str, name: str, prompts: Dict[str, str], pre: List[Dict[str, Any]], in_session: List[Dict[str, Any]]) -> Dict[str, Any]:
        cosmos_db = self._get_db()
        timestamp = int(datetime.now(timezone.utc).timestamp() * 1000)
        # Use a UUID for id to avoid special-character issues and collisions
        subcategory_id = f"subcategory_{timestamp}_{uuid.uuid4().hex}"
        subcategory_data = {
            "id": subcategory_id,
            "type": "prompt_subcategory",
            "category_id": category_id,
            "name": name,
            "prompts": prompts or {},
            "preSessionTalkingPoints": pre or [],
            "inSessionTalkingPoints": in_session or [],
            "created_at": timestamp,
            "updated_at": timestamp,
        }
        return cosmos_db.prompts_container.create_item(body=subcategory_data)

    async def async_create_subcategory(self, category_id: str, name: str, prompts: Dict[str, str], pre: List[Dict[str, Any]], in_session: List[Dict[str, Any]]) -> Dict[str, Any]:
        return await run_sync(lambda: self.create_subcategory(category_id, name, prompts, pre, in_session))

    def list_subcategories(self, category_id: Optional[str] = None) -> List[Dict[str, Any]]:
        cosmos_db = self._get_db()
        if category_id:
            q = {
                "query": "SELECT * FROM c WHERE c.type = 'prompt_subcategory' AND c.category_id = @category_id",
                "parameters": [{"name": "@category_id", "value": category_id}],
            }
            return list(cosmos_db.prompts_container.query_items(query=q["query"], parameters=q["parameters"], enable_cross_partition_query=True))

        q = "SELECT * FROM c WHERE c.type = 'prompt_subcategory'"
        return list(cosmos_db.prompts_container.query_items(query=q, enable_cross_partition_query=True))

    async def async_list_subcategories(self, category_id: Optional[str] = None) -> List[Dict[str, Any]]:
        return await run_sync(lambda: self.list_subcategories(category_id))

    def get_subcategory(self, subcategory_id: str) -> Optional[Dict[str, Any]]:
        cosmos_db = self._get_db()
        q = {
            "query": "SELECT * FROM c WHERE c.type = 'prompt_subcategory' AND c.id = @id",
            "parameters": [{"name": "@id", "value": subcategory_id}],
        }
        items = list(cosmos_db.prompts_container.query_items(query=q["query"], parameters=q["parameters"], enable_cross_partition_query=True))
        return items[0] if items else None

    async def async_get_subcategory(self, subcategory_id: str) -> Optional[Dict[str, Any]]:
        return await run_sync(lambda: self.get_subcategory(subcategory_id))

    def update_subcategory(self, subcategory_id: str, name: str, prompts: Dict[str, str], pre: List[Dict[str, Any]], in_session: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        cosmos_db = self._get_db()
        existing = self.get_subcategory(subcategory_id)
        if not existing:
            return None
        existing["name"] = name
        existing["prompts"] = prompts or {}
        existing["preSessionTalkingPoints"] = pre or []
        existing["inSessionTalkingPoints"] = in_session or []
        existing["updated_at"] = int(datetime.now(timezone.utc).timestamp() * 1000)
        return cosmos_db.prompts_container.upsert_item(body=existing)

    async def async_update_subcategory(self, subcategory_id: str, name: str, prompts: Dict[str, str], pre: List[Dict[str, Any]], in_session: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        return await run_sync(lambda: self.update_subcategory(subcategory_id, name, prompts, pre, in_session))

    def delete_subcategory(self, subcategory_id: str) -> None:
        cosmos_db = self._get_db()
        cosmos_db.prompts_container.delete_item(item=subcategory_id, partition_key=subcategory_id)

    async def async_delete_subcategory(self, subcategory_id: str) -> None:
        return await run_sync(lambda: self.delete_subcategory(subcategory_id))

    def retrieve_prompts_hierarchy(self) -> List[Dict[str, Any]]:
        cosmos_db = self._get_db()
        categories = list(cosmos_db.prompts_container.query_items(query="SELECT * FROM c WHERE c.type = 'prompt_category'", enable_cross_partition_query=True))
        subcategories = list(cosmos_db.prompts_container.query_items(query="SELECT * FROM c WHERE c.type = 'prompt_subcategory'", enable_cross_partition_query=True))

        results = []
        for category in categories:
            category_data = {
                "category_name": category.get("name"),
                "category_id": category.get("id"),
                "parent_category_id": category.get("parent_category_id"),
                "subcategories": [],
            }
            for sub in subcategories:
                if sub.get("category_id") == category.get("id"):
                    category_data["subcategories"].append({
                        "subcategory_name": sub.get("name"),
                        "subcategory_id": sub.get("id"),
                        "prompts": sub.get("prompts", {}),
                        "preSessionTalkingPoints": sub.get("preSessionTalkingPoints", []),
                        "inSessionTalkingPoints": sub.get("inSessionTalkingPoints", []),
                    })
            results.append(category_data)

        return results

    async def async_retrieve_prompts_hierarchy(self) -> List[Dict[str, Any]]:
        return await run_sync(lambda: self.retrieve_prompts_hierarchy())


# Singleton instance
prompt_service = PromptService()
