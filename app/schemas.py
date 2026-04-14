from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel


class VMBase(BaseModel):
    id: int
    host_id: int
    name: str
    guest_hostname: Optional[str] = None
    notes: Optional[str] = None
    ip: Optional[str] = None
    ram_mb: Optional[int] = None
    total_vhd_gb: Optional[float] = None
    total_vhd_file_gb: Optional[float] = None
    last_seen: Optional[datetime] = None
    state: Optional[str] = None

    class Config:
        from_attributes = True


class HostBase(BaseModel):
    id: int
    name: str
    ip: Optional[str] = None
    type: Optional[str] = None
    tags: Optional[List[str]] = []
    free_disk_gb: Optional[float] = None
    free_mem_mb: Optional[int] = None
    last_seen: Optional[datetime] = None
    cpu_usage_pct: Optional[float] = None
    total_disk_gb: Optional[float] = None
    total_mem_mb: Optional[int] = None

    class Config:
        from_attributes = True


class HostWithVMs(HostBase):
    vms: List[VMBase] = []
