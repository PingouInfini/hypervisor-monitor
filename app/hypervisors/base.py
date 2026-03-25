from abc import ABC, abstractmethod
from typing import Any, Dict

class BaseClient(ABC):
    def __init__(self, host_config):
        self.config = host_config
        self.host_ip = host_config.ip

    @abstractmethod
    def collect(self) -> Dict[str, Any]:
        """
        Doit retourner un dictionnaire contenant :
        - host_name, host_ip, host_cpu_pct, host_free_mem_mb, host_total_mem_mb, tags...
        - vms: liste de dictionnaires (name, state, ip, fqdn, ram_mb, etc.)
        """
        pass