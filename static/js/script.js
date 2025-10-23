// Toasts from Flask flashes
(function initToasts() {
  const flash = document.getElementById('flash-messages');
  if (!flash) return;
  const msgs = JSON.parse(flash.getAttribute('data-messages') || '[]');
  const container = document.getElementById('toast-container');
  if (!container) return;
  msgs.forEach((m) => {
    const el = document.createElement('div');
    el.className = 'toast align-items-center text-bg-primary border-0 show';
    el.setAttribute('role', 'alert');
    el.innerHTML = `<div class="d-flex"><div class="toast-body">${m}</div><button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button></div>`;
    container.appendChild(el);
  });
})();

// Flatpickr for all date inputs
(function initDates() {
  if (typeof flatpickr === 'undefined') return;
  flatpickr('.datepicker', { dateFormat: 'Y-m-d', allowInput: true });
})();

// Charts
(function initCharts() {
  if (typeof Chart === 'undefined' || !window.SHELFLIFE) return;
  const { expiringCounts, consumptionSeries } = window.SHELFLIFE;
  if (expiringCounts) {
    const labels = Object.keys(expiringCounts);
    const data = Object.values(expiringCounts);
    new Chart(document.getElementById('expiringChart'), {
      type: 'doughnut',
      data: { labels, datasets: [{ data, backgroundColor: ['#dc3545','#ffc107','#28a745','#6c757d'] }]},
      options: { plugins: { legend: { position: 'bottom' }, title: { display: false } } }
    });
  }
  if (consumptionSeries) {
    new Chart(document.getElementById('consumptionChart'), {
      type: 'bar',
      data: { labels: consumptionSeries.map(x => x.name), datasets: [{ label: 'units/day', data: consumptionSeries.map(x => x.cpd), backgroundColor: '#0d6efd' }]},
      options: { plugins: { legend: { display: true } }, scales: { y: { beginAtZero: true } } }
    });
  }
})();

// Table search/sort/pagination
(function tableUX() {
  const table = document.getElementById('items-table');
  if (!table) return;
  const tbody = table.querySelector('tbody');
  const rows = Array.from(tbody.querySelectorAll('tr'));
  const search = document.getElementById('table-search');
  const pagerInfo = document.getElementById('pager-info');
  const prevBtn = document.getElementById('prev-page');
  const nextBtn = document.getElementById('next-page');
  // Show all rows by default; search will still filter dynamically
  let PAGE_SIZE = rows.length || 10;
  let current = 1;
  let filtered = rows.slice();

  function rowText(r) {
    let text = r.textContent || '';
    // Also include input values so editable fields are searchable
    r.querySelectorAll('input, select').forEach(el => {
      const v = (el.value || '').toString();
      if (v) text += ' ' + v;
    });
    return text.toLowerCase();
  }

  function applySearch() {
    const q = (search?.value || '').toLowerCase();
    filtered = rows.filter(r => rowText(r).includes(q));
    current = 1;
    render();
  }

  function sortByIdx(idx, type, asc) {
    const getVal = (r) => r.children[idx]?.textContent.trim() || '';
    const parseNum = (s) => parseFloat((s.match(/[\-\d\.]+/)||['0'])[0]) || 0;
    const parseDate = (s) => Date.parse(s) || 0;
    filtered.sort((a,b)=>{
      let va = getVal(a), vb = getVal(b), cmp=0;
      if (type==='num') cmp = parseNum(va) - parseNum(vb);
      else if (type==='date') cmp = parseDate(va) - parseDate(vb);
      else cmp = va.localeCompare(vb);
      return asc? cmp : -cmp;
    });
    current = 1; render();
  }

  function render() {
    rows.forEach(r => r.style.display='none');
    const total = filtered.length;
    const pages = Math.max(1, Math.ceil(total / PAGE_SIZE));
    if (current > pages) current = pages;
    const start = (current - 1) * PAGE_SIZE;
    const pageRows = filtered.slice(start, start + PAGE_SIZE);
    pageRows.forEach(r => r.style.display='');
    if (pagerInfo) pagerInfo.textContent = `Showing ${pageRows.length} of ${total}`;
    if (prevBtn) prevBtn.disabled = current<=1;
    if (nextBtn) nextBtn.disabled = current>=pages;
  }

  // Sort handlers
  Array.from(table.querySelectorAll('thead th')).forEach((th, idx) => {
    const type = th.getAttribute('data-sort');
    if (!type) return;
    let asc = true;
    th.style.cursor = 'pointer';
    th.addEventListener('click', () => { asc = !asc; sortByIdx(idx, type, asc); });
  });

  search?.addEventListener('input', applySearch);
  prevBtn?.addEventListener('click', (e)=>{ e.preventDefault(); if (current>1){ current--; render(); }});
  nextBtn?.addEventListener('click', (e)=>{ e.preventDefault(); current++; render(); });

  // Initial render
  applySearch();
})();

// Smooth scroll for notification links
(function smoothNotifLinks(){
  const links = document.querySelectorAll('a.notif-link[href^="#item-"]');
  if (!links.length) return;
  links.forEach(a => {
    a.addEventListener('click', (e) => {
      const href = a.getAttribute('href') || '';
      if (!href.startsWith('#')) return;
      const target = document.querySelector(href);
      if (!target) return;
      e.preventDefault();
      // Close any open Bootstrap dropdown
      try {
        const menu = a.closest('.dropdown-menu');
        if (menu) {
          const btn = document.getElementById('notif-bell');
          btn?.click();
        }
      } catch (_) {}
      target.scrollIntoView({ behavior: 'smooth', block: 'center' });
      // brief highlight
      target.classList.add('table-active');
      setTimeout(()=> target.classList.remove('table-active'), 1200);
    });
  });
})();
