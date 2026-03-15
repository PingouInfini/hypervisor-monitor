function switchTab(targetId) {
  document.querySelectorAll('.pane').forEach(p => p.classList.remove('active'));
  document.querySelectorAll('a.tab').forEach(t => t.classList.remove('active'));
  document.getElementById(targetId).classList.add('active');
  document.querySelectorAll('a.tab').forEach(t => {
    if (t.dataset.target === targetId) t.classList.add('active');
  });
}

document.addEventListener('click', (e) => {
  const t = e.target;
  if (t.matches('a.tab')) {
    e.preventDefault();
    switchTab(t.dataset.target);
  }
});

async function fetchJSON(url) {
  const res = await fetch(url);
  if (!res.ok) throw new Error('HTTP ' + res.status);
  return await res.json();
}

function fmtDate(s) {
  if (!s) return 'Jamais';
  const d = new Date(s);
  return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) + ' - ' + d.toLocaleDateString();
}

async function loadVMs() {
  const data = await fetchJSON('/api/vms');
  const tbody = document.getElementById('vms-body');
  tbody.innerHTML = '';
  data.forEach(vm => {
    const isUp = !!vm.ip;
    const statusHtml = `<span class="status-dot ${isUp ? 'up' : 'down'}" title="${isUp ? 'UP' : 'DOWN'}"></span>`;

    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td>${statusHtml} &nbsp; ${vm.name}</td>
      <td>${vm.guest_hostname || '<span class="text-muted">—</span>'}</td>
      <td style="font-family: monospace;">${vm.ip || '<span class="text-muted">—</span>'}</td>
      <td>${vm.ram_mb ? vm.ram_mb + ' MB' : '—'}</td>
      <td>${vm.total_vhd_gb ? vm.total_vhd_gb + ' GB' : '—'}</td>
      <td>${vm.total_vhd_file_gb ? vm.total_vhd_file_gb + ' GB' : '—'}</td>
      <td class="host-name" data-host-id="${vm.host_id}"></td>
      <td style="font-size: 0.85rem; color: #94a3b8;">${fmtDate(vm.last_seen)}</td>
    `;
    tbody.appendChild(tr);
  });

  // Résolution des noms d'hôtes pour le tableau
  const hosts = await fetchJSON('/api/hosts');
  const hostMap = {};
  hosts.forEach(h => hostMap[h.id] = h.name);
  document.querySelectorAll('#vms-body .host-name').forEach(td => {
    const hid = parseInt(td.dataset.hostId, 10);
    td.textContent = hostMap[hid] || hid;
  });

  // Init/refresh DataTable
  if (window._dt) {
    window._dt.destroy();
  }
  window._dt = new DataTable('#vms-table', {
    responsive: true,
    pageLength: 25,
    language: { search: "Rechercher :", lengthMenu: "Afficher _MENU_ VMs" }
  });
}

async function loadHosts() {
  const hosts = await fetchJSON('/api/hosts');
  const grid = document.getElementById('hosts-grid');
  grid.innerHTML = '';

  for (const h of hosts) {
    const detail = await fetchJSON('/api/hosts/' + h.id);
    const vms = detail.vms || [];

    // Trier les VMs : Les allumées (avec IP) d'abord
    vms.sort((a, b) => (b.ip ? 1 : 0) - (a.ip ? 1 : 0));

    const vmsHtml = vms.map(vm => {
      const isUp = !!vm.ip;
      return `
        <div class="vm-row">
          <div class="vm-info">
            <span class="status-dot ${isUp ? 'up' : 'down'}"></span>
            <span class="vm-name">${vm.name}</span>
          </div>
          <span class="vm-ip">${vm.ip || 'Hors ligne'}</span>
        </div>
      `;
    }).join('');

    const card = document.createElement('div');
    card.className = 'host-card';
    card.innerHTML = `
      <div class="host-header">
        <div>
          <h3>🖥️ ${h.name}</h3>
          <div class="host-meta">${h.ip || 'IP Inconnue'}</div>
        </div>
        <div class="host-meta" style="text-align: right;">
          <div>Vu à</div>
          <div>${fmtDate(h.last_seen)}</div>
        </div>
      </div>

      <div class="host-stats">
        <div class="stat-box">
          <span class="stat-label">RAM Libre</span>
          <span class="stat-value">${h.free_mem_mb ? h.free_mem_mb + ' MB' : 'N/A'}</span>
        </div>
        <div class="stat-box">
          <span class="stat-label">Stockage Libre</span>
          <span class="stat-value">${h.free_disk_gb ? h.free_disk_gb + ' GB' : 'N/A'}</span>
        </div>
      </div>

      <div class="vm-list">
        <div style="font-size: 0.85rem; color: #94a3b8; margin-bottom: 4px; padding-left: 4px;">Machines Virtuelles (${vms.length})</div>
        ${vmsHtml || '<div class="vm-row" style="justify-content: center; color: #94a3b8;">Aucune VM détectée</div>'}
      </div>
    `;
    grid.appendChild(card);
  }
}

async function refreshAll() {
  const btn = document.getElementById('refresh-btn');
  btn.setAttribute('aria-busy', 'true');
  btn.textContent = 'Actualisation...';

  try {
    await fetch('/api/refresh', { method: 'POST' });
  } catch (e) {
    console.error(e);
  }

  await Promise.all([loadVMs(), loadHosts()]);

  btn.removeAttribute('aria-busy');
  btn.textContent = '↻ Actualiser';
}

document.getElementById('refresh-btn').addEventListener('click', refreshAll);

// Initial load
window.addEventListener('load', async () => {
  await Promise.all([loadVMs(), loadHosts()]);
});