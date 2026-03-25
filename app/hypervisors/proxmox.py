import logging
from typing import Any, Dict
from proxmoxer import ProxmoxAPI
from .base import BaseClient

logger = logging.getLogger(__name__)

class ProxmoxClient(BaseClient):
    def collect(self) -> Dict[str, Any]:
        # Connexion à l'API Proxmox
        proxmox = ProxmoxAPI(
            self.host_ip,
            user=self.config.username,
            password=self.config.password,
            verify_ssl=False
        )

        # Récupération du premier nœud (généralement suffisant si non-cluster, sinon adapter)
        node = proxmox.nodes.get()[0]['node']
        status = proxmox.nodes(node).status.get()

        host_cpu_pct = round(status.get('cpu', 0) * 100, 1)
        total_mem_mb = int(status.get('memory', {}).get('total', 0) / 1048576)
        free_mem_mb = int(status.get('memory', {}).get('free', 0) / 1048576)

        # Disque (Root)
        total_disk_gb = round(status.get('rootfs', {}).get('total', 0) / 1073741824, 2)
        free_disk_gb = round(status.get('rootfs', {}).get('avail', 0) / 1073741824, 2)

        vms_data = []

        # Parcours des VMs (QEMU)
        for vm in proxmox.nodes(node).qemu.get():
            vmid = vm.get('vmid')
            state = "Running" if vm.get('status') == 'running' else "Stopped"

            # Tentative de récupération de l'IP via QEMU Guest Agent
            ip_address = None
            if state == "Running":
                try:
                    # Nécessite que l'agent QEMU soit activé et fonctionnel
                    ifaces = proxmox.nodes(node).qemu(vmid).agent('network-get-interfaces').get()
                    for iface in ifaces.get('result', []):
                        for addr in iface.get('ip-addresses', []):
                            if addr['ip-address-type'] == 'ipv4' and not addr['ip-address'].startswith('127.'):
                                ip_address = addr['ip-address']
                                break
                        if ip_address:
                            break
                except Exception as e:
                    # Agent non installé ou injoignable
                    logger.debug(f"Agent inactif ou injoignable sur VM {vmid}: {e}")

            vms_data.append({
                "name": vm.get('name'),
                "state": state,
                "ip": ip_address,
                "ram_mb": int(vm.get('maxmem', 0) / 1048576),
                "total_vhd_gb": round(vm.get('maxdisk', 0) / 1073741824, 2)
            })

        return {
            "host_name": node,
            "host_ip": self.host_ip,
            "tags": self.config.tags,
            "host_cpu_pct": host_cpu_pct,
            "host_free_mem_mb": free_mem_mb,
            "host_total_mem_mb": total_mem_mb,
            "host_free_disk_gb": free_disk_gb,
            "host_total_disk_gb": total_disk_gb,
            "vms": vms_data
        }