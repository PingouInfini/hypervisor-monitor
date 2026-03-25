from ..config import HostConfig
from .hyperv import HyperVClient
from .proxmox import ProxmoxClient
from .esxi import ESXiClient

def get_client(host_config: HostConfig):
    ctype = host_config.type.lower()
    if ctype == "hyperv":
        return HyperVClient(host_config)
    elif ctype == "proxmox":
        return ProxmoxClient(host_config)
    elif ctype == "esxi":
        return ESXiClient(host_config)
    else:
        raise ValueError(f"Type d'hyperviseur non pris en charge: {ctype}")