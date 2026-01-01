from fastapi import HTTPException
from sqlalchemy.orm import Session
from app.models.settings import Settings
from app.services.ContentService import content_service


class SettingsService:
    def get_all_settings(self, db: Session):
        """Get all settings from database"""
        try:
            settings = db.query(Settings).all()
            return {setting.key: setting.value for setting in settings}
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to get settings: {str(e)}")
    
    def update_settings(self, db: Session, settings_dict: dict):
        """Update settings in database"""
        try:
            for key, value in settings_dict.items():
                setting = db.query(Settings).filter(Settings.key == key).first()
                if setting:
                    setting.value = str(value) if value is not None else None
                else:
                    # Create new setting if it doesn't exist
                    setting = Settings(key=key, value=str(value) if value is not None else None)
                    db.add(setting)
            
            db.commit()
            
            # Invalidate cache in ContentService so it reloads settings
            content_service._invalidate_settings_cache()
            
            return {"status": "success", "updated": list(settings_dict.keys())}
        except Exception as e:
            db.rollback()
            raise HTTPException(status_code=500, detail=f"Failed to update settings: {str(e)}")
    
    def get_setting(self, db: Session, key: str):
        """Get a single setting by key"""
        try:
            setting = db.query(Settings).filter(Settings.key == key).first()
            if setting:
                return {"key": setting.key, "value": setting.value}
            else:
                raise HTTPException(status_code=404, detail=f"Setting '{key}' not found")
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to get setting: {str(e)}")


# Create a global instance of the service
settings_service = SettingsService()

