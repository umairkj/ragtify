from pydantic import BaseModel
from typing import Dict, Optional


class SettingsResponse(BaseModel):
    settings: Dict[str, str]


class SettingsUpdateRequest(BaseModel):
    settings: Dict[str, Optional[str]]

