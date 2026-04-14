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
        hosts_config = settings.hosts_config

    # LOG INFO : On vérifie que la configuration a bien été chargée
    logger.info(f"Début du cycle de polling. Nombre d'hôtes configurés : {len(hosts_config) if hosts_config else 0}")

    if not hosts_config:
        logger.warning("Aucun hôte configuré. Vérifie que ton fichier .env existe et que HOSTS_CONFIG est bien formaté.")
        return

    for h_conf in hosts_config:
        logger.info(f"[{h_conf.type}] Tentative de connexion et collecte sur {h_conf.ip}...")

        try:
            client = get_client(h_conf)
            data = client.collect()
            vms_count = len(data.get("vms", []))
            logger.info(f"[{h_conf.type}] Collecte réussie sur {h_conf.ip}. {vms_count} VM(s) trouvée(s).")

        except Exception as e:
            logger.error(f"[{h_conf.type}] Échec de la collecte sur {h_conf.ip} : {e}")
            db = SessionLocal()
            try:
                # Ajout dynamique du tag "injoignable"
                fail_tags = h_conf.tags.copy()
                if "injoignable" not in fail_tags:
                    fail_tags.append("injoignable")

                # On cherche le nom actuel en BDD pour ne pas créer un doublon
                existing_host = db.execute(
                    select(models.Host).where(models.Host.ip == h_conf.ip)
                ).scalar_one_or_none()

                db_name = existing_host.name if existing_host else h_conf.ip

                # On met les stats à Null pour indiquer qu'on n'a pas de data fraîche
                upsert_host(
                    db,
                    name=db_name,  # On utilise le nom existant ou l'IP en fallback
                    ip=h_conf.ip,
                    free_disk_gb=None,
                    free_mem_mb=None,
                    cpu_usage_pct=None,
                    total_disk_gb=None,
                    total_mem_mb=None,
                    htype=h_conf.type,
                    tags=fail_tags
                )
                logger.info(f"[{h_conf.type}] Hôte {h_conf.ip} marqué comme injoignable en base.")
            except Exception as inner_e:
                logger.error(f"[{h_conf.type}] Erreur lors de la mise à jour du statut injoignable pour {h_conf.ip} : {inner_e}")
            finally:
                db.close()
            continue  # Passe au host suivant

        # Si la collecte a réussi, on sauvegarde
        db = SessionLocal()
        try:
            host_name = data.get("host_name") or h_conf.ip

            # On s'assure de nettoyer le tag "injoignable" s'il était présent
            success_tags = [t for t in h_conf.tags if t != "injoignable"]

            host_row = upsert_host(
                db,
                name=host_name,
                ip=h_conf.ip,
                free_disk_gb=data.get("host_free_disk_gb"),
                free_mem_mb=data.get("host_free_mem_mb"),
                cpu_usage_pct=data.get("host_cpu_pct"),
                total_disk_gb=data.get("host_total_disk_gb"),
                total_mem_mb=data.get("host_total_mem_mb"),
                htype=h_conf.type,
                tags=success_tags
            )

            vms = data.get("vms", [])
            seen_names = set()

            for vm in vms:
                ip = vm.get("ip")
                if isinstance(ip, dict):
                    ip = json.dumps(ip)

                name = vm.get("name")
                seen_names.add(name)

                upsert_vm(
                    db,
                    host_id=host_row.id,
                    name=name,
                    ip=ip,
                    guest_hostname=vm.get("vm_hostname"),
                    notes=vm.get('notes'),
                    ram_mb=vm.get("ram_mb"),
                    total_vhd_gb=vm.get("total_vhd_gb"),
                    total_vhd_file_gb=vm.get("total_vhd_file_gb"),
                    state=vm.get("state"),
                )

            # Suppression des VMs disparues
            if seen_names:
                q = select(models.VM).where(models.VM.host_id == host_row.id)
                db_vms = db.execute(q).scalars().all()
                for db_vm in db_vms:
                    if db_vm.name not in seen_names:
                        logger.info(f"[{h_conf.type}] Suppression de la VM disparue '{db_vm.name}' sur {h_conf.ip}")
                        db.delete(db_vm)

            db.commit()
            logger.info(f"[{h_conf.type}] Données sauvegardées en BDD avec succès pour {h_conf.ip}.")
        except Exception as inner_e:
            # Sécurité absolue : un bug SQL ne plantera pas les autres hyperviseurs
            logger.error(f"Erreur d'insertion DB pour l'hôte {h_conf.ip}: {inner_e}")
            db.rollback()
        finally:
            db.close()

async def collect_once(hosts: List[str] | None = None):
    await asyncio.to_thread(collect_once_sync, hosts)

async def polling_loop():
    logger.info("Starting polling loop...")
    while True:
        try:
            # Essai global (empêche le crach du thread complet)
            await collect_once()
            logger.info("Fin du cycle de polling. Attente avant le prochain cycle...")
        except Exception as e:
            logger.critical(f"Erreur majeure dans la boucle de polling : {e}")

        # On attend POLL_MINUTES avant de recommencer
        await asyncio.sleep(max(1, settings.poll_minutes) * 60)