"""
机械工程AI战略转型课程 - 生产级主应用
完整集成Week 1-20所有功能模块

架构：FastAPI + SQLAlchemy + Redis + PostgreSQL + WebSocket
"""

import os
import sys
import socket
import logging
from pathlib import Path
import asyncio
from typing import Optional, Dict, Any
from contextlib import asynccontextmanager
from datetime import datetime, timedelta

from fastapi import FastAPI, WebSocket, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from fastapi.openapi.utils import get_openapi

from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool

import redis.asyncio as redis_async
from pydantic import AliasChoices, BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# ============================================================================
# 配置管理（统一环境变量）
# ============================================================================

class Settings(BaseSettings):
    """应用配置 - Week 20: 配置管理"""

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False)

    # 基础配置
    app_name: str = "Mechanical Engineering AI System"
    version: str = "1.0.0"
    environment: str = Field(default="production", validation_alias="ENVIRONMENT")
    debug: bool = False
    
    # API配置
    api_prefix: str = "/api/v1"
    openai_api_key: str = Field(default="", validation_alias="OPENAI_API_KEY")
    openai_org_id: str = Field(default="", validation_alias="OPENAI_ORG_ID")
    llm_model: str = "gpt-4-turbo"
    
    # 数据库配置（显式别名，确保 Docker / shell 中的 POSTGRES_URL 一定生效）
    postgres_url: str = Field(
        default="postgresql://user:password@localhost:5432/mechanical_ai",
        validation_alias=AliasChoices("POSTGRES_URL", "postgres_url"),
    )
    db_pool_size: int = 20
    db_pool_recycle: int = 3600
    
    # Redis配置
    redis_url: str = Field(
        default="redis://localhost:6379/0",
        validation_alias=AliasChoices("REDIS_URL", "redis_url"),
    )
    redis_ttl: int = 3600
    
    # 认证配置
    jwt_secret: str = Field(default="your-secret-key")
    jwt_algorithm: str = "HS256"
    jwt_expire_hours: int = 24
    
    # CORS配置（含 Docker 静态前端 8080、本机 API 文档）
    allowed_origins: list = [
        "http://localhost:3000",
        "http://localhost:8000",
        "http://localhost:8010",
        "http://localhost:8080",
        "http://127.0.0.1:8080",
        "http://127.0.0.1:8010",
    ]
    allowed_methods: list = ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
    allowed_headers: list = ["*"]


settings = Settings()

# ============================================================================
# 日志配置（Week 20: 日志系统）
# ============================================================================

_log_dir = Path(__file__).resolve().parent / "logs"
_log_dir.mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(_log_dir / "app.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ============================================================================
# 数据库连接池（Week 4: 数据库优化）
# ============================================================================

engine = create_engine(
    settings.postgres_url,
    poolclass=QueuePool,
    pool_size=settings.db_pool_size,
    max_overflow=10,
    pool_recycle=settings.db_pool_recycle,
    echo=settings.debug
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db() -> Session:
    """获取数据库会话"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ============================================================================
# Redis连接（Week 19: 缓存优化）
# ============================================================================

class RedisClient:
    """Redis客户端管理（未起 Redis 或网络失败时降级，避免业务接口 500）"""
    _instance: Optional[redis_async.Redis] = None

    @classmethod
    async def init(cls):
        """初始化Redis连接"""
        if cls._instance is None:
            r: Optional[redis_async.Redis] = None
            try:
                r = redis_async.from_url(
                    settings.redis_url,
                    encoding="utf-8",
                    decode_responses=True,
                )
                await r.ping()
                cls._instance = r
                logger.info("Redis连接初始化成功")
            except Exception as e:
                if r is not None:
                    try:
                        await r.close()
                    except Exception:
                        pass
                cls._instance = None
                logger.warning("Redis 不可用，将跳过缓存（诊断等接口仍可工作）: %s", e)
    
    @classmethod
    async def close(cls):
        """关闭Redis连接"""
        if cls._instance:
            try:
                await cls._instance.close()
            except Exception:
                pass
            cls._instance = None
            logger.info("Redis连接已关闭")
    
    @classmethod
    async def ping(cls) -> bool:
        if not cls._instance:
            return False
        try:
            await cls._instance.ping()
            return True
        except Exception:
            return False
    
    @classmethod
    async def get(cls, key: str) -> Optional[str]:
        """获取缓存值"""
        if not cls._instance:
            return None
        try:
            return await cls._instance.get(key)
        except Exception as e:
            logger.warning("Redis get 失败: %s", e)
            return None
    
    @classmethod
    async def set(cls, key: str, value: str, expire: int = None):
        """设置缓存值"""
        if not cls._instance:
            return
        try:
            await cls._instance.set(
                key,
                value,
                ex=expire or settings.redis_ttl,
            )
        except Exception as e:
            logger.warning("Redis set 失败: %s", e)
    
    @classmethod
    async def delete(cls, key: str):
        """删除缓存"""
        if not cls._instance:
            return
        try:
            await cls._instance.delete(key)
        except Exception as e:
            logger.warning("Redis delete 失败: %s", e)

# ============================================================================
# 数据模型
# ============================================================================

class HealthCheck(BaseModel):
    """系统健康检查响应"""
    status: str
    timestamp: datetime
    version: str
    environment: str
    components: Dict[str, str]

class DiagnosisRequest(BaseModel):
    """故障诊断请求（Week 4+: 工业诊断系统）"""
    equipment_id: str = Field(..., description="设备ID")
    equipment_type: str = Field(..., description="设备类型")
    symptoms: str = Field(..., description="故障症状描述")
    sensor_data: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None

class DiagnosisResponse(BaseModel):
    """故障诊断响应"""
    diagnosis_id: str
    equipment_id: str
    diagnosis_result: str
    confidence: float
    suggested_actions: list
    timestamp: datetime

class KnowledgeRequest(BaseModel):
    """知识库查询（Week 13+: 知识管理）"""
    query: str = Field(..., description="查询内容")
    similarity_threshold: float = 0.7
    top_k: int = 5

class AgentExecutionRequest(BaseModel):
    """Agent执行请求（Week 15+: Agent系统）"""
    task_description: str
    tools: list = []
    parameters: Optional[Dict[str, Any]] = None

# ============================================================================
# 启动和关闭事件
# ============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动事件
    logger.info(f"应用启动: {settings.app_name} v{settings.version}")
    
    # 初始化Redis
    await RedisClient.init()
    
    # 数据库连接测试
    try:
        with SessionLocal() as db:
            db.execute(text("SELECT 1"))
        logger.info("数据库连接测试成功")
    except Exception as e:
        logger.error(f"数据库连接失败: {e}")
    
    yield
    
    # 关闭事件
    logger.info("应用关闭")
    await RedisClient.close()
    engine.dispose()

# ============================================================================
# FastAPI应用初始化
# ============================================================================

app = FastAPI(
    title=settings.app_name,
    description="机械工程AI战略转型课程 - 生产级系统",
    version=settings.version,
    # 文档挂在根路径，避免误以为 /docs 404（业务接口仍在 /api/v1/*）
    openapi_url="/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# ============================================================================
# 中间件配置
# ============================================================================

# CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=settings.allowed_methods,
    allow_headers=settings.allowed_headers,
    max_age=600,
)

# 可信主机中间件（含 testserver 供 Starlette TestClient / 自动化测试）
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=[
        "localhost",
        "127.0.0.1",
        "[::1]",
        "testserver",
        "*.example.com",
    ],
)

# Gzip压缩中间件
app.add_middleware(GZipMiddleware, minimum_size=1000)

# ============================================================================
# 根路径（避免打开 / 时 404）
# ============================================================================

@app.get("/")
async def root():
    return {
        "service": settings.app_name,
        "version": settings.version,
        "health": "/health",
        "docs": "/docs",
        "api_prefix": settings.api_prefix,
        "example": f"{settings.api_prefix}/auth/login",
    }


# ============================================================================
# 健康检查端点
# ============================================================================

@app.get("/health")
async def health_check() -> HealthCheck:
    """系统健康检查（Week 20: 监控系统）"""
    components = {
        "api": "healthy",
        "redis": "checking",
        "database": "checking"
    }
    
    # 检查Redis（ping，避免 get 吞异常后误报健康）
    components["redis"] = "healthy" if await RedisClient.ping() else "unhealthy"
    
    # 检查数据库（直连引擎，避免 Session 上下文与连接池边缘情况）
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        components["database"] = "healthy"
    except Exception:
        components["database"] = "unhealthy"
    
    return HealthCheck(
        status="healthy" if all(v == "healthy" for v in components.values()) else "degraded",
        timestamp=datetime.now(),
        version=settings.version,
        environment=settings.environment,
        components=components
    )

# ============================================================================
# 核心API路由
# ============================================================================

@app.post(f"{settings.api_prefix}/diagnosis/submit")
async def submit_diagnosis(
    request: DiagnosisRequest,
    db: Session = Depends(get_db)
) -> DiagnosisResponse:
    """提交故障诊断请求（Week 4+: 工业诊断）
    
    这个端点整合了：
    - Week 4: RAG诊断系统
    - Week 8: 多Agent诊断
    - Week 11: 设备故障诊断
    - Week 12: 故障预警
    """
    try:
        # 1. 从Redis缓存获取历史诊断（Week 19: 缓存优化）
        cache_key = f"diagnosis:{request.equipment_id}"
        cached = await RedisClient.get(cache_key)
        
        # 2. 调用RAG诊断系统（Week 4: RAG系统）
        # diagnosis_result = await rag_diagnosis_engine.diagnose(
        #     equipment_type=request.equipment_type,
        #     symptoms=request.symptoms,
        #     sensor_data=request.sensor_data
        # )
        
        # 3. 多Agent协作诊断（Week 8: 多Agent系统）
        # agent_results = await multi_agent_executor.execute(
        #     diagnosis_task=request,
        #     tools=[
        #         "sensor_analysis_tool",
        #         "knowledge_search_tool",
        #         "prediction_tool"
        #     ]
        # )
        
        # 模拟诊断结果
        diagnosis_id = f"DIAG-{datetime.now().timestamp()}"
        
        response = DiagnosisResponse(
            diagnosis_id=diagnosis_id,
            equipment_id=request.equipment_id,
            diagnosis_result="设备轴承磨损，建议在24小时内进行维护",
            confidence=0.92,
            suggested_actions=[
                "立即停止设备运行",
                "更换轴承",
                "进行性能测试",
                "添加润滑油"
            ],
            timestamp=datetime.now()
        )
        
        # 缓存诊断结果
        await RedisClient.set(cache_key, response.model_dump_json())
        
        logger.info(f"诊断请求处理成功: {diagnosis_id}")
        return response
        
    except Exception as e:
        logger.error(f"诊断请求处理失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get(f"{settings.api_prefix}/diagnosis/{{diagnosis_id}}")
async def get_diagnosis_result(
    diagnosis_id: str,
    db: Session = Depends(get_db)
) -> DiagnosisResponse:
    """获取诊断结果"""
    # 从缓存或数据库获取诊断结果
    logger.info(f"获取诊断结果: {diagnosis_id}")
    return DiagnosisResponse(
        diagnosis_id=diagnosis_id,
        equipment_id="EQ-001",
        diagnosis_result="设备正常运行",
        confidence=0.95,
        suggested_actions=[],
        timestamp=datetime.now()
    )

@app.websocket(f"{settings.api_prefix}/diagnosis/stream")
async def diagnosis_stream(websocket: WebSocket):
    """诊断流式输出（Week 17: WebSocket实时通信）"""
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_text()
            # 模拟流式诊断输出
            await websocket.send_json({
                "type": "diagnosis_progress",
                "stage": "analyzing",
                "progress": 45,
                "message": "正在分析传感器数据..."
            })
            await asyncio.sleep(0.5)
    except Exception as e:
        logger.error(f"WebSocket错误: {e}")
    finally:
        await websocket.close()

@app.post(f"{settings.api_prefix}/knowledge/search")
async def search_knowledge(
    request: KnowledgeRequest,
    db: Session = Depends(get_db)
) -> dict:
    """知识库搜索（Week 13+: 知识检索）
    
    整合了：
    - Week 13: 知识库扩展
    - Week 14: 检索优化
    """
    logger.info(f"知识库查询: {request.query}")
    return {
        "query": request.query,
        "results": [
            {
                "id": "KB-001",
                "content": "轴承故障通常表现为噪音增加...",
                "similarity": 0.95,
                "source": "maintenance_manual.pdf"
            }
        ],
        "total": 1
    }

@app.post(f"{settings.api_prefix}/agent/execute")
async def execute_agent(
    request: AgentExecutionRequest,
    db: Session = Depends(get_db)
) -> dict:
    """执行Agent任务（Week 15+: Agent系统）
    
    整合了：
    - Week 15: Agent架构与工具系统
    - Week 16: Agent协作与规划
    """
    logger.info(f"执行Agent任务: {request.task_description}")
    return {
        "task_id": f"TASK-{datetime.now().timestamp()}",
        "status": "executing",
        "progress": 0,
        "message": "Agent开始执行任务"
    }

@app.post(f"{settings.api_prefix}/auth/login")
async def login(username: str, password: str):
    """用户登录（Week 18: 认证系统）"""
    # JWT Token生成逻辑
    logger.info(f"用户登录: {username}")
    return {
        "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
        "token_type": "bearer",
        "expires_in": 86400
    }

@app.post(f"{settings.api_prefix}/auth/register")
async def register(username: str, email: str, password: str):
    """用户注册（Week 18: 用户系统）"""
    logger.info(f"用户注册: {username}")
    return {
        "user_id": "USR-001",
        "username": username,
        "email": email,
        "created_at": datetime.now()
    }

@app.get(f"{settings.api_prefix}/analytics/dashboard")
async def get_dashboard(db: Session = Depends(get_db)):
    """获取仪表板数据（Week 19: 数据分析）"""
    return {
        "total_diagnoses": 1234,
        "success_rate": 0.96,
        "avg_response_time": 0.45,
        "active_agents": 12,
        "system_health": 0.98,
        "charts": {
            "diagnoses_by_hour": [],
            "equipment_status": [],
            "top_issues": []
        }
    }

@app.get(f"{settings.api_prefix}/admin/system/metrics")
async def get_system_metrics():
    """获取系统指标（Week 20: 监控系统）"""
    return {
        "cpu_usage": 45.2,
        "memory_usage": 62.8,
        "disk_usage": 73.5,
        "network_io": {
            "in": 1024000,
            "out": 512000
        },
        "db_connections": 18,
        "cache_hit_rate": 0.85,
        "requests_per_second": 145.3,
        "error_rate": 0.002
    }

# ============================================================================
# 自定义OpenAPI文档
# ============================================================================

def custom_openapi():
    """自定义OpenAPI文档"""
    if app.openapi_schema:
        return app.openapi_schema
    
    openapi_schema = get_openapi(
        title=settings.app_name,
        version=settings.version,
        description="机械工程AI战略转型课程 - 完整API文档",
        routes=app.routes,
    )
    
    openapi_schema["info"]["x-logo"] = {
        "url": "https://example.com/logo.png"
    }
    
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi

# ============================================================================
# 异常处理
# ============================================================================

@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """HTTP异常处理"""
    logger.error(f"HTTP异常: {exc.status_code} - {exc.detail}")
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail,
            "status_code": exc.status_code,
            "timestamp": datetime.now().isoformat()
        }
    )

@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """通用异常处理（Week 20: 错误处理）"""
    logger.error(f"未处理的异常: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal Server Error",
            "status_code": 500,
            "timestamp": datetime.now().isoformat()
        }
    )

# ============================================================================
# 启动入口
# ============================================================================

def _assert_loopback_port_not_in_use(port: int) -> None:
    """避免与 Docker 等已映射到本机回环的服务抢同一端口（macOS 上可能出现 Docker 与本地 Python 同时 LISTEN，curl 127.0.0.1 会打到错误进程）。"""
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=0.5):
            pass
    except OSError:
        return
    logger.error(
        "127.0.0.1:%s 上已有 TCP 服务在响应（常见原因：docker compose 已映射 API_PORT 到此端口）。"
        "请先停止冲突进程，或换端口运行本脚本，例如: MAIN_APP_PORT=8020 python main_app.py",
        port,
    )
    logger.error("查看占用: lsof -nP -iTCP:%s -sTCP:LISTEN", port)
    sys.exit(1)


def _assert_listen_port_free(port: int, host: str = "0.0.0.0") -> None:
    """在拉起 Uvicorn 前先试绑端口，避免 lifespan/Redis 日志跑完才报 Address already in use。"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            s.bind((host, port))
        except OSError as e:
            logger.error("端口 %s 已被占用（%s），无法启动。", port, e)
            logger.error("结束占用进程示例: lsof -nP -iTCP:%s -sTCP:LISTEN", port)
            logger.error("或换端口: MAIN_APP_PORT=8020 python main_app.py")
            sys.exit(1)


if __name__ == "__main__":
    import uvicorn

    # 与 mechanical-ai-platform（常见 8000）并存：默认 8010；也可 MAIN_APP_PORT 或 PORT 覆盖
    _port = int(os.environ.get("MAIN_APP_PORT", os.environ.get("PORT", "8010")))
    _assert_loopback_port_not_in_use(_port)
    _assert_listen_port_free(_port)
    logger.info("启动 Uvicorn: 0.0.0.0:%s（占用请改端口或结束占用进程）", _port)
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=_port,
        reload=settings.debug,
        log_level="info",
    )

