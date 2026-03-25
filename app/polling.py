import asyncio
import json
import logging
import os
from typing import List

from sqlalchemy import select

from . import models
from .config import settings
from .crud import upsert_host, upsert_vm
from .db import SessionLocal
from .hypervisors import get_client

# --- Logger setup ---
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    level=getattr(logging, LOG_LEVEL, logging.INFO),
)
logger = logging.getLogger(__name__)


def collect_once_sync(hosts_config=None):
    if hosts_config is None:
        hosts_config = settings.hosts_config  # C'est maintenant une liste d'objets HostConfig

    for h_conf in hosts_config:
        logger.debug(f"Collecting metrics from {h_conf.type} host {h_conf.ip}...")
        try:
            client = get_client(h_conf)
            data = client.collect()
            logger.debug(f"Successfully connected to {h_conf.ip}")
        except Exception as e:
            logger.error(f"Failed to collect from host {h_conf.ip}: {e}")
            db = SessionLocal()
            try:
                # On persiste le host même en cas d'échec
                upsert_host(db, name=h_conf.ip, ip=h_conf.ip, free_disk_gb=None, free_mem_mb=None, htype=h_conf.type,
                            tags=h_conf.tags)
            finally:
                db.close()
            continue

        db = SessionLocal()
        try:
            # Sécurité : Si l'API/Script ne remonte pas le hostname, on utilise l'IP
            host_name = data.get("host_name") or h_conf.ip

            host_row = upsert_host(
                db,
                name=host_name,
                ip=h_conf.ip,  # On force l'IP issue de la config pour être sûr
                free_disk_gb=data.get("host_free_disk_gb"),
                free_mem_mb=data.get("host_free_mem_mb"),
                cpu_usage_pct=data.get("host_cpu_pct"),
                total_disk_gb=data.get("host_total_disk_gb"),
                total_mem_mb=data.get("host_total_mem_mb"),
                htype=h_conf.type,
                tags=h_conf.tags
            )
            vms = data.get("vms", [])
            seen_names = set()
            if vms:
                logger.debug(f"Host {h_conf}: found {len(vms)} VMs")

                for vm in vms:
                    ip = vm.get("ip")
                    if isinstance(ip, dict):
                        ip = json.dumps(ip)

                    name = vm.get("name")
                    seen_names.add(name)

                    logger.debug(f"Processing VM '{vm.get('name')}' on host {h_conf}")
                    upsert_vm(
                        db,
                        host_id=host_row.id,
                        name=name,
                        ip=ip,
                        guest_hostname=vm.get("vm_hostname"),
                        fqdn=vm.get('fqdn'),
                        ram_mb=vm.get("ram_mb"),
                        total_vhd_gb=vm.get("total_vhd_gb"),
                        total_vhd_file_gb=vm.get("total_vhd_file_gb"),
                        state=vm.get("state"),
                    )

            # --- suppression des VMs disparues ---
            if seen_names:
                q = select(models.VM).where(models.VM.host_id == host_row.id)
                db_vms = db.execute(q).scalars().all()
                for db_vm in db_vms:
                    if db_vm.name not in seen_names:
                        logger.info(f"Removing VM '{db_vm.name}' (no longer present on host {h_conf})")
                        db.delete(db_vm)

            db.commit()
        finally:
            db.close()


async def collect_once(hosts: List[str] | None = None):
    """Version asynchrone : exécute la collecte synchrone dans un thread"""
    await asyncio.to_thread(collect_once_sync, hosts)


async def polling_loop():
    logger.info("Starting polling loop...")
    # Première collecte immédiate
    await collect_once()
    # Boucle infinie
    while True:
        await asyncio.sleep(max(1, settings.poll_minutes) * 60)
        await collect_once()
