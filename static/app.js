const tg = window.Telegram?.WebApp;
tg?.expand();
tg?.setHeaderColor('bg_color');

const API = '';
let initData = tg?.initData || '';
let currentUser = null;
let isAdmin = false;

// ── API helper ──────────────────────────────────────────────────────────────
async function api(method, path, body) {
  const opts = {
    method: method || 'GET',
    headers: { 'x-init-data': initData, 'Content-Type': 'application/json' },
  };
  if (body) opts.body = JSON.stringify(body);
  const res = await fetch(API + path, opts);
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

// ── State ───────────────────────────────────────────────────────────────────
let state = { tab: 'tournaments', subview: null, data: {} };

function navigate(tab, subview = null, data = {}) {
  state.tab = tab;
  state.subview = subview;
  state.data = data;
  render();
}

// ── App entry ────────────────────────────────────────────────────────────────
async function boot() {
  try {
    const me = await api('GET', '/api/me');
    currentUser = me.user;
    isAdmin = me.is_admin;
  } catch(e) {
    // dev fallback
    currentUser = { id: 0, first_name: 'Demo', username: null };
    isAdmin = false;
  }
  render();
}

// ── Render ───────────────────────────────────────────────────────────────────
function render() {
  const app = document.getElementById('app');
  app.innerHTML = '';

  const main = document.createElement('div');
  main.id = 'main-content';

  if (state.subview) {
    renderSubview(main);
  } else {
    renderTab(main);
  }

  app.appendChild(main);
  app.appendChild(renderTabBar());
}

function renderTabBar() {
  const tabs = [
    { id: 'tournaments', icon: iconTournament, label: 'Турниры' },
    { id: 'leaderboard', icon: iconLeaderboard, label: 'Лидерборд' },
    { id: 'profile', icon: iconProfile, label: 'Профиль' },
  ];
  if (isAdmin) tabs.push({ id: 'admin', icon: iconAdmin, label: 'Админ' });

  const bar = document.createElement('nav');
  bar.className = 'tab-bar';
  tabs.forEach(t => {
    const item = document.createElement('div');
    item.className = 'tab-item' + (state.tab === t.id && !state.subview ? ' active' : '');
    item.innerHTML = t.icon() + `<span>${t.label}</span>`;
    item.onclick = () => navigate(t.id);
    bar.appendChild(item);
  });
  return bar;
}

// ── Tab routing ──────────────────────────────────────────────────────────────
function renderTab(container) {
  switch (state.tab) {
    case 'tournaments': return renderTournaments(container);
    case 'leaderboard': return renderLeaderboard(container);
    case 'profile': return renderProfile(container);
    case 'admin': return renderAdmin(container);
  }
}

function renderSubview(container) {
  switch (state.subview) {
    case 'tournament-detail': return renderTournamentDetail(container, state.data);
    case 'admin-tournament': return renderAdminTournament(container, state.data);
    case 'admin-participants': return renderAdminParticipants(container, state.data);
    case 'admin-set-winner': return renderAdminSetWinner(container, state.data);
    case 'admin-create': return renderAdminCreate(container);
  }
}

// ── Tournaments tab ──────────────────────────────────────────────────────────
async function renderTournaments(container) {
  container.innerHTML = `<div class="page-header">🏆 Турниры</div>
    <div class="pills">
      <div class="pill active" id="pill-upcoming">Предстоящие</div>
      <div class="pill" id="pill-completed">Завершённые</div>
    </div>
    <div id="t-list" class="card-list"><div class="loader-wrap" style="height:200px"><div class="spinner"></div></div></div>`;

  container.querySelector('#pill-upcoming').onclick = () => loadUpcoming(container);
  container.querySelector('#pill-completed').onclick = () => loadCompleted(container);
  loadUpcoming(container);
}

async function loadUpcoming(container) {
  setPill(container, 'upcoming');
  const list = container.querySelector('#t-list');
  list.innerHTML = loader();
  try {
    const data = await api('GET', '/api/tournaments/upcoming');
    list.innerHTML = '';
    if (!data.length) {
      list.innerHTML = empty('📅', 'Нет предстоящих турниров');
      return;
    }
    data.forEach(t => {
      const card = document.createElement('div');
      card.className = 'card';
      const badge = t.registration_open
        ? `<span class="card-badge green">🔓 Регистрация</span>`
        : `<span class="card-badge gray">${t.status === 'active' ? '⚡ Идёт' : '📅 Скоро'}</span>`;
      card.innerHTML = `
        <div class="card-title">${esc(t.name)}</div>
        <div class="card-meta">
          ${t.date ? `<span>📅 ${esc(t.date)}</span>` : ''}
          <span>👥 ${t.participants_count}</span>
          ${badge}
        </div>
        <div class="card-winner">🥇 Победитель: <span>Неизвестно</span></div>`;
      card.onclick = () => navigate('tournaments', 'tournament-detail', t);
      list.appendChild(card);
    });
  } catch(e) { list.innerHTML = empty('❌', 'Ошибка загрузки'); }
}

async function loadCompleted(container) {
  setPill(container, 'completed');
  const list = container.querySelector('#t-list');
  list.innerHTML = loader();
  try {
    const data = await api('GET', '/api/tournaments/completed');
    list.innerHTML = '';
    if (!data.length) {
      list.innerHTML = empty('✅', 'Нет завершённых турниров');
      return;
    }
    data.forEach(t => {
      const card = document.createElement('div');
      card.className = 'card';
      const w = t.winners['1'];
      const winnerName = w ? esc(w.name) : '—';
      card.innerHTML = `
        <div class="card-title">${esc(t.name)}</div>
        <div class="card-meta">
          ${t.date ? `<span>📅 ${esc(t.date)}</span>` : ''}
          <span class="card-badge gray">✅ Завершён</span>
        </div>
        <div class="card-winner">🥇 Победитель: <span>${winnerName}</span></div>`;
      card.onclick = () => navigate('tournaments', 'tournament-detail', t);
      list.appendChild(card);
    });
  } catch(e) { list.innerHTML = empty('❌', 'Ошибка загрузки'); }
}

function setPill(container, active) {
  container.querySelector('#pill-upcoming').className = 'pill' + (active === 'upcoming' ? ' active' : '');
  container.querySelector('#pill-completed').className = 'pill' + (active === 'completed' ? ' active' : '');
}

// ── Tournament detail ────────────────────────────────────────────────────────
async function renderTournamentDetail(container, t) {
  const isCompleted = !!t.winners;
  container.innerHTML = `
    <div class="back-btn" id="back">◀ Назад</div>
    <div class="detail-view">
      <div class="detail-name">${esc(t.name)}</div>
      <div class="detail-meta">
        ${t.date ? `<span>📅 ${esc(t.date)}</span>` : ''}
        <span class="card-badge ${isCompleted ? 'gray' : t.registration_open ? 'green' : 'gray'}">
          ${isCompleted ? '✅ Завершён' : t.registration_open ? '🔓 Регистрация' : t.status === 'active' ? '⚡ Идёт' : '📅 Скоро'}
        </span>
      </div>
      <div id="detail-body"></div>
    </div>`;

  container.querySelector('#back').onclick = () => navigate(state.tab);

  const body = container.querySelector('#detail-body');

  if (isCompleted) {
    const places = [1, 2, 3];
    let rows = '';
    places.forEach(p => {
      const w = t.winners[p];
      const medal = ['🥇','🥈','🥉'][p-1];
      rows += `<div class="winner-row">
        <div class="winner-place">${medal}</div>
        <div class="winner-name">${w ? esc(w.name) : '<span style="color:var(--tg-hint)">—</span>'}</div>
      </div>`;
    });
    body.innerHTML = `<div class="detail-section">
      <div class="detail-section-title">Призёры</div>${rows}</div>`;
  } else {
    // Upcoming — show registration button
    const isReg = t.is_registered;
    body.innerHTML = `
      <div class="detail-section">
        <div class="detail-section-title">Участники</div>
        <p style="color:var(--tg-hint);font-size:14px;margin-bottom:16px">👥 ${t.participants_count} зарегистрировано</p>
        ${t.registration_open
          ? `<button class="btn ${isReg ? 'btn-danger' : 'btn-primary'}" id="reg-btn">
              ${isReg ? '❌ Отменить регистрацию' : '✅ Зарегистрироваться'}
            </button>`
          : `<button class="btn btn-secondary" disabled style="opacity:.5">Регистрация закрыта</button>`}
      </div>`;

    const regBtn = body.querySelector('#reg-btn');
    if (regBtn) regBtn.onclick = async () => {
      regBtn.disabled = true;
      try {
        if (isReg) {
          await api('POST', `/api/tournaments/${t.id}/unregister`);
          tg?.HapticFeedback?.notificationOccurred('success');
          t.is_registered = false;
          t.participants_count--;
        } else {
          await api('POST', `/api/tournaments/${t.id}/register`);
          tg?.HapticFeedback?.notificationOccurred('success');
          t.is_registered = true;
          t.participants_count++;
        }
        navigate('tournaments', 'tournament-detail', t);
      } catch(e) {
        tg?.HapticFeedback?.notificationOccurred('error');
        regBtn.disabled = false;
      }
    };
  }
}

// ── Leaderboard tab ──────────────────────────────────────────────────────────
async function renderLeaderboard(container) {
  container.innerHTML = `<div class="page-header">📊 Лидерборд</div><div class="lb-list" id="lb">${loader()}</div>`;
  try {
    const data = await api('GET', '/api/leaderboard');
    const lb = container.querySelector('#lb');
    lb.innerHTML = '';
    if (!data.length) { lb.innerHTML = empty('📊', 'Пока нет данных'); return; }
    data.forEach(row => {
      const rank = row.rank <= 3 ? ['🥇','🥈','🥉'][row.rank-1] : row.rank + '.';
      const medals = [
        row.wins ? `🥇×${row.wins}` : '',
        row.seconds ? `🥈×${row.seconds}` : '',
        row.thirds ? `🥉×${row.thirds}` : '',
      ].filter(Boolean).join('  ');
      const item = document.createElement('div');
      item.className = 'lb-item';
      item.innerHTML = `
        <div class="lb-rank">${rank}</div>
        <div class="lb-info">
          <div class="lb-name">${esc(row.name)}</div>
          ${medals ? `<div class="lb-medals">${medals}</div>` : ''}
        </div>
        <div class="lb-points">${row.points} <span class="lb-pts-label">очк.</span></div>`;
      lb.appendChild(item);
    });
  } catch(e) { container.querySelector('#lb').innerHTML = empty('❌', 'Ошибка загрузки'); }
}

// ── Profile tab ──────────────────────────────────────────────────────────────
async function renderProfile(container) {
  container.innerHTML = loader();
  try {
    const data = await api('GET', '/api/profile');
    const initial = (data.name || '?')[0].toUpperCase();
    const usernameStr = data.username ? `@${esc(data.username)}` : '';
    const wins = data.history.filter(h => h.place === 1).length;
    const top3 = data.history.filter(h => h.place <= 3).length;

    // Medals row
    const medals = data.history
      .filter(h => h.place <= 3)
      .map(h => {
        const emoji = ['🥇','🥈','🥉'][h.place-1];
        return `<div class="medal-chip"><span class="emoji">${emoji}</span><span class="label">${esc(h.tournament_name)}</span></div>`;
      }).join('');

    // History table rows
    const rows = data.history.map(h => {
      const emoji = h.place <= 3 ? ['🥇','🥈','🥉'][h.place-1] : `#${h.place}`;
      return `<tr><td>${esc(h.tournament_name)}</td><td>${emoji}</td></tr>`;
    }).join('');

    container.innerHTML = `
      <div class="profile-header">
        <div class="profile-avatar">${initial}</div>
        <div>
          <div class="profile-name">${esc(data.name)}</div>
          ${usernameStr ? `<div class="profile-username">${usernameStr}</div>` : ''}
        </div>
      </div>
      <div class="profile-points-row">
        <div class="profile-stat"><div class="profile-stat-value">${data.total_points}</div><div class="profile-stat-label">очков</div></div>
        <div class="profile-stat"><div class="profile-stat-value">${wins}</div><div class="profile-stat-label">побед</div></div>
        <div class="profile-stat"><div class="profile-stat-value">${top3}</div><div class="profile-stat-label">призовых</div></div>
      </div>
      ${medals ? `
        <div class="section-header">Медали</div>
        <div class="medals-scroll">${medals}</div>
      ` : ''}
      ${rows ? `
        <div class="section-header">История матчей</div>
        <table class="history-table">
          <thead><tr><th>Турнир</th><th>Место</th></tr></thead>
          <tbody>${rows}</tbody>
        </table>
      ` : `<div style="padding:16px">${empty('🃏','Матчей пока нет')}</div>`}`;
  } catch(e) {
    container.innerHTML = empty('❌', 'Ошибка загрузки');
  }
}

// ── Admin tab ────────────────────────────────────────────────────────────────
async function renderAdmin(container) {
  container.innerHTML = `<div class="page-header">⚙️ Администратор</div>
    <div class="card-list" id="admin-list">${loader()}</div>`;

  const fab = document.createElement('div');
  fab.style.cssText = 'position:fixed;bottom:90px;right:16px;z-index:99';
  fab.innerHTML = `<button class="btn btn-primary btn-sm" id="create-btn" style="width:auto;padding:12px 20px">➕ Создать турнир</button>`;
  container.appendChild(fab);
  fab.querySelector('#create-btn').onclick = () => navigate('admin', 'admin-create');

  await loadAdminTournaments(container);
}

async function loadAdminTournaments(container) {
  const list = container.querySelector('#admin-list');
  if (!list) return;
  list.innerHTML = loader();
  try {
    const data = await api('GET', '/api/admin/tournaments');
    list.innerHTML = '';
    if (!data.length) { list.innerHTML = empty('📋', 'Турниров нет'); return; }
    data.forEach(t => {
      const card = document.createElement('div');
      card.className = 'card';
      const statusLabel = { upcoming: '📅 Ожидание', active: '⚡ Идёт', completed: '✅ Завершён' }[t.status];
      const w1 = t.winners?.['1'];
      card.innerHTML = `
        <div class="card-title">${esc(t.name)}</div>
        <div class="card-meta">
          ${t.date ? `<span>📅 ${esc(t.date)}</span>` : ''}
          <span class="card-badge gray">${statusLabel}</span>
          ${t.registration_open ? `<span class="card-badge green">🔓</span>` : ''}
          <span>👥 ${t.participants_count}</span>
        </div>
        ${w1 ? `<div class="card-winner">🥇 ${esc(w1.name)}</div>` : ''}`;
      card.onclick = () => navigate('admin', 'admin-tournament', t);
      list.appendChild(card);
    });
  } catch(e) { if (list) list.innerHTML = empty('❌', 'Ошибка'); }
}

// ── Admin: tournament detail ─────────────────────────────────────────────────
async function renderAdminTournament(container, t) {
  const isCompleted = t.status === 'completed';
  const winners = t.winners || {};

  container.innerHTML = `
    <div class="back-btn" id="back">◀ Назад</div>
    <div class="detail-view">
      <div class="detail-name">${esc(t.name)}</div>
      <div class="detail-meta">
        ${t.date ? `<span>📅 ${esc(t.date)}</span>` : ''}
        <span class="card-badge gray">${{upcoming:'📅 Ожидание',active:'⚡ Идёт',completed:'✅ Завершён'}[t.status]}</span>
      </div>

      ${[1,2,3].map(p => {
        const w = winners[p] || winners[String(p)];
        const medal = ['🥇','🥈','🥉'][p-1];
        return `<div class="winner-row">
          <div class="winner-place">${medal}</div>
          <div class="winner-name">${w ? esc(w.name) : '<span style="color:var(--tg-hint)">—</span>'}</div>
          <div style="margin-left:auto;cursor:pointer;color:var(--tg-button)" data-set-winner="${p}">Назначить</div>
        </div>`;
      }).join('')}

      <div class="admin-actions" style="margin-top:16px">
        ${!isCompleted ? `
          <div class="toggle-row">
            <span class="toggle-label">Регистрация</span>
            <div class="toggle ${t.registration_open ? 'on' : ''}" id="reg-toggle"></div>
          </div>
          ${t.status === 'upcoming' ? `<button class="btn btn-primary" id="start-btn">▶️ Начать турнир</button>` : ''}
          ${t.status === 'active' ? `<button class="btn btn-secondary" id="finish-btn">🏁 Завершить турнир</button>` : ''}
        ` : ''}
        <button class="btn btn-secondary" id="participants-btn">👥 Участники (${t.participants_count})</button>
        <button class="btn btn-danger" id="delete-btn">🗑 Удалить турнир</button>
      </div>
    </div>`;

  container.querySelector('#back').onclick = () => navigate('admin');

  // Set winner buttons
  container.querySelectorAll('[data-set-winner]').forEach(el => {
    el.onclick = () => navigate('admin', 'admin-set-winner', { tournament: t, place: +el.dataset.setWinner });
  });

  const regToggle = container.querySelector('#reg-toggle');
  if (regToggle) regToggle.onclick = async () => {
    const newVal = !t.registration_open;
    await api('PATCH', `/api/admin/tournaments/${t.id}`, { registration_open: newVal });
    t.registration_open = newVal;
    regToggle.classList.toggle('on', newVal);
    tg?.HapticFeedback?.selectionChanged();
  };

  const startBtn = container.querySelector('#start-btn');
  if (startBtn) startBtn.onclick = async () => {
    await api('PATCH', `/api/admin/tournaments/${t.id}`, { status: 'active', registration_open: false });
    t.status = 'active'; t.registration_open = false;
    tg?.HapticFeedback?.notificationOccurred('success');
    navigate('admin', 'admin-tournament', t);
  };

  const finishBtn = container.querySelector('#finish-btn');
  if (finishBtn) finishBtn.onclick = async () => {
    await api('PATCH', `/api/admin/tournaments/${t.id}`, { status: 'completed' });
    t.status = 'completed';
    tg?.HapticFeedback?.notificationOccurred('success');
    navigate('admin', 'admin-tournament', t);
  };

  container.querySelector('#participants-btn').onclick = () =>
    navigate('admin', 'admin-participants', { tournament: t });

  container.querySelector('#delete-btn').onclick = async () => {
    if (!confirm(`Удалить турнир "${t.name}"?`)) return;
    await api('DELETE', `/api/admin/tournaments/${t.id}`);
    tg?.HapticFeedback?.notificationOccurred('warning');
    navigate('admin');
  };
}

// ── Admin: set winner ────────────────────────────────────────────────────────
async function renderAdminSetWinner(container, { tournament, place }) {
  const medal = ['🥇','🥈','🥉'][place-1];
  container.innerHTML = `
    <div class="back-btn" id="back">◀ Назад</div>
    <div class="page-header">${medal} ${place} место</div>
    <div class="card-list" id="user-list">${loader()}</div>`;
  container.querySelector('#back').onclick = () => navigate('admin', 'admin-tournament', tournament);

  const list = container.querySelector('#user-list');
  try {
    const participants = await api('GET', `/api/admin/tournaments/${tournament.id}/participants`);
    const active = participants.filter(p => !p.excluded);
    if (!active.length) { list.innerHTML = empty('👥', 'Нет участников'); return; }
    active.forEach(p => {
      const card = document.createElement('div');
      card.className = 'card';
      card.innerHTML = `<div class="card-title">${esc(p.name)}</div>${p.username ? `<div class="card-meta">@${esc(p.username)}</div>` : ''}`;
      card.onclick = async () => {
        await api('POST', `/api/admin/tournaments/${tournament.id}/winners`, { user_id: p.user_id, place });
        if (!tournament.winners) tournament.winners = {};
        tournament.winners[place] = { name: p.name };
        tournament.winners[String(place)] = { name: p.name };
        tg?.HapticFeedback?.notificationOccurred('success');
        navigate('admin', 'admin-tournament', tournament);
      };
      list.appendChild(card);
    });
  } catch(e) { list.innerHTML = empty('❌', 'Ошибка'); }
}

// ── Admin: participants ──────────────────────────────────────────────────────
async function renderAdminParticipants(container, { tournament }) {
  container.innerHTML = `
    <div class="back-btn" id="back">◀ Назад</div>
    <div class="page-header">👥 Участники</div>
    <div class="card-list" id="p-list">${loader()}</div>`;
  container.querySelector('#back').onclick = () => navigate('admin', 'admin-tournament', tournament);

  const list = container.querySelector('#p-list');
  try {
    const participants = await api('GET', `/api/admin/tournaments/${tournament.id}/participants`);
    if (!participants.length) { list.innerHTML = empty('👥', 'Нет участников'); return; }
    participants.forEach(p => {
      const item = document.createElement('div');
      item.className = 'participant-item';
      item.innerHTML = `
        <div class="participant-name ${p.excluded ? 'excluded' : ''}">${esc(p.name)}${p.username ? ` <span style="color:var(--tg-hint)">@${esc(p.username)}</span>` : ''}</div>
        <div class="participant-toggle">${p.excluded ? '🚫' : '✅'}</div>`;
      item.querySelector('.participant-toggle').onclick = async () => {
        if (p.excluded) {
          await api('POST', `/api/admin/tournaments/${tournament.id}/participants/${p.user_id}/include`);
          p.excluded = false;
        } else {
          await api('POST', `/api/admin/tournaments/${tournament.id}/participants/${p.user_id}/exclude`);
          p.excluded = true;
        }
        tg?.HapticFeedback?.selectionChanged();
        navigate('admin', 'admin-participants', { tournament });
      };
      list.appendChild(item);
    });
  } catch(e) { list.innerHTML = empty('❌', 'Ошибка'); }
}

// ── Admin: create tournament ─────────────────────────────────────────────────
function renderAdminCreate(container) {
  container.innerHTML = `
    <div class="back-btn" id="back">◀ Назад</div>
    <div class="page-header">➕ Новый турнир</div>
    <div style="padding:0 16px">
      <div class="input-group">
        <label class="input-label">Название *</label>
        <input class="input-field" id="t-name" placeholder="Турнир #1" />
      </div>
      <div class="input-group">
        <label class="input-label">Дата (необязательно)</label>
        <input class="input-field" id="t-date" placeholder="25.12.2024" />
      </div>
      <button class="btn btn-primary" id="create-submit" style="margin-top:8px">Создать</button>
    </div>`;

  container.querySelector('#back').onclick = () => navigate('admin');
  container.querySelector('#create-submit').onclick = async () => {
    const name = container.querySelector('#t-name').value.trim();
    const date = container.querySelector('#t-date').value.trim();
    if (!name) { container.querySelector('#t-name').focus(); return; }
    try {
      await api('POST', '/api/admin/tournaments', { name, date: date || null });
      tg?.HapticFeedback?.notificationOccurred('success');
      navigate('admin');
    } catch(e) {
      tg?.HapticFeedback?.notificationOccurred('error');
    }
  };
}

// ── Utils ────────────────────────────────────────────────────────────────────
function esc(str) {
  if (!str) return '';
  return String(str).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}
function loader() {
  return `<div class="loader-wrap" style="height:200px"><div class="spinner"></div></div>`;
}
function empty(icon, text) {
  return `<div class="empty"><div class="empty-icon">${icon}</div><div>${text}</div></div>`;
}

// ── Icons ────────────────────────────────────────────────────────────────────
function iconTournament() {
  return `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
    <path d="M6 9H4.5a2.5 2.5 0 010-5H6"/><path d="M18 9h1.5a2.5 2.5 0 000-5H18"/>
    <path d="M4 22h16"/><path d="M10 14.66V17c0 .55-.47.98-.97 1.21C7.85 18.75 7 20.24 7 22"/>
    <path d="M14 14.66V17c0 .55.47.98.97 1.21C16.15 18.75 17 20.24 17 22"/>
    <path d="M18 2H6v7a6 6 0 0012 0V2z"/>
  </svg>`;
}
function iconLeaderboard() {
  return `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
    <line x1="18" y1="20" x2="18" y2="10"/><line x1="12" y1="20" x2="12" y2="4"/>
    <line x1="6" y1="20" x2="6" y2="14"/>
  </svg>`;
}
function iconProfile() {
  return `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
    <path d="M20 21v-2a4 4 0 00-4-4H8a4 4 0 00-4 4v2"/>
    <circle cx="12" cy="7" r="4"/>
  </svg>`;
}
function iconAdmin() {
  return `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
    <circle cx="12" cy="12" r="3"/>
    <path d="M19.07 4.93a10 10 0 010 14.14M4.93 4.93a10 10 0 000 14.14"/>
    <path d="M12 2v2M12 20v2M2 12h2M20 12h2"/>
  </svg>`;
}

// ── Start ────────────────────────────────────────────────────────────────────
boot();
