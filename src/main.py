"""
FastAPI Application Entry Point

This is the main entry point for the Intelligent Support Router API.
"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from loguru import logger

from src.config import settings
from src.database import close_db, init_db

# Import routers
from src.api.tickets import router as tickets_router
from src.api.analytics import router as analytics_router
from src.api.config_api import router as config_router
from src.api.webhooks import router as webhooks_router
from src.api.health import router as health_router
from src.api.agents import router as agents_router


# -----------------------------------------------------------------------------
# Application Lifespan
# -----------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator:
    """
    Application lifespan context manager.
    
    Handles startup and shutdown events.
    """
    # Startup
    logger.info("Starting Intelligent Support Router...")
    logger.info(f"Environment: {settings.app_env}")
    logger.info(f"Debug mode: {settings.debug}")
    
    # Initialize database
    try:
        await init_db()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise
    
    # Initialize vector database (ChromaDB)
    try:
        from src.services.rag import knowledge_base
        await knowledge_base.initialize()
        logger.info("Knowledge base initialized successfully")
    except Exception as e:
        logger.warning(f"Failed to initialize knowledge base: {e}")
    
    logger.info("Application started successfully!")
    
    yield
    
    # Shutdown
    logger.info("Shutting down application...")
    await close_db()
    logger.info("Application shutdown complete")


# -----------------------------------------------------------------------------
# Application Factory
# -----------------------------------------------------------------------------

def create_application() -> FastAPI:
    """
    Application factory function.
    
    Returns:
        FastAPI: Configured FastAPI application
    """
    app = FastAPI(
        title=settings.app_name,
        description="""
        🎯 **Intelligent Support Router**
        
        Open-source AI-powered customer support ticket routing system.
        
        ## Features
        
        - 🤖 AI-powered ticket classification
        - 🎯 Smart agent routing
        - 📊 Priority scoring
        - 💬 Sentiment analysis
        - 🔍 Suggested responses via RAG
        - 🔌 Multiple integrations
        
        ## Documentation
        
        - [GitHub Repository](https://github.com/meryemsakin/supportiq)
        - [API Documentation](/docs)
        - [ReDoc](/redoc)
        """,
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url=f"{settings.api_v1_prefix}/openapi.json",
        lifespan=lifespan,
    )
    
    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Include routers
    app.include_router(
        health_router,
        prefix=f"{settings.api_v1_prefix}",
        tags=["Health"]
    )
    app.include_router(
        tickets_router,
        prefix=f"{settings.api_v1_prefix}/tickets",
        tags=["Tickets"]
    )
    app.include_router(
        agents_router,
        prefix=f"{settings.api_v1_prefix}/agents",
        tags=["Agents"]
    )
    app.include_router(
        analytics_router,
        prefix=f"{settings.api_v1_prefix}/analytics",
        tags=["Analytics"]
    )
    app.include_router(
        config_router,
        prefix=f"{settings.api_v1_prefix}/config",
        tags=["Configuration"]
    )
    app.include_router(
        webhooks_router,
        prefix=f"{settings.api_v1_prefix}/webhooks",
        tags=["Webhooks"]
    )
    
    # Global exception handler
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        """Handle all unhandled exceptions."""
        logger.error(f"Unhandled exception: {exc}", exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "detail": "Internal server error",
                "message": str(exc) if settings.debug else "An unexpected error occurred"
            }
        )
    
    return app


# -----------------------------------------------------------------------------
# Application Instance
# -----------------------------------------------------------------------------

app = create_application()


# -----------------------------------------------------------------------------
# Root Endpoint
# -----------------------------------------------------------------------------

@app.get("/", tags=["Root"])
async def root():
    """
    Root endpoint - returns basic API information.
    """
    return {
        "name": settings.app_name,
        "version": "0.1.0",
        "status": "running",
        "docs": "/docs",
        "health": f"{settings.api_v1_prefix}/health"
    }
