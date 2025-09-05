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
  if (!s) return '';
  const d = new Date(s);
  return d.toLocaleString();
}

async function loadVMs() {
  const data = await fetchJSON('/api/vms');
  const tbody = document.getElementById('vms-body');
  tbody.innerHTML = '';
  data.forEach(vm => {
    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td>${vm.name}</td>
      <td>${vm.guest_hostname || ''}</td>
      <td>${vm.ip || ''}</td>
      <td>${vm.ram_mb ?? ''}</td>
      <td>${vm.total_vhd_gb ?? ''}</td>
      <td>${vm.total_vhd_file_gb ?? ''}</td>
      <td class="host-name" data-host-id="${vm.host_id}"></td>
      <td class="small">${fmtDate(vm.last_seen)}</td>
    `;
    tbody.appendChild(tr);
  });

  // Resolve host names for each VM row
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
  window._dt = new DataTable('#vms-table', { responsive: true, pageLength: 25 });
}

async function loadHosts() {
  const hosts = await fetchJSON('/api/hosts');
  const grid = document.getElementById('hosts-grid');
  grid.innerHTML = '';
  for (const h of hosts) {
    // Load host detail to fetch VMs
    const detail = await fetchJSON('/api/hosts/' + h.id);
    const card = document.createElement('div');
    card.className = 'host-card';
    card.innerHTML = `
      <h3>${h.name}</h3>
      <p class="small">IP: ${h.ip || ''} • RAM libre: ${h.free_mem_mb ?? ''} MB • Disque libre: ${h.free_disk_gb ?? ''} GB</p>
      <p class="small">Vu: ${fmtDate(h.last_seen)}</p>
      <div>${(detail.vms || []).map(vm => `<span class="vm-chip">${vm.name} (${vm.ip || '—'})</span>`).join('')}</div>
    `;
    grid.appendChild(card);
  }
}

async function refreshAll() {
  try {
    await fetch('/api/refresh', { method: 'POST' });
  } catch (e) { console.error(e); }
  await Promise.all([loadVMs(), loadHosts()]);
}

document.getElementById('refresh-btn').addEventListener('click', refreshAll);

// Initial load
window.addEventListener('load', async () => {
  await Promise.all([loadVMs(), loadHosts()]);
});
