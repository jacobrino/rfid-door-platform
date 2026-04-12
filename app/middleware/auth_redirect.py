from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import RedirectResponse


class AuthRedirectMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        user_id = request.session.get("user_id")

        public_paths = {
            "/",
            "/logout",
            "/openapi.json",
            "/docs",
            "/docs/oauth2-redirect",
            "/redoc",
        }

        public_prefixes = (
            "/static/",
            "/api/",
        )

        if path.startswith(public_prefixes):
            return await call_next(request)

        # Si déjà connecté, /login redirige vers /dashboard
        if path == "/login" and user_id:
            return RedirectResponse(url="/dashboard", status_code=303)

        # Routes publiques autorisées sans connexion
        if path in public_paths or path == "/login":
            return await call_next(request)

        # Toute autre route web protégée redirige vers /login si non connecté
        if not user_id:
            return RedirectResponse(url="/login", status_code=303)

        return await call_next(request)