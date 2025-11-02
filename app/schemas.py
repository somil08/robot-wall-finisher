from pydantic import BaseModel
from typing import List, Optional

class ObstacleIn(BaseModel):
    name: Optional[str] = None
    x: float
    y: float
    w: float
    h: float

class WallIn(BaseModel):
    name: str
    width: float
    height: float
    step: Optional[float] = 0.1
    obstacles: Optional[List[ObstacleIn]] = []
