from pydantic import BaseModel
from typing import Dict, List, Optional
from datetime import datetime

class Rocket(BaseModel):
    id: str
    name: str

class Launchpad(BaseModel):
    id: str
    name: str

class Launch(BaseModel):
    id: str
    name: str
    date_utc: datetime
    rocket: Rocket
    success: Optional[bool]
    launchpad: Launchpad

class PaginatedResponse(BaseModel):
    total: int
    limit: int
    offset: int
    data: List[Launch]
    next: Optional[str] = None
    previous: Optional[str] = None

class RocketStats(BaseModel):
    rocket_name: str
    total: int
    success: int
    success_rate: float

class LaunchpadStats(BaseModel):
    launchpad_name: str
    total: int

class FrequencyStats(BaseModel):
    by_month: Dict[str, int]
    by_year: Dict[int, int]