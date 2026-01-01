from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from fastapi_utils.cbv import cbv
from app.schemas.settings import SettingsResponse, SettingsUpdateRequest
from app.services.SettingsService import settings_service
from app.db.session import get_db

router = APIRouter()


@cbv(router)
class SettingsAPI:
    def __init__(self, db: Session = Depends(get_db)):
        self.db = db

    @router.get("/", response_model=SettingsResponse)
    def get_settings(self):
        """Get all settings"""
        settings = settings_service.get_all_settings(self.db)
        return SettingsResponse(settings=settings)

    @router.put("/")
    def update_settings(self, request: SettingsUpdateRequest):
        """Update settings"""
        return settings_service.update_settings(self.db, request.settings)

