# Hyper-V Monitor (Docker + FastAPI)

Projet Python modulaire et dockerisé qui :
- Lit une liste d'hôtes Hyper‑V depuis des variables d’environnement
- Sonde chaque hôte à une fréquence (en minutes) configurable via variable d’environnement
- Récupère et persiste :
  - IP de l’hôte
  - Espace disque restant (somme des volumes) sur l’hôte
  - RAM disponible sur l’hôte
  - Et pour chaque VM :
    - IP
    - hostname (si disponible via intégrations)
    - nom
    - configuration RAM (MB)
    - informations disque (taille VHD et taille de fichier)
- Expose une API (FastAPI) pour récupérer les informations
- Sert une petite page Web à deux onglets :
  - Onglet 1 : tableau triable/filtrable des VMs (+ host rattaché)
  - Onglet 2 : vue par host avec ses VMs

## TL;DR

```bash
cp env.example .env
# Éditez .env pour configurer vos hôtes et identifiants WinRM
docker compose up --build
```

Puis ouvrez http://localhost:8000

## Variables d’environnement

- `HOSTS`: liste d’hôtes à sonder, séparés par des virgules (ex: `hyperv1,hyperv2.contoso.local,10.0.0.12`)
- `POLL_MINUTES`: fréquence de rafraîchissement en minutes (ex: `5`)
- `WINRM_USERNAME`: compte (domaine\utilisateur ou utilisateur@domaine)
- `WINRM_PASSWORD`: mot de passe
- `WINRM_USE_SSL`: `true` ou `false` (par défaut `false`)
- `WINRM_PORT`: `5985` (HTTP) ou `5986` (HTTPS)
- `WINRM_VERIFY_SSL`: `true` ou `false` (par défaut `false`) — utile si vous avez un cert valide

> Notes Hyper‑V/WinRM
> - Assurez-vous que WinRM est activé sur les hôtes Hyper‑V (`winrm quickconfig`).
> - Pour récupérer IPs des VMs, l’Intégration Services doit exposer les adresses (VMs démarrées).
> - Le « hostname » invité peut ne pas être disponible selon vos intégrations; le champ peut être `null`.

## Endpoints principaux

- `GET /api/hosts`
- `GET /api/hosts/{host_id}`
- `GET /api/vms`
- `GET /api/vms/{vm_id}`
- `POST /api/refresh` — déclenche une collecte immédiate

Page UI : `GET /`

## Persistance

SQLite (`app.db`) via SQLAlchemy. Montez un volume pour la conserver :
```yaml
volumes:
  - ./data:/app/data
```

## Développement

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

## Sécurité

- Les identifiants WinRM sont fournis par variables d’environnement (ne pas commiter votre `.env`).
- Pour WinRM via HTTPS (`WINRM_USE_SSL=true`), configurez un certificat côté hôte.

## Limitations connues

- « Espace disque » d’une VM = taille(s) des VHD et taille(s) de fichier côté hôte. Le libre **à l’intérieur** de l’OS invité n’est pas collecté par défaut.
- Le « hostname » invité peut être indisponible selon les services d’intégration et l’OS invité.


## Tester une connexion winrm

```
pip install pywinrm[credssp]
```

```
import winrm

s = winrm.Session("http://192.168.xx.yy:5985/wsman", auth=("HOSTNAME\\Administrateur", "xxxx"))
r = s.run_cmd("hostname")
print(r.std_out)
```