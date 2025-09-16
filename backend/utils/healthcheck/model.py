from typing import List, Optional, Union
from .enum import HealthCheckStatusEnum
from datetime import datetime
from pydantic import BaseModel
from conf import settings


class HealthCheckEntityModel(BaseModel):
    alias: str
    status: Union[HealthCheckStatusEnum, str] = HealthCheckStatusEnum.HEALTHY
    timeTaken: Union[Optional[datetime], str] = None
    tags: List[str] = list()


class HealthCheckModel(BaseModel):
    version: Optional[str] = settings.PROJECT_VERSION
    status: Union[HealthCheckStatusEnum, str] = HealthCheckStatusEnum.HEALTHY
    totalTimeTaken: Union[Optional[datetime], str] = None
    entities: List[HealthCheckEntityModel] = list()
