import time
import logging

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

logger = logging.getLogger("insighta.access")

# Configure structured logging once
logging.basicConfig(
    level=logging.INFO,
    format='{"time":"%(asctime)s","level":"%(levelname)s","message":%(message)s}',
    datefmt="%Y-%m-%dT%H:%M:%SZ",
)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Logs every request: method, endpoint, status code, response time.
    """
    async def dispatch(self, request: Request, call_next):
        start = time.perf_counter()
        response = await call_next(request)
        elapsed_ms = (time.perf_counter() - start) * 1000

        logger.info(
            '"method":"%s","endpoint":"%s","status":%d,"response_time_ms":%.2f',
            request.method,
            request.url.path,
            response.status_code,
            elapsed_ms,
        )
        return response
