import logging
import time

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from valuation_service.api.endpoints import router as api_router

# Setup logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("valuation_service")

app = FastAPI(title="Valuation Engine API", version="0.1.0")

app.include_router(api_router)

@app.middleware("http")
async def log_requests(request: Request, call_next):
    logger.info(f"Incoming request: {request.method} {request.url.path}")
    start_time = time.time()
    try:
        response = await call_next(request)
        process_time = time.time() - start_time
        logger.info(f"Request completed: {request.method} {request.url.path} Status: {response.status_code} Time: {process_time:.4f}s")
        return response
    except Exception as e:
        process_time = time.time() - start_time
        logger.error(f"Request failed: {request.method} {request.url.path} Error: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal Server Error"}
        )

@app.get("/")
def read_root():
    return {"message": "Valuation Engine API is running"}
