"""
Middleware components for VerificAI Backend
"""

import time
import uuid
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.base import RequestResponseEndpoint
from starlette.responses import JSONResponse

from app.core.logging import request_logger, security_logger
from app.core.exceptions import RateLimitExceededError


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Add request ID to all requests"""

    async def dispatch(
        self,
        request: Request,
        call_next: Callable
    ) -> Response:
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id

        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id

        return response


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Log HTTP requests and responses"""

    async def dispatch(
        self,
        request: Request,
        call_next: Callable
    ) -> Response:
        start_time = time.time()

        # Extract user info if available
        user_id = None
        if hasattr(request.state, 'user'):
            user_id = request.state.user.id

        # Extract IP address
        ip_address = request.client.host if request.client else None

        # Get request ID
        request_id = getattr(request.state, 'request_id', None)

        response = await call_next(request)

        # Calculate processing time
        processing_time = time.time() - start_time

        # Log the request
        request_logger.log_request(
            method=request.method,
            url=str(request.url),
            status_code=response.status_code,
            response_time=processing_time,
            user_id=user_id,
            ip_address=ip_address,
            request_id=request_id
        )

        return response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security headers to responses"""

    async def dispatch(
        self,
        request: Request,
        call_next: Callable
    ) -> Response:
        response = await call_next(request)

        # Don't add security headers to OPTIONS requests (CORS preflight)
        if request.method == "OPTIONS":
            return response

        # Add security headers
        security_headers = {
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "X-XSS-Protection": "1; mode=block",
            "Referrer-Policy": "strict-origin-when-cross-origin",
            "Permissions-Policy": "geolocation=(), microphone=(), camera=()",
            # CSP: allow Vercel frontend + Vercel live feedback + Render backend + localhost for dev
            "Content-Security-Policy": (
                "default-src 'self'; "
                "script-src 'self' 'unsafe-inline' https://vercel.live https://cdn.jsdelivr.net; "
                "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
                "img-src 'self' data: https:; "
                "font-src 'self' https:; "
                "connect-src 'self' https://*.vercel.app https://*.vercel.live https://*.onrender.com "
                "http://localhost:* http://127.0.0.1:*"
            )
        }

        for header, value in security_headers.items():
            response.headers[header] = value

        return response


class ErrorHandlerMiddleware(BaseHTTPMiddleware):
    """Global error handler middleware"""

    async def dispatch(
        self,
        request: Request,
        call_next: Callable
    ) -> Response:
        try:
            response = await call_next(request)
            return response
        except Exception as exc:
            # Get request info for logging
            request_id = getattr(request.state, 'request_id', None)
            ip_address = request.client.host if request.client else None

            # Log the error with full traceback
            import traceback
            print(f"ERROR: {exc}")
            print(f"TRACEBACK: {traceback.format_exc()}")

            security_logger.log_security_event(
                event_type="request_error",
                description=f"Error processing request: {str(exc)}",
                severity="ERROR",
                ip_address=ip_address
            )

            # Return appropriate error response
            if hasattr(exc, 'status_code'):
                return JSONResponse(
                    status_code=exc.status_code,
                    content={
                        "error_code": getattr(exc, 'error_code', 'UNKNOWN_ERROR'),
                        "message": str(exc),
                        "request_id": request_id
                    }
                )

            # For unhandled exceptions
            return JSONResponse(
                status_code=500,
                content={
                    "error_code": "INTERNAL_ERROR",
                    "message": "Internal server error",
                    "request_id": request_id
                }
            )


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Simple rate limiting middleware"""

    def __init__(self, app, requests_per_minute: int = 60):
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.request_counts = {}

    async def dispatch(
        self,
        request: Request,
        call_next: Callable
    ) -> Response:
        client_ip = request.client.host
        current_time = int(time.time())

        # Clean old entries (older than 1 minute)
        cutoff_time = current_time - 60
        self.request_counts = {
            ip: times for ip, times in self.request_counts.items()
            if times and times[-1] > cutoff_time
        }

        # Check rate limit
        if client_ip not in self.request_counts:
            self.request_counts[client_ip] = []

        recent_requests = [
            t for t in self.request_counts[client_ip]
            if t > cutoff_time
        ]

        if len(recent_requests) >= self.requests_per_minute:
            raise RateLimitExceededError(
                message="Rate limit exceeded",
                retry_after=60
            )

        # Record this request
        self.request_counts[client_ip].append(current_time)

        return await call_next(request)