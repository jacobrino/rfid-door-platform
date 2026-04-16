from app.main import app
from fastapi.routing import APIRoute

print("\nListe des routes :\n")

for route in app.routes:
    if isinstance(route, APIRoute):
        methods = ", ".join(sorted(route.methods))
        print(f"{methods:15} {route.path:45} name={route.name}")