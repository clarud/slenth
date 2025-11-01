"""
Main FastAPI application for SLENTH AML Monitoring System.
"""
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import time
from loguru import logger

from config import settings
from db.database import init_db
from app.api import transactions, documents, internal_rules, alerts, cases, health


def _mask_url(url: str) -> str:
    try:
        if "@" in url and "://" in url:
            scheme, rest = url.split("://", 1)
            if "@" in rest:
                creds, host = rest.split("@", 1)
                return f"{scheme}://***:***@{host}"
        return url
    except Exception:
        return url

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup
    logger.info("Starting SLENTH AML Monitoring System...")
    logger.info(f"Environment: {settings.app_env}")
    logger.info(f"Debug mode: {settings.debug}")
    try:
        logger.info(f"DB URL: {_mask_url(str(settings.database_url))}")
    except Exception:
        pass
    
    # Initialize database
    try:
        init_db()
        logger.info("✅ Database initialized")
    except Exception as e:
        logger.error(f"❌ Database initialization failed: {e}")
        raise
    
    logger.info("🚀 Application startup complete")
    
    yield
    
    # Shutdown
    logger.info("Shutting down SLENTH AML Monitoring System...")


# Create FastAPI app
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Agentic AI for Real-Time AML Monitoring and Document Corroboration",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all HTTP requests."""
    start_time = time.time()
    
    # Log request
    logger.info(f"➡️  {request.method} {request.url.path}")
    
    try:
        response = await call_next(request)
        process_time = time.time() - start_time
        
        # Log response
        logger.info(
            f"⬅️  {request.method} {request.url.path} "
            f"Status: {response.status_code} "
            f"Duration: {process_time:.3f}s"
        )
        
        # Add custom headers
        response.headers["X-Process-Time"] = str(process_time)
        return response
    
    except Exception as e:
        process_time = time.time() - start_time
        logger.error(
            f"❌ {request.method} {request.url.path} "
            f"Error: {str(e)} "
            f"Duration: {process_time:.3f}s"
        )
        raise


# Exception handlers
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Handle all uncaught exceptions."""
    logger.exception(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "message": str(exc) if settings.debug else "An error occurred",
            "path": request.url.path,
        },
    )


# Include routers
app.include_router(health.router, prefix="/health", tags=["Health"])
# transactions and documents routers already define their own prefixes;
# avoid double-prefixing here.
app.include_router(transactions.router, tags=["Transactions (Part 1)"])
app.include_router(documents.router, tags=["Documents (Part 2)"])
app.include_router(internal_rules.router, prefix="/internal_rules", tags=["Internal Rules"])
app.include_router(alerts.router, prefix="/alerts", tags=["Alerts"])
app.include_router(cases.router, prefix="/cases", tags=["Cases"])


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint with system information."""
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "environment": settings.app_env,
        "docs": "/docs",
        "health": "/health",
        "status": "operational",
    }


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.api_reload,
        log_level=settings.log_level.lower(),
    )
