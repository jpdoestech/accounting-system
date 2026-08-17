"""
Security headers middleware.

Adds a small, uncontroversial set of response headers that cost
nothing functionally but close off easy attack surface (clickjacking,
MIME-sniffing, leaking the referrer to third parties). Deliberately
does NOT set a Content-Security-Policy here, since a CSP tight enough
to be meaningful has to be tailored to the actual frontend's script/
style sources -- shipping a generic one risks breaking the app while
giving a false sense of security. A production deployment should set
CSP at the reverse-proxy/CDN layer where it can be tuned per
environment without a backend redeploy.
"""
from starlette.middleware.base import BaseHTTPMiddleware


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        return response
