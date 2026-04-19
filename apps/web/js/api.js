const API_BASE = '/api';

// ── Auth helpers ──────────────────────────────────────────────────────────────
function getToken() {
  return localStorage.getItem('truehire_token') || '';
}
function getUserId() {
  return localStorage.getItem('truehire_user_id') || '';
}
function getFullName() {
  return localStorage.getItem('truehire_full_name') || '';
}
function setUser(user_id, token, full_name) {
  localStorage.setItem('truehire_user_id', user_id);
  localStorage.setItem('truehire_token', token);
  localStorage.setItem('truehire_full_name', full_name || '');
}
function logout() {
  const token = getToken();
  if (token) fetch(API_BASE + '/auth/logout?token=' + token, {method: 'POST'}).catch(() => {});
  localStorage.removeItem('truehire_token');
  localStorage.removeItem('truehire_user_id');
  localStorage.removeItem('truehire_full_name');
  window.location.href = '/login.html';
}

// Redirect to login if not authenticated (call on every protected page)
function requireAuth() {
  if (!getToken() || !getUserId()) {
    window.location.href = '/login.html';
    return false;
  }
  return true;
}

// ── Fetch wrappers ────────────────────────────────────────────────────────────
function _authHeaders() {
  return {'Content-Type': 'application/json', 'X-Token': getToken()};
}

async function apiGet(path) {
  const token = getToken();
  const sep = path.includes('?') ? '&' : '?';
  const res = await fetch(API_BASE + path + sep + 'token=' + token);
  if (res.status === 401) { logout(); throw new Error('Session expired'); }
  if (!res.ok) throw new Error(`API error ${res.status}`);
  return res.json();
}

async function apiPost(path, body) {
  const res = await fetch(API_BASE + path, {
    method: 'POST',
    headers: _authHeaders(),
    body: JSON.stringify(body)
  });
  if (res.status === 401) { logout(); throw new Error('Session expired'); }
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `API error ${res.status}`);
  }
  return res.json();
}

async function apiPostForm(path, formData) {
  const token = getToken();
  const sep = path.includes('?') ? '&' : '?';
  const res = await fetch(API_BASE + path + sep + 'token=' + token, {method: 'POST', body: formData});
  if (res.status === 401) { logout(); throw new Error('Session expired'); }
  if (!res.ok) throw new Error(`API error ${res.status}`);
  return res.json();
}

// ── Populate nav user display ─────────────────────────────────────────────────
function populateNavUser() {
  const name = getFullName() || getUserId();
  const el = document.getElementById('nav-user-name');
  if (el) el.textContent = name;
  const initEl = document.getElementById('nav-user-initials');
  if (initEl) initEl.textContent = name ? name[0].toUpperCase() : '?';
  // Wire logout buttons
  document.querySelectorAll('[data-logout]').forEach(btn => {
    btn.addEventListener('click', logout);
  });
}
