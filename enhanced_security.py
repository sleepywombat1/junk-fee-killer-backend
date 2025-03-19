# security.py
"""
Enhanced security measures for the Fee Detective API
"""

import secrets
import hashlib
import time
from fastapi import Request, HTTPException, Depends, Security
from fastapi.security import APIKeyHeader
from starlette.status import HTTP_403_FORBIDDEN, HTTP_429_TOO_MANY_REQUESTS
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Rate limiting
class RateLimiter:
    """Simple in-memory rate limiter"""
    
    def __init__(self, requests_per_minute=20):
        self.requests_per_minute = requests_per_minute
        self.request_history = {}  # IP -> list of timestamps
    
    async def check_rate_limit(self, request: Request):
        # Get client IP
        client_ip = request.client.host
        
        # Get current time
        current_time = time.time()
        
        # Initialize or update request history
        if client_ip not in self.request_history:
            self.request_history[client_ip] = []
        
        # Clean up old requests (older than 1 minute)
        self.request_history[client_ip] = [
            t for t in self.request_history[client_ip] 
            if current_time - t < 60
        ]
        
        # Check if rate limit is exceeded
        if len(self.request_history[client_ip]) >= self.requests_per_minute:
            logger.warning(f"Rate limit exceeded for IP: {client_ip}")
            raise HTTPException(
                status_code=HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded. Please try again later."
            )
        
        # Add current request timestamp
        self.request_history[client_ip].append(current_time)
        
        # Clean up rate limiter periodically
        if len(self.request_history) > 10000:  # Arbitrary limit to prevent memory issues
            self._cleanup_old_ips()
    
    def _cleanup_old_ips(self):
        """Remove IPs with no recent activity"""
        current_time = time.time()
        inactive_ips = [
            ip for ip, timestamps in self.request_history.items()
            if not timestamps or current_time - max(timestamps) > 3600  # No activity for 1 hour
        ]
        
        for ip in inactive_ips:
            del self.request_history[ip]

# Create rate limiter instance
rate_limiter = RateLimiter()

# API Key authentication (for partner integrations)
API_KEY_NAME = "X-API-Key"
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)

# In production, these would be stored securely (e.g., in a database)
# This is just for demonstration
API_KEYS = {
    "test-partner-1": hashlib.sha256("partner1-secret-key".encode()).hexdigest(),
    "test-partner-2": hashlib.sha256("partner2-secret-key".encode()).hexdigest(),
}

async def verify_api_key(api_key: str = Security(api_key_header)):
    if api_key is None:
        return None  # Allow anonymous access for regular users
        
    # Check if API key is valid
    if api_key in API_KEYS.values():
        return api_key
        
    logger.warning(f"Invalid API key attempted: {api_key[:10]}...")
    raise HTTPException(
        status_code=HTTP_403_FORBIDDEN,
        detail="Invalid API key"
    )

# Content Security Policy middleware
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    
    # Add security headers
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "script-src 'self'; "
        "style-src 'self'; "
        "img-src 'self' data:; "
        "font-src 'self'; "
        "connect-src 'self'; "
        "frame-ancestors 'none'"
    )
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    
    return response

# Generate a secure token for CSRF protection
def generate_csrf_token():
    return secrets.token_hex(32)

# Verify CSRF token
def verify_csrf_token(request_token, session_token):
    if not request_token or not session_token:
        return False
    return secrets.compare_digest(request_token, session_token)
