# api/__init__.py
# 初始化API，路由注册

from fastapi import APIRouter

from app.api import validate_flow

api_router = APIRouter()
api_router.include_router(validate_flow.router, prefix="/api", tags=["api"])