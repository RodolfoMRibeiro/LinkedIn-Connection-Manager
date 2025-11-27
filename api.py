"""
LinkedIn Profile Scraper API

A FastAPI application that scrapes LinkedIn profiles.
The browser session is initialized once on startup and reused for all requests.
"""
import asyncio
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel, HttpUrl

from linkedin.linkedin_service import linkedin_service


class ProfileResponse(BaseModel):
    """Response model for profile data."""
    success: bool
    data: Optional[dict] = None
    error: Optional[str] = None


class HealthResponse(BaseModel):
    """Response model for health check."""
    status: str
    service: dict


class ScrapeRequest(BaseModel):
    """Request model for scraping a profile."""
    url: HttpUrl


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for FastAPI.
    Handles startup (login) and shutdown (cleanup).
    """
    # Startup: Initialize LinkedIn service
    print("=" * 50)
    print("Starting LinkedIn Scraper API...")
    print("=" * 50)
    
    # Run initialization in a thread pool to not block
    loop = asyncio.get_event_loop()
    success = await loop.run_in_executor(None, linkedin_service.initialize)
    
    if not success:
        print("WARNING: LinkedIn service failed to initialize!")
        print("The API will start but scraping won't work until session is recovered.")
    
    yield
    
    # Shutdown: Clean up resources
    print("=" * 50)
    print("Shutting down LinkedIn Scraper API...")
    print("=" * 50)
    
    await loop.run_in_executor(None, linkedin_service.shutdown)


# Create FastAPI app
app = FastAPI(
    title="LinkedIn Profile Scraper API",
    description="API for scraping LinkedIn profiles. Session is managed automatically.",
    version="1.0.0",
    lifespan=lifespan,
)


@app.get("/", tags=["Root"])
async def root():
    """Root endpoint with API information."""
    return {
        "name": "LinkedIn Profile Scraper API",
        "version": "1.0.0",
        "endpoints": {
            "scrape": "/scrape?url=<linkedin_profile_url>",
            "health": "/health",
        }
    }


@app.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check():
    """
    Health check endpoint.
    Returns the status of the LinkedIn service.
    """
    status = linkedin_service.get_status()
    
    return HealthResponse(
        status="healthy" if linkedin_service.is_ready else "degraded",
        service=status
    )


@app.get("/scrape", response_model=ProfileResponse, tags=["Scrape"])
async def scrape_profile(
    url: str = Query(
        ...,
        description="LinkedIn profile URL to scrape",
        example="https://www.linkedin.com/in/username"
    )
):
    """
    Scrape a LinkedIn profile.
    
    Args:
        url: The LinkedIn profile URL to scrape
        
    Returns:
        ProfileResponse with the scraped data or error message
    """
    # Validate URL format
    if not url.startswith("https://www.linkedin.com/in/"):
        raise HTTPException(
            status_code=400,
            detail="Invalid LinkedIn profile URL. Must start with 'https://www.linkedin.com/in/'"
        )
    
    # Check if service is ready
    if not linkedin_service.is_ready:
        # Try to recover
        loop = asyncio.get_event_loop()
        recovered = await loop.run_in_executor(None, linkedin_service._recover_session)
        
        if not recovered:
            raise HTTPException(
                status_code=503,
                detail="LinkedIn service is not available. Please try again later."
            )
    
    try:
        # Run scraping in thread pool to not block async
        loop = asyncio.get_event_loop()
        profile_data = await loop.run_in_executor(
            None,
            linkedin_service.scrape_profile,
            url
        )
        
        return ProfileResponse(
            success=True,
            data=profile_data
        )
        
    except Exception as e:
        error_message = str(e)
        print(f"ERROR: Failed to scrape {url}: {error_message}")
        
        return ProfileResponse(
            success=False,
            error=error_message
        )


@app.post("/scrape", response_model=ProfileResponse, tags=["Scrape"])
async def scrape_profile_post(request: ScrapeRequest):
    """
    Scrape a LinkedIn profile (POST version).
    
    Args:
        request: ScrapeRequest with the profile URL
        
    Returns:
        ProfileResponse with the scraped data or error message
    """
    return await scrape_profile(str(request.url))


# Error handlers
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler for unhandled errors."""
    print(f"ERROR: Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": "Internal server error",
            "detail": str(exc)
        }
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "api:app",
        host="0.0.0.0",
        port=8000,
        reload=False,  # Don't reload - we want to keep the session
        workers=1,     # Single worker to maintain one session
    )

