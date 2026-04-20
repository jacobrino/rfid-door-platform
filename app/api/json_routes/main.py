from fastapi import APIRouter

from app.api.json_routes.auth_api import router as auth_api_router
from app.api.json_routes.dashboard_api import router as dashboard_api_router
from app.api.json_routes.authorized_users_api import router as authorized_users_api_router
from app.api.json_routes.staff_users_api import router as staff_users_api_router
from app.api.json_routes.rfid_cards_api import router as rfid_cards_api_router
from app.api.json_routes.assignments_api import router as assignments_api_router
from app.api.json_routes.devices_api import router as devices_api_router
from app.api.json_routes.access_logs_api import router as access_logs_api_router

router = APIRouter()

router.include_router(auth_api_router)
router.include_router(dashboard_api_router)
router.include_router(authorized_users_api_router)
router.include_router(staff_users_api_router)
router.include_router(rfid_cards_api_router)
router.include_router(assignments_api_router)
router.include_router(devices_api_router)
router.include_router(access_logs_api_router)