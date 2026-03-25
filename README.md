# 🖥️ Hypervisor Monitor (Multi-Provider)

Projet Python moderne et modulaire pour centraliser la supervision de vos infrastructures de virtualisation. Il supporte nativement **Hyper-V**, **Proxmox** et **ESXi**.

## ✨ Fonctionnalités

* **Multi-Hyperviseur** : Collecte unifiée pour Hyper-V (WinRM), Proxmox (API Rest) et ESXi (pyVmomi).

* **Dashboard Hybride** :

* **Vue Hosts** (Style Beszel) : Cartes d'état avec consommation CPU/RAM/Disque en temps réel.

* **Vue VMs** (Style Dozzle) : Tableau global filtrable et triable pour toutes vos machines virtuelles.

* **Système de Tags** : Catégorisation visuelle des hôtes avec couleurs personnalisables.

* **Recherche Intelligente** : Filtrage instantané par nom, IP ou hôte sur l'ensemble de l'infra.

* **Persistance** : Historisation des états via SQLite (SQLAlchemy 2.0).

---

## 🚀 Démarrage Rapide

```bash
# 1. Préparer l'environnement
cp .env.example .env

# 2. Configurer vos hôtes dans le .env (voir section Configuration)

# 3. Lancer avec Docker
docker compose up --build -d
```

Accès à l'interface : **[http://localhost:27888](http://localhost:27888)**

---

## ⚙️ Configuration (.env)

La configuration est désormais basée sur des objets JSON pour permettre une flexibilité totale par hôte.

### Variables Globales

* `POLL_MINUTES` : Fréquence de scan (ex: `10`).
* `DB_PATH` : Chemin de la base SQLite (défaut: `data/app.db`).
* `WINRM_USERNAME/PASSWORD` : Identifiants Hyper-V par défaut.

### `HOSTS_CONFIG` (JSON)

Définit la liste des serveurs à monitorer. Vous pouvez surcharger les identifiants pour chaque hôte.

```json
[
  {
    "ip": "192.168.1.10",
    "type": "hyperv",
    "tags": ["Prod", "Windows"]
  },
  {
    "ip": "192.168.1.20", 
    "type": "proxmox",
    "username": "root@pam",
    "password": "PasswordSpecifique",
    "tags": ["Dev", "PVE"]
  }
]
```

* Pour créer un utilisateur et un token Proxmox (méthode recommandée)

  ```bash
  # Créer un utilisateur dédié au monitoring
  pveum user add monitor@pve

  # Lui attribuer un rôle en lecture seule sur toute l'infra
  pveum aclmod / -user monitor@pve -role PVEAuditor

  # Créer un token API (sans séparation de privilèges pour simplifier)
  pveum user token add monitor@pve api-token --privsep 0
  ```

  👉 Vous obtiendrez un identifiant de type :

  ```
  monitor@pve!api-token
  ```

  ainsi qu’un **secret** à utiliser comme mot de passe dans votre configuration.

* Pour récupérer les adresses IP des VMs Proxmox

  * Installer et activer le **QEMU Guest Agent** dans chaque VM :

    * Sur Debian/Ubuntu :

    ```bash
    apt install qemu-guest-agent -y
    systemctl enable --now qemu-guest-agent
    ```

    * Sur Windows :
      Installer le package *QEMU Guest Agent* depuis l’ISO VirtIO.

  * Vérifier côté Proxmox que l’option est activée :

    ```
    VM → Options → QEMU Guest Agent → Enabled
    ```

  👉 Sans cet agent, aucune IP ne pourra être remontée via l’API.

### `TAG_COLORS` (JSON)

Personnalisation des badges dans l'interface.

```json
{
  "Prod": {"bg": "#D91A1A", "text": "#FFFFFF"},
  "Dev": {"bg": "#30E6F2", "text": "#000000"}
}
```

---

## 🛠️ Pré-requis par Type

### Hyper-V (Windows)

* WinRM activé : `winrm quickconfig`.
* Authentification **CredSSP** recommandée pour le passage de credentials.
* Intégration Services activés sur les VMs pour la remontée d'IP.

### Proxmox

* L'utilisateur doit avoir les droits `PVEAuditor` ou `PVEDatastoreAdmin`.
* Le **QEMU Guest Agent** doit être installé sur les VMs pour récupérer les adresses IP.

### ESXi (VMware)

* Accès utilisateur (lecture seule autorisée).
* **VMware Tools** installés sur les VMs pour la remontée des informations Guest.

---

## 📡 Endpoints API

* `GET /api/hosts` : Liste des hyperviseurs et métriques.
* `GET /api/vms` : Liste de toutes les VMs.
* `POST /api/refresh` : Déclenche un scan immédiat de toute l'infra.
* `GET /api/config/tags` : Récupère la configuration des couleurs.
* `DELETE /api/hosts/{id}` : Supprime un hôte et ses VMs de la base.

---

## 📦 Développement (Local)

1. **Installation des dépendances** :

```bash
pip install -r requirements.txt
```

2. **Lancement du serveur** :

```bash
uvicorn app.main:app --host 0.0.0.0 --port 27888 --reload
```

**Requirements clés :**

* `fastapi`, `uvicorn` (Web)
* `sqlalchemy` (Database)
* `pywinrm[credssp]` (Hyper-V)
* `proxmoxer` (Proxmox)
* `pyvmomi` (ESXi)

---

## ⚠️ Limitations

* **Stockage** : La taille disque affichée pour les VMs correspond à l'occupation sur l'hôte (fichiers VHD/RAW/VMDK), et non à l'espace libre à l'intérieur de la partition de l'OS invité.
* **Réseau** : Les IPs ne sont remontées que si les "Guest Tools" sont actifs et que la VM est démarrée.
