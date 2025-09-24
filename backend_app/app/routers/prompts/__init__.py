"""
Prompts Router Module - expose a single prompts_router that includes internal prompt routes
"""
from fastapi import APIRouter
from .prompts import router as prompts_router_internal

# Create main prompts router that exposes all prompts-related endpoints under a common prefix
prompts_router = APIRouter(prefix="/api/prompts", tags=["prompts"])
prompts_router.include_router(prompts_router_internal, prefix="")

__all__ = ["prompts_router", "prompts_router_internal"]
