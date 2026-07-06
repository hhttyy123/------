"""FastAPI 应用入口"""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.exc import SQLAlchemyError

from app.config import settings
from app.api.v1 import router as api_v1_router
from app.api.v2 import router as api_v2_router
from app.database import SessionLocal, database_status
from sqlalchemy import text
from datetime import datetime, timezone
import uuid
from app.api.auth import require_user, router as auth_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用启动/关闭事件"""
    # 创建必要的目录
    Path(settings.UPLOAD_DIR).mkdir(parents=True, exist_ok=True)
    Path(settings.DATA_DIR).mkdir(parents=True, exist_ok=True)
    yield


app = FastAPI(
    title="劳务派遣管理系统",
    description="Labor Dispatch Management System - Intelligent Excel Import",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS - 允许前端开发服务器
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def audit_mutations(request: Request, call_next):
    request_id=request.headers.get("x-request-id") or str(uuid.uuid4());response=await call_next(request);response.headers["x-request-id"]=request_id
    if request.method in {"POST","PATCH","PUT","DELETE"} and response.status_code < 400 and request.url.path.startswith("/api/") and hasattr(request.state,"user_id"):
        with SessionLocal() as db:
            db.execute(text("INSERT INTO audit_logs(actor_id,action,object_type,request_id,ip_address,user_agent,created_at) VALUES(:actor,:action,:object,:rid,CAST(:ip AS inet),:ua,:created)"),{"actor":request.state.user_id,"action":request.method.lower(),"object":request.url.path[:50],"rid":request_id,"ip":request.client.host if request.client else None,"ua":request.headers.get("user-agent"),"created":datetime.now(timezone.utc)});db.commit()
    return response


app.include_router(auth_router)
app.include_router(api_v1_router, dependencies=[Depends(require_user)])
app.include_router(api_v2_router, dependencies=[Depends(require_user)])


@app.get("/api/health")
async def health_check():
    return {"status": "ok", "version": "0.1.0"}


@app.get("/api/health/db")
async def database_health_check():
    try:
        return database_status()
    except (SQLAlchemyError, RuntimeError) as exc:
        raise HTTPException(status_code=503, detail="数据库连接不可用") from exc
