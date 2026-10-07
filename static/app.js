const API = '/api/v1';
const PAGE_SIZE = 20;
let token = null;
let taskPage = { offset: 0, total: 0, items: [] };
let filters = { search: '', status: '', priority: '' };

const $ = (selector) => document.querySelector(selector);
const views = ['auth-view', 'dashboard-view', 'task-view', 'task-form-view'];

function showOnly(id) {
  views.forEach((view) => { $(`#${view}`).hidden = view !== id; });
  $('#main-content').focus();
}
function message(text, type = 'success') {
  const region = $('#message-region');
  region.replaceChildren();
  if (!text) return;
  const notice = document.createElement('div');
  notice.className = `notice notice-${type}`;
  notice.setAttribute('role', type === 'error' ? 'alert' : 'status');
  notice.textContent = text;
  region.append(notice);
}
function setAuthNavigation() {
  document.querySelectorAll('[data-auth-only]').forEach((node) => { node.hidden = !token; });
}
function errorText(payload, fallback) {
  if (!payload) return fallback;
  if (typeof payload.message === 'string') return payload.message;
  if (Array.isArray(payload.detail)) return payload.detail.map((item) => item.msg || String(item)).join(' ');
  if (typeof payload.detail === 'string') return payload.detail;
  return fallback;
}
async function request(path, options = {}) {
  const headers = new Headers(options.headers || {});
  if (token) headers.set('Authorization', `Bearer ${token}`);
  if (options.body) headers.set('Content-Type', 'application/json');
  let response;
  try { response = await fetch(`${API}${path}`, { ...options, headers }); }
  catch { throw new Error('Unable to reach the server. Please try again.'); }
  let payload = null;
  try { payload = await response.json(); } catch { /* Empty or non-JSON response. */ }
  if (response.status === 401) {
    token = null;
    setAuthNavigation();
    window.location.hash = '#/login';
    throw new Error('Your session has ended. Please log in again.');
  }
  if (!response.ok || payload?.success === false) throw new Error(errorText(payload, `Request failed (${response.status}).`));
  return payload?.data;
}
function route() {
  const hash = window.location.hash || '#/login';
  const parts = hash.replace(/^#\/?/, '').split('/').filter(Boolean);
  const isAuth = parts[0] === 'login' || parts[0] === 'register';
  if (!token && !isAuth) { window.location.hash = '#/login'; return; }
  if (token && isAuth) { window.location.hash = '#/dashboard'; return; }
  message('');
  if (parts[0] === 'login' || parts[0] === 'register') renderAuth(parts[0]);
  else if (parts[0] === 'dashboard') renderDashboard();
  else if (parts[0] === 'task' && parts[1] === 'new') renderTaskForm();
  else if (parts[0] === 'task' && /^\d+$/.test(parts[1] || '')) {
    if (parts[2] === 'edit') renderTaskForm(Number(parts[1]));
    else renderTaskDetail(Number(parts[1]));
  } else window.location.hash = '#/dashboard';
}
function renderAuth(mode) {
  showOnly('auth-view');
  $('#login-panel').hidden = mode !== 'login';
  $('#register-panel').hidden = mode !== 'register';
  $('#auth-heading').textContent = mode === 'login' ? 'A calmer way to manage tasks.' : 'Start organizing today.';
  setTimeout(() => $(`#${mode}-email`).focus(), 0);
}
function filterParams(offset) {
  const params = new URLSearchParams({ offset: String(offset), limit: String(PAGE_SIZE) });
  if (filters.search.trim()) params.set('search', filters.search.trim());
  if (filters.status) params.set('status', filters.status);
  if (filters.priority) params.set('priority', filters.priority);
  return params;
}
async function renderDashboard(offset = 0) {
  showOnly('dashboard-view');
  $('#loading-region').hidden = false; $('#empty-region').hidden = true; $('#task-list').replaceChildren(); $('#pagination').hidden = true;
  try {
    const result = await request(`/tasks?${filterParams(offset)}`);
    taskPage = result;
    renderStats(result.items);
    renderTaskList(result.items);
    $('#result-summary').textContent = `${result.total} task${result.total === 1 ? '' : 's'} total`;
    renderPagination(result);
  } catch (err) { message(err.message, 'error'); }
  finally { $('#loading-region').hidden = true; }
}
function renderStats(items) {
  const count = (status) => items.filter((task) => task.status === status).length;
  $('#stat-total').textContent = items.length;
  $('#stat-pending').textContent = count('Pending');
  $('#stat-progress').textContent = count('In Progress');
  $('#stat-completed').textContent = count('Completed');
}
function renderTaskList(items) {
  const list = $('#task-list'); list.replaceChildren();
  $('#empty-region').hidden = items.length !== 0;
  items.forEach((task) => {
    const card = document.createElement('article'); card.className = 'task-card';
    const content = document.createElement('div');
    const title = document.createElement('h3'); const link = document.createElement('a'); link.href = `#/task/${task.id}`; link.textContent = task.title; title.append(link);
    const meta = document.createElement('div'); meta.className = 'task-meta';
    const priority = document.createElement('span'); priority.className = `badge priority-${task.priority.toLowerCase()}`; priority.textContent = task.priority;
    const status = document.createElement('span'); status.className = 'badge'; status.textContent = task.status;
    const due = document.createElement('span'); due.textContent = `Due ${formatDate(task.due_date)}`;
    meta.append(priority, status, due); content.append(title, meta);
    const actions = document.createElement('div'); actions.className = 'task-actions';
    if (task.status !== 'Completed') actions.append(actionButton('Complete', 'complete', task.id, 'button-secondary'));
    actions.append(actionButton('Edit', 'edit', task.id, 'button-quiet'), actionButton('Delete', 'delete', task.id, 'button-quiet danger'));
    card.append(content, actions); list.append(card);
  });
}
function actionButton(label, action, id, classes) { const button = document.createElement('button'); button.type = 'button'; button.className = `button icon-button ${classes}`; button.dataset.action = action; button.dataset.id = String(id); button.textContent = label; return button; }
function renderPagination(result) {
  const nav = $('#pagination'); nav.replaceChildren();
  if (!result.total) return;
  const previous = actionButton('Previous', 'page', Math.max(0, result.offset - PAGE_SIZE), 'button-quiet'); previous.disabled = result.offset === 0;
  const position = document.createElement('span'); position.className = 'muted'; position.textContent = `${result.offset + 1}–${Math.min(result.offset + result.items.length, result.total)} of ${result.total}`;
  const next = actionButton('Next', 'page', result.offset + PAGE_SIZE, 'button-quiet'); next.disabled = result.offset + result.limit >= result.total;
  nav.append(previous, position, next); nav.hidden = false;
}
function formatDate(value) { return new Intl.DateTimeFormat(undefined, { dateStyle: 'medium' }).format(new Date(`${value}T00:00:00`)); }
async function renderTaskDetail(id) {
  showOnly('task-view'); $('#task-content').innerHTML = '<div class="loading" role="status">Loading task…</div>';
  try {
    const task = await request(`/tasks/${id}`); const content = $('#task-content'); content.replaceChildren();
    const panel = document.createElement('article'); panel.className = 'panel';
    const header = document.createElement('div'); header.className = 'detail-header';
    const titleArea = document.createElement('div'); const eyebrow = document.createElement('p'); eyebrow.className = 'eyebrow'; eyebrow.textContent = task.status; const heading = document.createElement('h1'); heading.textContent = task.title; titleArea.append(eyebrow, heading);
    header.append(titleArea, actionButton('Edit task', 'edit', task.id, 'button-secondary')); panel.append(header);
    const description = document.createElement('p'); description.className = 'detail-description'; description.textContent = task.description; panel.append(description);
    const data = document.createElement('dl'); data.className = 'detail-data'; [['Priority', task.priority], ['Due date', formatDate(task.due_date)], ['Status', task.status]].forEach(([key, value]) => { const div = document.createElement('div'); const dt = document.createElement('dt'); dt.textContent = key; const dd = document.createElement('dd'); dd.textContent = value; div.append(dt, dd); data.append(div); }); panel.append(data);
    const actions = document.createElement('div'); actions.className = 'form-actions'; if (task.status !== 'Completed') actions.append(actionButton('Mark complete', 'complete', task.id, 'button-primary')); actions.append(actionButton('Delete task', 'delete', task.id, 'button-quiet danger')); panel.append(actions); content.append(panel);
  } catch (err) { $('#task-content').textContent = ''; message(err.message, 'error'); }
}
async function renderTaskForm(id = null) {
  showOnly('task-form-view'); const form = $('#task-form'); form.reset(); $('#task-id').value = id || ''; $('#task-form-heading').textContent = id ? 'Edit task' : 'Create task';
  if (!id) return;
  $('#task-form-heading').insertAdjacentText('afterend', '');
  try { const task = await request(`/tasks/${id}`); ['title', 'description', 'priority', 'status', 'due_date'].forEach((key) => { $(`#task-${key.replace('_', '-')}`).value = task[key]; }); }
  catch (err) { message(err.message, 'error'); window.location.hash = '#/dashboard'; }
}
function setBusy(form, busy) { form.querySelectorAll('button').forEach((button) => { button.disabled = busy; }); }

document.addEventListener('submit', async (event) => {
  const form = event.target;
  if (form.id === 'filter-form') { event.preventDefault(); filters = { search: $('#search').value, status: $('#filter-status').value, priority: $('#filter-priority').value }; renderDashboard(); return; }
  if (!['login-form', 'register-form', 'task-form'].includes(form.id)) return;
  event.preventDefault(); message('');
  if (!form.reportValidity()) return;
  if (form.id === 'register-form' && $('#register-password').value !== $('#register-password-confirm').value) { message('Passwords do not match.', 'error'); $('#register-password-confirm').focus(); return; }
  setBusy(form, true);
  try {
    if (form.id === 'login-form' || form.id === 'register-form') {
      const prefix = form.id === 'login-form' ? 'login' : 'register';
      const payload = { email: $(`#${prefix}-email`).value.trim(), password: $(`#${prefix}-password`).value };
      const data = await request(`/auth/${prefix}`, { method: 'POST', body: JSON.stringify(payload) });
      if (prefix === 'register') { message('Account created. Please log in.', 'success'); window.location.hash = '#/login'; }
      else { token = data.access_token; setAuthNavigation(); message('You are logged in.', 'success'); window.location.hash = '#/dashboard'; }
    } else {
      const id = $('#task-id').value; const payload = { title: $('#task-title').value.trim(), description: $('#task-description').value.trim(), priority: $('#task-priority').value, status: $('#task-status').value, due_date: $('#task-due-date').value };
      if (!payload.title || !payload.description) throw new Error('Title and description are required.');
      const task = await request(id ? `/tasks/${id}` : '/tasks', { method: id ? 'PUT' : 'POST', body: JSON.stringify(payload) });
      message(id ? 'Task updated.' : 'Task created.', 'success'); window.location.hash = `#/task/${task.id}`;
    }
  } catch (err) { message(err.message, 'error'); }
  finally { setBusy(form, false); }
});
document.addEventListener('click', async (event) => {
  const button = event.target.closest('button[data-action]'); if (!button) return;
  const { action, id } = button.dataset;
  if (action === 'edit') { window.location.hash = `#/task/${id}/edit`; return; }
  if (action === 'page') { renderDashboard(Number(id)); return; }
  if (action === 'delete' && !window.confirm('Delete this task? This cannot be undone.')) return;
  button.disabled = true;
  try {
    if (action === 'complete') { await request(`/tasks/${id}/complete`, { method: 'PATCH' }); message('Task completed.', 'success'); }
    if (action === 'delete') { await request(`/tasks/${id}`, { method: 'DELETE' }); message('Task deleted.', 'success'); }
    if (window.location.hash.startsWith(`#/task/${id}`)) window.location.hash = '#/dashboard'; else renderDashboard(taskPage.offset);
  } catch (err) { message(err.message, 'error'); button.disabled = false; }
});
$('#clear-filters').addEventListener('click', () => { $('#filter-form').reset(); filters = { search: '', status: '', priority: '' }; renderDashboard(); });
$('#logout-button').addEventListener('click', () => { token = null; setAuthNavigation(); message('You have been logged out.', 'success'); window.location.hash = '#/login'; });
window.addEventListener('hashchange', route);
setAuthNavigation(); route();
