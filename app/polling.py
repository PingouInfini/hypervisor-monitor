import asyncio
import json
import logging
import os
from typing import List

from .config import settings
from .crud import upsert_host, upsert_vm
from .db import SessionLocal
from .hyperv.client import HyperVClient, WinRMConfig

# --- Logger setup ---
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    level=getattr(logging, LOG_LEVEL, logging.INFO),
)
logger = logging.getLogger(__name__)


def get_client(host: str) -> HyperVClient:
    cfg = WinRMConfig(
        username=settings.winrm_username,
        password=settings.winrm_password,
        use_ssl=settings.winrm_use_ssl,
        port=settings.winrm_port,
        verify_ssl=settings.winrm_verify_ssl,
    )
    return HyperVClient(host, cfg)


async def collect_once(hosts: List[str] | None = None):
    if hosts is None:
        hosts = settings.hosts
    for h in hosts:
        logger.debug(f"Collecting metrics from host {h}...")
        try:
            client = get_client(h)
            data = client.collect()
            logger.debug(f"Successfully connected to {h} via WinRM")
        except Exception as e:
            logger.error(f"Failed to collect from host {h}: {e}")
            # On échec, on persiste au moins le host avec valeurs nulles
            db = SessionLocal()
            upsert_host(db, h, ip=None, free_disk_gb=None, free_mem_mb=None)
            db.close()
            continue

        db = SessionLocal()
        try:
            host_row = upsert_host(
                db,
                h,
                ip=data.get("host_ip"),
                free_disk_gb=data.get("host_free_disk_gb"),
                free_mem_mb=data.get("host_free_mem_mb"),
            )
            vms = data.get("vms", [])
            if vms:
                logger.debug(f"Host {h}: found {len(vms)} VMs")

                for vm in vms:
                    ip = vm.get("ip")
                    if isinstance(ip, dict):
                        ip = json.dumps(ip)

                    logger.debug(f"Processing VM '{vm.get('name')}' on host {h}")
                    upsert_vm(
                        db,
                        host_id=host_row.id,
                        name=vm.get("name"),
                        ip=ip,
                        guest_hostname=vm.get("vm_hostname"),
                        ram_mb=vm.get("ram_mb"),
                        total_vhd_gb=vm.get("total_vhd_gb"),
                        total_vhd_file_gb=vm.get("total_vhd_file_gb"),
                    )
        finally:
            db.close()


async def polling_loop():
    logger.info("Starting polling loop...")
    # Première collecte immédiate
    await collect_once()
    # Boucle infinie
    while True:
        await asyncio.sleep(max(1, settings.poll_minutes) * 60)
        await collect_once()
