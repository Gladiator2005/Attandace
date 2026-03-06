import time
import asyncio
from collections import defaultdict, deque
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

# Rate limit rules: { path_prefix: (max_requests, window_seconds) }
RATE_LIMITS = {
    "/api/auth/login":     (5, 60),    # 5 attempts per 60s
    "/api/face/":          (10, 60),   # 10 face scans per 60s
    "/api/subjects/face-scan": (10, 60),
}

# ip+path -> deque of timestamps
_request_log: dict = defaultdict(deque)
_lock = asyncio.Lock()


def _get_limit(path: str):
    for prefix, rule in RATE_LIMITS.items():
        if path.startswith(prefix):
            return rule
    return None


class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        rule = _get_limit(request.url.path)
        if rule:
            max_req, window = rule
            ip = request.client.host if request.client else "unknown"
            key = f"{ip}:{request.url.path}"
            now = time.monotonic()

            async with _lock:
                dq = _request_log[key]
                # Remove expired timestamps
                while dq and now - dq[0] > window:
                    dq.popleft()

                if len(dq) >= max_req:
                    retry_after = int(window - (now - dq[0])) + 1
                    return JSONResponse(
                        status_code=429,
                        content={
                            "detail": f"Too many requests. Try again in {retry_after} seconds.",
                            "retry_after": retry_after,
                        },
                        headers={"Retry-After": str(retry_after)},
                    )
                dq.append(now)

        return await call_next(request)
