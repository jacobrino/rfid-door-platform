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

        if path == request.url_for("auth.login.index").path and user_id:
            return RedirectResponse(url=request.url_for("dashboard.index"), status_code=303)

        # Routes publiques autorisées sans connexion
        if path in public_paths or path == request.url_for("auth.login.index").path:
            return await call_next(request)

        # Toute autre route web protégée redirige vers /login si non connecté
        if not user_id:
            return RedirectResponse(url=request.url_for("auth.login.index"), status_code=303)

        return await call_next(request)