import json
import re
import socket
from typing import Any, Dict

import winrm
from ..config import settings
from .base import BaseClient

class HyperVClient(BaseClient):
    def __init__(self, host_config):
        super().__init__(host_config)

        # Priorité aux identifiants spécifiques du host, sinon paramètres globaux
        user = self.config.username or settings.winrm_username
        pwd = self.config.password or settings.winrm_password

        protocol = "https" if settings.winrm_use_ssl else "http"
        self.url = f"{protocol}://{self.host_ip}:{settings.winrm_port}/wsman"

        #self.session = winrm.Session(
        #    self.url,
        #    auth=(user, pwd),
        #    server_cert_validation=("validate" if settings.winrm_verify_ssl else "ignore"),
        #    transport='credssp',
        #    operation_timeout_sec=10,
        #    read_timeout_sec=15
        #)

        self.session = winrm.Session(
            self.url,
            auth=(user, pwd),
            transport='ntlm',
            server_cert_validation="ignore"
        )

    def _run_ps_json(self, script: str) -> Dict[str, Any]:
        # On sauvegarde le timeout par défaut (généralement None, soit infini)
        default_timeout = socket.getdefaulttimeout()

        try:
            # On force un timeout brutal de 15 secondes au niveau de la carte réseau
            # Ça tuera la requête même si credssp ou WMI bloque.
            socket.setdefaulttimeout(15.0)

            r = self.session.run_ps(script)

            if r.status_code != 0:
                raise RuntimeError(f"PowerShell error ({r.status_code}): {r.std_err.decode(errors='ignore')}")

            raw = r.std_out.decode(errors="ignore").strip()
            m = re.findall(r'\{.*}|\[.*]', raw, re.S)
            text = raw if not m else m[-1]
            return json.loads(text) if text else {}

        except socket.timeout:
            raise TimeoutError("Le serveur Hyper-V n'a pas répondu (Socket Timeout).")
        finally:
            # On restaure le timeout par défaut pour ne pas impacter le reste de l'application
            socket.setdefaulttimeout(default_timeout)

    def collect(self) -> Dict[str, Any]:
        ps = r'''
$ProgressPreference='SilentlyContinue'
$ErrorActionPreference='SilentlyContinue'
$hostName=(Get-ComputerInfo -Property CsName).CsName
$hostIP=(Get-NetIPAddress -AddressFamily IPv4|?{$_.IPAddress -notlike '169.*' -and $_.IPAddress -notlike '127.*'}|Select -First 1 -ExpandProperty IPAddress)
$cpu=Get-CimInstance Win32_Processor|Measure -Property LoadPercentage -Average
$cpuUsage=if($cpu.Average){[int]$cpu.Average}else{0}
$os=Get-CimInstance Win32_OperatingSystem
$freeMemMB=[int]($os.FreePhysicalMemory/1024)
$totalMemMB=[int]($os.TotalVisibleMemorySize/1024)
$fixed=Get-CimInstance Win32_LogicalDisk -Filter "DriveType=3"|Select DeviceID,FreeSpace,Size
$freeDiskGB=[math]::Round((($fixed|Measure -Property FreeSpace -Sum).Sum)/1GB,2)
$totalDiskGB=[math]::Round((($fixed|Measure -Property Size -Sum).Sum)/1GB,2)

$vms=Get-VM|%{
 $vm=$_
 $ip=$null
 try{$adp=$vm|Get-VMNetworkAdapter;$ip=$adp.IPAddresses|?{$_ -match '^\d{1,3}(\.\d{1,3}){3}$' -and $_ -notlike '169.*'}|Select -First 1}catch{}
 
 $kvpHash=@{}
 try{
  $kvpService=$vm|Get-VMIntegrationService|?{$_.Name -match 'Key-Value|change de paires'}
  if($kvpService -and $kvpService.Enabled){
   $vm|Get-VMKeyValuePair -Source Guest|%{ $kvpHash[$_.Name]=$_.Value }
  }
 }catch{}
 
 $rawHost=$kvpHash['HostName']
 $rawFqdn=$kvpHash['FullyQualifiedDomainName']
 $vmDns=if($kvpHash['NameServer']){$kvpHash['NameServer'] -split ','}else{@()}
 
 $vmHost=if($rawHost){$rawHost.Split('.')[0]}else{$vm.Name}
 $trueDomain=$null
 

 
 $vmFqdn=$null
 if($trueDomain -and $trueDomain -notmatch 'WORKGROUP|^\s*$'){
  $vmFqdn="$vmHost.$trueDomain"
 }elseif($rawFqdn -match '\.'){
  $vmFqdn=$rawFqdn
  $vmHost=$rawFqdn.Split('.')[0]
 }else{
  $vmFqdn=$vmHost
 }
 
 $vhdInfo=@()
 try{$vhdInfo=$vm|Get-VMHardDiskDrive|%{ $vhd=Get-VHD -Path $_.Path;[pscustomobject]@{Path=$vhd.Path;Size=[int64]$vhd.Size;FileSize=[int64]$vhd.FileSize}}}catch{}
 $totVhd=if($vhdInfo){[math]::Round((($vhdInfo|Measure -Property Size -Sum).Sum)/1GB,2)}else{$null}
 $totVhdFile=if($vhdInfo){[math]::Round((($vhdInfo|Measure -Property FileSize -Sum).Sum)/1GB,2)}else{$null}
 
 [pscustomobject]@{name=$vm.Name;state=$vm.State.ToString();vm_hostname=$vmHost;fqdn=$vmFqdn;dns_servers=$vmDns;ip=$ip;ram_mb=[int]($vm.MemoryStartup/1MB);total_vhd_gb=$totVhd;total_vhd_file_gb=$totVhdFile}
}
[pscustomobject]@{host_name=$hostName;host_ip=$hostIP;host_cpu_pct=$cpuUsage;host_free_mem_mb=$freeMemMB;host_total_mem_mb=$totalMemMB;host_free_disk_gb=$freeDiskGB;host_total_disk_gb=$totalDiskGB;vms=$vms}|ConvertTo-Json -Depth 6
'''
        return self._run_ps_json(ps)