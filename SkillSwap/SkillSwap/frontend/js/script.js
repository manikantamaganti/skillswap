/**
 * SkillSwap - Core JavaScript Controller & Single Script Client
 * Handles routing, API communications, sidebar state, modals, toasts,
 * and page-specific logic across all 12 platform views.
 */

const API_BASE = '';
let currentUser = null;

// ===================================================================
// Core Utilities
// ===================================================================
async function apiCall(endpoint, options = {}) {
  const defaultHeaders = { 'Accept': 'application/json' };
  if (!(options.body instanceof FormData)) {
    defaultHeaders['Content-Type'] = 'application/json';
  }

  const config = {
    method: options.method || 'GET',
    headers: { ...defaultHeaders, ...options.headers },
    credentials: 'include',
    ...options
  };

  if (options.data && !(options.data instanceof FormData)) {
    config.body = JSON.stringify(options.data);
  }

  try {
    const response = await fetch(`${API_BASE}${endpoint}`, config);
    const result = await response.json().catch(() => ({
      success: false,
      message: `HTTP Error ${response.status}`
    }));
    return { ok: response.ok, status: response.status, ...result };
  } catch (err) {
    console.error('Fetch error:', err);
    return {
      ok: false,
      success: false,
      message: 'Cannot connect to SkillSwap server. Please ensure the backend is running.'
    };
  }
}

function showToast(message, type = 'info', duration = 3500) {
  let container = document.getElementById('toast-container');
  if (!container) {
    container = document.createElement('div');
    container.id = 'toast-container';
    document.body.appendChild(container);
  }

  const toast = document.createElement('div');
  toast.className = `toast ${type}`;
  const icons = { success: '✓', error: '✕', warning: '⚠', info: 'ℹ' };

  toast.innerHTML = `
    <span style="font-weight: 800; font-size: 1.1rem;">${icons[type] || 'ℹ'}</span>
    <span style="flex: 1;">${message}</span>
  `;
  container.appendChild(toast);

  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transform = 'translateX(20px)';
    toast.style.transition = 'all 0.3s ease';
    setTimeout(() => toast.remove(), 300);
  }, duration);
}

function openModal(id) {
  const m = document.getElementById(id);
  if (m) {
    m.classList.add('active');
    document.body.style.overflow = 'hidden';
  }
}

function closeModal(id) {
  const m = document.getElementById(id);
  if (m) {
    m.classList.remove('active');
    document.body.style.overflow = 'auto';
  }
}

document.addEventListener('click', (e) => {
  if (e.target.classList.contains('modal-overlay')) {
    e.target.classList.remove('active');
    document.body.style.overflow = 'auto';
  }
});

function generateAvatarHtml(imageName, fullName = 'Student', size = 42) {
  const initials = fullName
    .split(' ')
    .filter(Boolean)
    .slice(0, 2)
    .map(n => n[0].toUpperCase())
    .join('');

  const colors = [
    ['#2563eb', '#3b82f6'],
    ['#7c3aed', '#a855f7'],
    ['#059669', '#10b981'],
    ['#d97706', '#f59e0b'],
    ['#dc2626', '#ef4444'],
    ['#0284c7', '#38bdf8']
  ];
  const charCode = (fullName.charCodeAt(0) || 65) + (fullName.charCodeAt(1) || 66);
  const colorPair = colors[charCode % colors.length];

  return `
    <div style="width: ${size}px; height: ${size}px; min-width: ${size}px; border-radius: 50%; background: linear-gradient(135deg, ${colorPair[0]}, ${colorPair[1]}); color: white; display: inline-flex; align-items: center; justify-content: center; font-weight: 700; font-size: ${Math.round(size * 0.4)}px; text-transform: uppercase; box-shadow: 0 2px 6px rgba(0,0,0,0.1);">
      ${initials || 'S'}
    </div>
  `;
}

// ===================================================================
// Auth Verification & Sidebar Layout Sync
// ===================================================================
async function checkAuth(requireAuth = false, requireAdmin = false) {
  const res = await apiCall('/api/auth/me');

  if (res.ok && res.success && res.user) {
    currentUser = res.user;

    // Check admin gate
    if (requireAdmin && currentUser.role !== 'admin') {
      showToast('Access restricted to administrators.', 'error');
      setTimeout(() => window.location.href = 'dashboard.html', 1000);
      return null;
    }

    updateSidebarUI(currentUser);
    return currentUser;
  } else {
    currentUser = null;
    if (requireAuth || requireAdmin) {
      sessionStorage.setItem('redirect_after_login', window.location.href);
      window.location.href = 'login.html';
    }
    return null;
  }
}

function updateSidebarUI(user) {
  // Update user info in sidebar
  const avatarEl = document.getElementById('sidebar-user-avatar');
  const nameEl = document.getElementById('sidebar-user-name');
  const roleEl = document.getElementById('sidebar-user-role');
  const notifBadge = document.getElementById('sidebar-notif-badge');
  const headerNotifDot = document.getElementById('header-notif-dot');
  const adminMenuItem = document.getElementById('sidebar-admin-item');

  if (avatarEl) avatarEl.innerHTML = generateAvatarHtml(user.profile_image, user.full_name, 38);
  if (nameEl) nameEl.textContent = user.full_name;
  if (roleEl) roleEl.textContent = user.role === 'admin' ? 'Administrator' : `${user.department} • ${user.year_of_study}`;

  if (user.unread_notifications > 0) {
    if (notifBadge) {
      notifBadge.textContent = user.unread_notifications;
      notifBadge.style.display = 'inline-block';
    }
    if (headerNotifDot) headerNotifDot.style.display = 'block';
  } else {
    if (notifBadge) notifBadge.style.display = 'none';
    if (headerNotifDot) headerNotifDot.style.display = 'none';
  }

  // Admin visibility
  if (adminMenuItem) {
    adminMenuItem.style.display = user.role === 'admin' ? 'block' : 'none';
  }

  // Highlight active sidebar item
  const currentPath = window.location.pathname.toLowerCase();
  document.querySelectorAll('.sidebar-link').forEach(link => {
    const href = link.getAttribute('href')?.toLowerCase();
    if (href && currentPath.includes(href)) {
      link.classList.add('active');
    } else {
      link.classList.remove('active');
    }
  });
}

async function handleLogout() {
  await apiCall('/api/auth/logout', { method: 'POST' });
  showToast('Logged out successfully.', 'info');
  setTimeout(() => window.location.href = 'index.html', 500);
}

// Mobile sidebar toggle
document.addEventListener('DOMContentLoaded', () => {
  const toggleBtn = document.getElementById('mobile-sidebar-toggle');
  const sidebar = document.querySelector('.sidebar');
  if (toggleBtn && sidebar) {
    toggleBtn.addEventListener('click', () => {
      sidebar.classList.toggle('show');
    });
  }
});

// ===================================================================
// 1. Dashboard Page Logic (dashboard.html)
// ===================================================================
async function initDashboard() {
  const user = await checkAuth(true);
  if (!user) return;

  const res = await apiCall('/api/dashboard');
  if (!res.ok || !res.success) return;

  const stats = res.stats;
  document.getElementById('dash-student-name').textContent = res.user.full_name;
  document.getElementById('stat-teach-count').textContent = stats.teaching_count;
  document.getElementById('stat-learn-count').textContent = stats.learning_count;
  document.getElementById('stat-connections-count').textContent = stats.total_connections;
  document.getElementById('stat-pending-count').textContent = stats.pending_requests;
  document.getElementById('stat-sessions-count').textContent = stats.active_sessions;

  // Render Teaching Skills
  const teachBox = document.getElementById('dash-teaching-skills');
  if (teachBox) {
    teachBox.innerHTML = res.teaching_skills.length > 0
      ? res.teaching_skills.map(s => `<span class="badge badge-teach">✓ ${s.skill_name}</span>`).join('')
      : `<p style="font-size: 0.85rem; color: var(--text-muted);">No teaching skills added yet. <a href="skills.html">Add Skills →</a></p>`;
  }

  // Render Learning Skills
  const learnBox = document.getElementById('dash-learning-skills');
  if (learnBox) {
    learnBox.innerHTML = res.learning_skills.length > 0
      ? res.learning_skills.map(s => `<span class="badge badge-learn">★ ${s.skill_name}</span>`).join('')
      : `<p style="font-size: 0.85rem; color: var(--text-muted);">No learning interests added yet. <a href="skills.html">Set Goals →</a></p>`;
  }

  // Render Upcoming Sessions
  const sessBox = document.getElementById('dash-upcoming-sessions');
  if (sessBox) {
    if (res.upcoming_sessions && res.upcoming_sessions.length > 0) {
      sessBox.innerHTML = res.upcoming_sessions.map(s => `
        <div style="padding: 0.85rem; background: var(--bg-body); border-radius: var(--radius-md); border: 1px solid var(--border); margin-bottom: 0.75rem; display: flex; justify-content: space-between; align-items: center;">
          <div>
            <h5 style="font-size: 0.95rem; margin-bottom: 0.2rem;">${s.session_title}</h5>
            <div style="font-size: 0.82rem; color: var(--text-muted);">
              ${s.skill_name} • Partner: <strong>${s.partner_name}</strong> • ${s.session_date} at ${s.session_time.slice(0, 5)}
            </div>
          </div>
          ${s.meeting_link ? `<a href="${s.meeting_link}" target="_blank" class="btn btn-primary btn-sm">Join Meeting</a>` : ''}
        </div>
      `).join('');
    } else {
      sessBox.innerHTML = `<p style="font-size: 0.88rem; color: var(--text-muted); padding: 1rem 0;">No active learning sessions. <a href="sessions.html">Schedule one with a peer →</a></p>`;
    }
  }

  // Render Recommendations
  loadDashboardRecommendations();
}

async function loadDashboardRecommendations() {
  const container = document.getElementById('dash-recommendations');
  if (!container) return;

  const res = await apiCall('/api/matching/recommendations');
  if (!res.ok || !res.recommendations || res.recommendations.length === 0) {
    container.innerHTML = `<p style="color: var(--text-muted); font-size: 0.9rem;">Add your teaching and learning skills to view personalized peer matches!</p>`;
    return;
  }

  container.innerHTML = res.recommendations.map(p => {
    const avatar = generateAvatarHtml(p.profile_image, p.full_name, 48);
    return `
      <div style="padding: 1rem; border: 1px solid var(--border); border-radius: var(--radius-md); margin-bottom: 0.85rem; background: white; display: flex; justify-content: space-between; align-items: center; gap: 1rem;">
        <div style="display: flex; gap: 0.85rem; align-items: center;">
          ${avatar}
          <div>
            <div style="display: flex; align-items: center; gap: 0.5rem;">
              <h5 style="margin: 0; font-size: 1rem;">${p.full_name}</h5>
              <span class="badge badge-match">${p.match_badge}</span>
            </div>
            <div style="font-size: 0.8rem; color: var(--text-muted);">${p.department} • ${p.college_name}</div>
            <div style="font-size: 0.82rem; color: var(--primary); margin-top: 0.2rem;">${p.match_reason}</div>
          </div>
        </div>
        <button class="btn btn-primary btn-sm" onclick="openRequestProposalModal(${p.user_id}, '${escapeQuotes(p.full_name)}')">
          Exchange ➔
        </button>
      </div>
    `;
  }).join('');
}

// ===================================================================
// 2. Skill Management Page Logic (skills.html)
// ===================================================================
async function initSkills() {
  const user = await checkAuth(true);
  if (!user) return;

  loadMySkillsLists();
  loadAvailableMasterSkills();
}

async function loadMySkillsLists() {
  const res = await apiCall('/api/skills/my-skills');
  if (!res.ok) return;

  const teachContainer = document.getElementById('my-teaching-skills-list');
  const learnContainer = document.getElementById('my-learning-skills-list');

  if (teachContainer) {
    teachContainer.innerHTML = res.teaching.length > 0
      ? res.teaching.map(s => `
        <span class="badge badge-teach" style="padding: 0.4rem 0.8rem; font-size: 0.85rem;">
          ✓ ${s.skill_name} (${s.category})
          <button onclick="removeSkill(${s.skill_id}, 'teach')" style="background:none; border:none; color:inherit; margin-left:6px; cursor:pointer; font-weight:800;">×</button>
        </span>
      `).join('')
      : `<p style="color: var(--text-muted); font-size: 0.88rem;">No teaching skills added yet. Select from the catalog below.</p>`;
  }

  if (learnContainer) {
    learnContainer.innerHTML = res.learning.length > 0
      ? res.learning.map(s => `
        <span class="badge badge-learn" style="padding: 0.4rem 0.8rem; font-size: 0.85rem;">
          ★ ${s.skill_name} (${s.category})
          <button onclick="removeSkill(${s.skill_id}, 'learn')" style="background:none; border:none; color:inherit; margin-left:6px; cursor:pointer; font-weight:800;">×</button>
        </span>
      `).join('')
      : `<p style="color: var(--text-muted); font-size: 0.88rem;">No learning interests added yet. Select what you wish to master.</p>`;
  }
}

async function loadAvailableMasterSkills() {
  const container = document.getElementById('master-skills-catalog');
  if (!container) return;

  const res = await apiCall('/api/skills');
  if (!res.ok || !res.skills) return;

  container.innerHTML = res.skills.map(s => `
    <div style="background: white; border: 1px solid var(--border); border-radius: var(--radius-md); padding: 1rem; display: flex; flex-direction: column; justify-content: space-between;">
      <div>
        <span style="font-size: 0.75rem; color: var(--purple); font-weight: 700; text-transform: uppercase;">${s.category}</span>
        <h4 style="font-size: 1.1rem; margin: 0.25rem 0 0.5rem;">${s.skill_name}</h4>
        <div style="font-size: 0.8rem; color: var(--text-muted); margin-bottom: 0.85rem;">
          ${s.teachers_count || 0} teaching • ${s.learners_count || 0} learning
        </div>
      </div>
      <div style="display: flex; gap: 0.5rem;">
        <button class="btn btn-outline-primary btn-sm" style="flex: 1;" onclick="addSkill(${s.skill_id}, '${s.skill_name}', 'teach')">
          + Can Teach
        </button>
        <button class="btn btn-purple btn-sm" style="flex: 1;" onclick="addSkill(${s.skill_id}, '${s.skill_name}', 'learn')">
          + Want to Learn
        </button>
      </div>
    </div>
  `).join('');
}

async function addSkill(skillId, skillName, type) {
  const res = await apiCall('/api/skills/my-skills', {
    method: 'POST',
    data: { skill_id: skillId, skill_name: skillName, skill_type: type }
  });

  if (res.ok && res.success) {
    showToast(res.message, 'success');
    loadMySkillsLists();
  } else {
    showToast(res.message || 'Could not add skill.', 'error');
  }
}

async function removeSkill(skillId, type) {
  const res = await apiCall(`/api/skills/my-skills/${skillId}?type=${type}`, {
    method: 'DELETE'
  });
  if (res.ok) {
    showToast('Skill removed.', 'info');
    loadMySkillsLists();
  }
}

async function addCustomSkill(type) {
  const input = document.getElementById(type === 'teach' ? 'custom-teach-skill' : 'custom-learn-skill');
  const name = input?.value.trim();
  if (!name) return;

  const res = await apiCall('/api/skills/my-skills', {
    method: 'POST',
    data: { skill_name: name, category: 'General', skill_type: type }
  });

  if (res.ok && res.success) {
    showToast(res.message, 'success');
    if (input) input.value = '';
    loadMySkillsLists();
    loadAvailableMasterSkills();
  } else {
    showToast(res.message || 'Error adding custom skill', 'error');
  }
}

// ===================================================================
// 3. Find Learning Partners (find_partners.html)
// ===================================================================
let partnersSearchTimer = null;

async function initFindPartners() {
  await checkAuth(); // Optional login
  loadPartners();

  const searchInput = document.getElementById('partner-search-input');
  if (searchInput) {
    searchInput.addEventListener('input', () => {
      clearTimeout(partnersSearchTimer);
      partnersSearchTimer = setTimeout(loadPartners, 300);
    });
  }
}

async function loadPartners() {
  const container = document.getElementById('partners-grid');
  if (!container) return;

  const search = document.getElementById('partner-search-input')?.value.trim() || '';
  const dept = document.getElementById('partner-dept-filter')?.value || 'all';
  const category = document.getElementById('partner-category-filter')?.value || 'all';

  let url = `/api/matching/partners?search=${encodeURIComponent(search)}&department=${encodeURIComponent(dept)}&category=${encodeURIComponent(category)}`;
  const res = await apiCall(url);
  if (!res.ok) return;

  // Populate department filter once
  const deptSelect = document.getElementById('partner-dept-filter');
  if (deptSelect && deptSelect.options.length <= 1 && res.departments) {
    res.departments.forEach(d => {
      const opt = document.createElement('option');
      opt.value = d;
      opt.textContent = d;
      deptSelect.appendChild(opt);
    });
  }

  if (res.partners.length === 0) {
    container.innerHTML = `<div style="grid-column: 1/-1; text-align: center; padding: 3rem; color: var(--text-muted);">No student peers found matching your criteria.</div>`;
    return;
  }

  container.innerHTML = res.partners.map(p => {
    const avatar = generateAvatarHtml(p.profile_image, p.full_name, 56);
    const teachPills = p.teaching_skills.map(s => `<span class="badge badge-teach">${s.skill_name}</span>`).join('') || '<span style="font-size:0.8rem; color:var(--text-light);">None</span>';
    const learnPills = p.learning_skills.map(s => `<span class="badge badge-learn">${s.skill_name}</span>`).join('') || '<span style="font-size:0.8rem; color:var(--text-light);">None</span>';

    return `
      <div class="card" style="margin: 0; display: flex; flex-direction: column;">
        <div style="display: flex; gap: 0.85rem; align-items: center; margin-bottom: 0.85rem;">
          ${avatar}
          <div>
            <h4 style="margin: 0; font-size: 1.1rem;">${p.full_name}</h4>
            <div style="font-size: 0.82rem; color: var(--text-muted);">${p.department} • ${p.year_of_study}</div>
            <div style="font-size: 0.8rem; color: var(--primary);">${p.college_name}</div>
          </div>
        </div>

        <div style="margin-bottom: 0.75rem;">
          <span class="badge badge-match">${p.match_badge}</span>
          <p style="font-size: 0.84rem; color: var(--text-muted); margin-top: 0.35rem;">${p.match_reason}</p>
        </div>

        <div style="margin-bottom: 0.65rem;">
          <div style="font-size: 0.75rem; font-weight: 700; color: var(--success); text-transform: uppercase;">Can Teach:</div>
          <div style="display: flex; flex-wrap: wrap; gap: 0.35rem; margin-top: 0.25rem;">${teachPills}</div>
        </div>

        <div style="margin-bottom: 1.25rem;">
          <div style="font-size: 0.75rem; font-weight: 700; color: var(--purple); text-transform: uppercase;">Wants to Learn:</div>
          <div style="display: flex; flex-wrap: wrap; gap: 0.35rem; margin-top: 0.25rem;">${learnPills}</div>
        </div>

        <div style="margin-top: auto; display: flex; gap: 0.5rem;">
          <a href="profile.html?id=${p.user_id}" class="btn btn-secondary btn-sm" style="flex: 1;">View Profile</a>
          ${p.is_connected ? `
            <a href="chat.html?user=${p.user_id}" class="btn btn-purple btn-sm" style="flex: 1.2;">Chat Now 💬</a>
          ` : p.has_pending_request ? `
            <button class="btn btn-secondary btn-sm" disabled style="flex: 1.2;">Pending...</button>
          ` : `
            <button class="btn btn-primary btn-sm" style="flex: 1.2;" onclick="openRequestProposalModal(${p.user_id}, '${escapeQuotes(p.full_name)}')">
              Send Request ➔
            </button>
          `}
        </div>
      </div>
    `;
  }).join('');
}

function openRequestProposalModal(receiverId, receiverName) {
  if (!currentUser) {
    showToast('Please log in to send skill exchange proposals.', 'warning');
    setTimeout(() => window.location.href = 'login.html', 1000);
    return;
  }

  document.getElementById('modal-receiver-id').value = receiverId;
  document.getElementById('modal-receiver-name').textContent = receiverName;
  openModal('exchange-request-modal');
}

async function submitExchangeRequest(e) {
  e.preventDefault();
  const receiverId = document.getElementById('modal-receiver-id').value;
  const skillOffered = document.getElementById('modal-skill-offered').value.trim();
  const skillRequested = document.getElementById('modal-skill-requested').value.trim();
  const message = document.getElementById('modal-request-message').value.trim();

  const res = await apiCall('/api/requests', {
    method: 'POST',
    data: { receiver_id: receiverId, skill_offered: skillOffered, skill_requested: skillRequested, message }
  });

  if (res.ok && res.success) {
    showToast(res.message, 'success');
    closeModal('exchange-request-modal');
    loadPartners();
  } else {
    showToast(res.message || 'Failed to send request.', 'error');
  }
}

// ===================================================================
// 4. Requests & Connections (requests.html)
// ===================================================================
async function initRequests() {
  const user = await checkAuth(true);
  if (!user) return;

  loadReceivedRequests();
  loadSentRequests();
  loadConnectedPeers();
}

function switchRequestsTab(tab) {
  document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
  document.querySelectorAll('.tab-pane').forEach(p => p.style.display = 'none');

  document.getElementById(`tab-btn-${tab}`)?.classList.add('active');
  const pane = document.getElementById(`tab-pane-${tab}`);
  if (pane) pane.style.display = 'block';
}

async function loadReceivedRequests() {
  const container = document.getElementById('received-requests-list');
  if (!container) return;

  const res = await apiCall('/api/requests/received');
  if (!res.ok) return;

  if (res.requests.length === 0) {
    container.innerHTML = `<p style="color: var(--text-muted); padding: 2rem; text-align: center;">No incoming skill exchange requests right now.</p>`;
    return;
  }

  container.innerHTML = res.requests.map(r => {
    const avatar = generateAvatarHtml(r.sender_avatar, r.sender_name, 48);
    return `
      <div class="card" style="display: flex; justify-content: space-between; align-items: center; gap: 1.5rem; flex-wrap: wrap;">
        <div style="display: flex; gap: 1rem; align-items: center;">
          ${avatar}
          <div>
            <div style="display: flex; align-items: center; gap: 0.5rem;">
              <h4 style="margin: 0;">${r.sender_name}</h4>
              <span class="badge badge-${r.status}">${r.status}</span>
            </div>
            <div style="font-size: 0.85rem; color: var(--text-muted);">${r.sender_department} • ${r.sender_college}</div>
            <div style="font-size: 0.9rem; margin: 0.35rem 0;">
              Offers: <strong style="color:var(--success);">${r.skill_offered}</strong> ⇄ Wants: <strong style="color:var(--purple);">${r.skill_requested}</strong>
            </div>
            <p style="font-size: 0.85rem; color: var(--text-main); font-style: italic;">"${r.message}"</p>
          </div>
        </div>
        <div style="display: flex; gap: 0.5rem;">
          ${r.status === 'pending' ? `
            <button class="btn btn-success btn-sm" onclick="respondRequest(${r.request_id}, 'accepted')">Accept</button>
            <button class="btn btn-secondary btn-sm" onclick="respondRequest(${r.request_id}, 'rejected')">Decline</button>
          ` : r.status === 'accepted' ? `
            <a href="chat.html?user=${r.sender_id}" class="btn btn-purple btn-sm">Open Chat 💬</a>
          ` : ''}
        </div>
      </div>
    `;
  }).join('');
}

async function loadSentRequests() {
  const container = document.getElementById('sent-requests-list');
  if (!container) return;

  const res = await apiCall('/api/requests/sent');
  if (!res.ok) return;

  if (res.requests.length === 0) {
    container.innerHTML = `<p style="color: var(--text-muted); padding: 2rem; text-align: center;">You haven't sent any skill exchange proposals yet.</p>`;
    return;
  }

  container.innerHTML = res.requests.map(r => {
    const avatar = generateAvatarHtml(r.receiver_avatar, r.receiver_name, 48);
    return `
      <div class="card" style="display: flex; justify-content: space-between; align-items: center; gap: 1.5rem; flex-wrap: wrap;">
        <div style="display: flex; gap: 1rem; align-items: center;">
          ${avatar}
          <div>
            <div style="display: flex; align-items: center; gap: 0.5rem;">
              <h4 style="margin: 0;">${r.receiver_name}</h4>
              <span class="badge badge-${r.status}">${r.status}</span>
            </div>
            <div style="font-size: 0.85rem; color: var(--text-muted);">${r.receiver_department} • ${r.receiver_college}</div>
            <div style="font-size: 0.9rem; margin: 0.35rem 0;">
              You Offer: <strong style="color:var(--success);">${r.skill_offered}</strong> ⇄ You Want: <strong style="color:var(--purple);">${r.skill_requested}</strong>
            </div>
          </div>
        </div>
        <div>
          ${r.status === 'pending' ? `
            <button class="btn btn-secondary btn-sm" onclick="respondRequest(${r.request_id}, 'cancelled')">Cancel Request</button>
          ` : r.status === 'accepted' ? `
            <a href="chat.html?user=${r.receiver_id}" class="btn btn-purple btn-sm">Chat 💬</a>
          ` : ''}
        </div>
      </div>
    `;
  }).join('');
}

async function loadConnectedPeers() {
  const container = document.getElementById('connected-peers-list');
  if (!container) return;

  const res = await apiCall('/api/requests/connections');
  if (!res.ok) return;

  if (res.connections.length === 0) {
    container.innerHTML = `<p style="color: var(--text-muted); padding: 2rem; text-align: center;">No accepted connections yet. Accept an incoming request to connect!</p>`;
    return;
  }

  container.innerHTML = res.connections.map(c => {
    const avatar = generateAvatarHtml(c.profile_image, c.full_name, 50);
    return `
      <div class="card" style="display: flex; justify-content: space-between; align-items: center; gap: 1rem; flex-wrap: wrap;">
        <div style="display: flex; gap: 1rem; align-items: center;">
          ${avatar}
          <div>
            <h4 style="margin: 0;">${c.full_name}</h4>
            <div style="font-size: 0.82rem; color: var(--text-muted);">${c.department} • ${c.college_name}</div>
            <div style="font-size: 0.8rem; color: var(--primary);">Connected Partner</div>
          </div>
        </div>
        <div style="display: flex; gap: 0.5rem;">
          <a href="chat.html?user=${c.user_id}" class="btn btn-primary btn-sm">Send Message 💬</a>
          <a href="sessions.html?host=${c.user_id}" class="btn btn-secondary btn-sm">Schedule Session 📅</a>
        </div>
      </div>
    `;
  }).join('');
}

async function respondRequest(requestId, status) {
  const res = await apiCall(`/api/requests/${requestId}/status`, {
    method: 'PUT',
    data: { status }
  });
  if (res.ok) {
    showToast(res.message, 'success');
    loadReceivedRequests();
    loadSentRequests();
    loadConnectedPeers();
  }
}

// ===================================================================
// 5. Chat & Communication (chat.html)
// ===================================================================
let activeChatPartnerId = null;
let chatPollingTimer = null;

async function initChat() {
  const user = await checkAuth(true);
  if (!user) return;

  const urlParams = new URLSearchParams(window.location.search);
  const targetUser = urlParams.get('user');

  await loadChatContacts(targetUser);

  // Form submit
  const chatForm = document.getElementById('chat-form');
  if (chatForm) {
    chatForm.addEventListener('submit', sendMessage);
  }
}

async function loadChatContacts(selectUserId = null) {
  const container = document.getElementById('chat-contacts-list');
  if (!container) return;

  const res = await apiCall('/api/chat/contacts');
  if (!res.ok) return;

  if (res.contacts.length === 0) {
    container.innerHTML = `<li style="padding: 1.5rem; text-align: center; color: var(--text-muted); font-size: 0.85rem;">No connected peers yet. Connect with students to start chatting!</li>`;
    return;
  }

  container.innerHTML = res.contacts.map(c => {
    const avatar = generateAvatarHtml(c.profile_image, c.full_name, 40);
    return `
      <li class="contact-item ${selectUserId && String(selectUserId) === String(c.user_id) ? 'active' : ''}" 
          id="contact-${c.user_id}" 
          onclick="openConversation(${c.user_id})">
        ${avatar}
        <div class="contact-info">
          <div class="contact-name">${c.full_name}</div>
          <div class="contact-snippet">${c.last_message || 'Connected on SkillSwap'}</div>
        </div>
        ${c.unread_count > 0 ? `<span class="badge" style="background:#ef4444; color:white;">${c.unread_count}</span>` : ''}
      </li>
    `;
  }).join('');

  if (selectUserId) {
    openConversation(parseInt(selectUserId));
  } else if (res.contacts.length > 0 && !activeChatPartnerId) {
    openConversation(res.contacts[0].user_id);
  }
}

async function openConversation(partnerId) {
  activeChatPartnerId = partnerId;

  document.querySelectorAll('.contact-item').forEach(el => el.classList.remove('active'));
  document.getElementById(`contact-${partnerId}`)?.classList.add('active');

  const res = await apiCall(`/api/chat/messages/${partnerId}`);
  if (!res.ok) {
    showToast(res.message, 'error');
    return;
  }

  // Header info
  document.getElementById('chat-active-name').textContent = res.partner.full_name;
  document.getElementById('chat-active-dept').textContent = `${res.partner.department} • ${res.partner.college_name}`;
  document.getElementById('chat-active-avatar').innerHTML = generateAvatarHtml(res.partner.profile_image, res.partner.full_name, 36);

  // Render messages
  const msgBox = document.getElementById('chat-messages-container');
  if (msgBox) {
    msgBox.innerHTML = res.messages.map(m => {
      const isMine = m.sender_id === currentUser.user_id;
      return `
        <div class="message-bubble ${isMine ? 'sent' : 'received'}">
          <div>${m.message_text}</div>
          <div class="message-time">${new Date(m.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</div>
        </div>
      `;
    }).join('');
    msgBox.scrollTop = msgBox.scrollHeight;
  }
}

async function sendMessage(e) {
  e.preventDefault();
  if (!activeChatPartnerId) return;

  const input = document.getElementById('chat-message-input');
  const text = input?.value.trim();
  if (!text) return;

  input.value = '';

  const res = await apiCall('/api/chat/messages', {
    method: 'POST',
    data: { receiver_id: activeChatPartnerId, message_text: text }
  });

  if (res.ok) {
    openConversation(activeChatPartnerId);
  }
}

// ===================================================================
// 6. Learning Sessions (sessions.html)
// ===================================================================
async function initSessions() {
  const user = await checkAuth(true);
  if (!user) return;

  loadSessions();
  populateConnectedPartnersDropdown();

  const sessionForm = document.getElementById('create-session-form');
  if (sessionForm) {
    sessionForm.addEventListener('submit', createNewSession);
  }
}

async function loadSessions() {
  const upcomingBox = document.getElementById('upcoming-sessions-list');
  const pastBox = document.getElementById('past-sessions-list');

  const res = await apiCall('/api/sessions');
  if (!res.ok) return;

  if (upcomingBox) {
    upcomingBox.innerHTML = res.upcoming.length > 0
      ? res.upcoming.map(s => `
        <div class="card">
          <div style="display: flex; justify-content: space-between; align-items: flex-start; gap: 1rem;">
            <div>
              <span class="badge badge-upcoming">Upcoming • ${s.session_date} at ${s.session_time.slice(0, 5)}</span>
              <h3 style="margin: 0.5rem 0 0.25rem; font-size: 1.2rem;">${s.session_title}</h3>
              <p style="font-size: 0.88rem; color: var(--text-muted);">${s.description || 'No session agenda provided.'}</p>
              <div style="font-size: 0.85rem; margin-top: 0.5rem;">
                Host: <strong>${s.host_name}</strong> | Partner: <strong>${s.partner_name}</strong>
              </div>
            </div>
            <div style="display: flex; flex-direction: column; gap: 0.5rem;">
              ${s.meeting_link ? `<a href="${s.meeting_link}" target="_blank" class="btn btn-primary btn-sm">Join Video Meeting 🎥</a>` : ''}
              <button class="btn btn-success btn-sm" onclick="setSessionStatus(${s.session_id}, 'completed')">Mark Completed ✓</button>
              <button class="btn btn-secondary btn-sm" onclick="setSessionStatus(${s.session_id}, 'cancelled')">Cancel</button>
            </div>
          </div>
        </div>
      `).join('')
      : `<p style="color: var(--text-muted); padding: 1.5rem; text-align: center;">No upcoming learning sessions scheduled.</p>`;
  }

  if (pastBox) {
    pastBox.innerHTML = res.past.length > 0
      ? res.past.map(s => `
        <div class="card" style="opacity: 0.85;">
          <span class="badge badge-${s.status}">${s.status.toUpperCase()}</span>
          <h4 style="margin: 0.35rem 0;">${s.session_title} (${s.skill_name})</h4>
          <div style="font-size: 0.82rem; color: var(--text-muted);">
            ${s.session_date} • Host: ${s.host_name} & Partner: ${s.partner_name}
          </div>
        </div>
      `).join('')
      : `<p style="color: var(--text-muted); padding: 1.5rem; text-align: center;">No past sessions.</p>`;
  }
}

async function populateConnectedPartnersDropdown() {
  const select = document.getElementById('session-partner-select');
  if (!select) return;

  const res = await apiCall('/api/requests/connections');
  if (res.ok && res.connections) {
    select.innerHTML = res.connections.map(c => `
      <option value="${c.user_id}">${c.full_name} (${c.department})</option>
    `).join('') || '<option value="">No connected peers yet. Connect first!</option>';
  }
}

async function createNewSession(e) {
  e.preventDefault();
  const partnerId = document.getElementById('session-partner-select').value;
  const title = document.getElementById('session-title-input').value.trim();
  const skill = document.getElementById('session-skill-input').value.trim();
  const date = document.getElementById('session-date-input').value;
  const time = document.getElementById('session-time-input').value;
  const desc = document.getElementById('session-desc-input').value.trim();
  const link = document.getElementById('session-link-input').value.trim();

  const res = await apiCall('/api/sessions', {
    method: 'POST',
    data: {
      partner_id: partnerId,
      session_title: title,
      skill_name: skill,
      session_date: date,
      session_time: time,
      description: desc,
      meeting_link: link
    }
  });

  if (res.ok && res.success) {
    showToast(res.message, 'success');
    closeModal('schedule-session-modal');
    loadSessions();
  } else {
    showToast(res.message || 'Could not schedule session.', 'error');
  }
}

async function setSessionStatus(sessionId, status) {
  const res = await apiCall(`/api/sessions/${sessionId}/status`, {
    method: 'PUT',
    data: { status }
  });
  if (res.ok) {
    showToast(res.message, 'info');
    loadSessions();
  }
}

// ===================================================================
// 7. Notifications (notifications.html)
// ===================================================================
async function initNotifications() {
  const user = await checkAuth(true);
  if (!user) return;

  const container = document.getElementById('notifications-container');
  if (!container) return;

  const res = await apiCall('/api/notifications');
  if (!res.ok) return;

  if (res.notifications.length === 0) {
    container.innerHTML = `<p style="color: var(--text-muted); text-align: center; padding: 3rem;">You have no notifications at this time.</p>`;
    return;
  }

  container.innerHTML = res.notifications.map(n => `
    <div class="card" style="border-left: 4px solid ${n.is_read ? 'var(--border)' : 'var(--primary)'}; margin-bottom: 0.85rem; padding: 1.15rem;">
      <div style="display: flex; justify-content: space-between; align-items: flex-start;">
        <div>
          <h4 style="margin: 0 0 0.25rem; font-size: 1rem; ${n.is_read ? '' : 'color: var(--primary);'}">${n.title}</h4>
          <p style="font-size: 0.9rem; color: var(--text-main); margin-bottom: 0.35rem;">${n.message}</p>
          <span style="font-size: 0.75rem; color: var(--text-light);">${new Date(n.created_at).toLocaleString()}</span>
        </div>
        ${n.link ? `<a href="${n.link}" class="btn btn-secondary btn-sm">View ➔</a>` : ''}
      </div>
    </div>
  `).join('');
}

async function markAllNotificationsRead() {
  const res = await apiCall('/api/notifications/mark-read', { method: 'PUT', data: {} });
  if (res.ok) {
    showToast('All notifications marked as read.', 'info');
    initNotifications();
  }
}

// ===================================================================
// 8. Profile View & Edit (profile.html)
// ===================================================================
async function initProfile() {
  const user = await checkAuth(true);
  if (!user) return;

  // Populate profile fields
  document.getElementById('profile-name').textContent = user.full_name;
  document.getElementById('profile-meta').textContent = `${user.department} • ${user.year_of_study} (${user.college_name})`;
  document.getElementById('profile-bio-text').textContent = user.bio || 'No bio provided.';
  document.getElementById('profile-avatar-box').innerHTML = generateAvatarHtml(user.profile_image, user.full_name, 90);

  // Edit form inputs
  document.getElementById('edit-fullname').value = user.full_name;
  document.getElementById('edit-college').value = user.college_name;
  document.getElementById('edit-department').value = user.department;
  document.getElementById('edit-year').value = user.year_of_study;
  document.getElementById('edit-bio').value = user.bio || '';

  // Teaching and learning skills
  const teachBox = document.getElementById('profile-teaching-skills');
  const learnBox = document.getElementById('profile-learning-skills');

  if (teachBox) {
    teachBox.innerHTML = user.teaching_skills.map(s => `<span class="badge badge-teach">✓ ${s.skill_name}</span>`).join('') || '<span style="color:var(--text-light);">None</span>';
  }
  if (learnBox) {
    learnBox.innerHTML = user.learning_skills.map(s => `<span class="badge badge-learn">★ ${s.skill_name}</span>`).join('') || '<span style="color:var(--text-light);">None</span>';
  }

  // Profile update form handler
  const form = document.getElementById('profile-update-form');
  if (form) {
    form.addEventListener('submit', async (e) => {
      e.preventDefault();
      const res = await apiCall('/api/auth/profile', {
        method: 'PUT',
        data: {
          full_name: document.getElementById('edit-fullname').value.trim(),
          college_name: document.getElementById('edit-college').value.trim(),
          department: document.getElementById('edit-department').value.trim(),
          year_of_study: document.getElementById('edit-year').value,
          bio: document.getElementById('edit-bio').value.trim()
        }
      });
      if (res.ok) {
        showToast(res.message, 'success');
        setTimeout(() => location.reload(), 500);
      }
    });
  }
}

// ===================================================================
// 9. Admin Dashboard (admin.html)
// ===================================================================
async function initAdmin() {
  const user = await checkAuth(true, true);
  if (!user) return;

  loadAdminStats();
  loadAdminUsers();
  loadAdminActivity();
}

async function loadAdminStats() {
  const res = await apiCall('/api/admin/stats');
  if (res.ok && res.stats) {
    document.getElementById('admin-stat-students').textContent = res.stats.total_students;
    document.getElementById('admin-stat-skills').textContent = res.stats.total_skills;
    document.getElementById('admin-stat-requests').textContent = res.stats.total_requests;
    document.getElementById('admin-stat-sessions').textContent = res.stats.active_sessions;
  }
}

async function loadAdminUsers() {
  const tableBody = document.getElementById('admin-users-table-body');
  if (!tableBody) return;

  const res = await apiCall('/api/admin/users');
  if (!res.ok || !res.users) return;

  tableBody.innerHTML = res.users.map(u => `
    <tr>
      <td style="padding: 0.75rem; border-bottom: 1px solid var(--border); font-weight: 600;">${u.full_name}</td>
      <td style="padding: 0.75rem; border-bottom: 1px solid var(--border);">${u.email}</td>
      <td style="padding: 0.75rem; border-bottom: 1px solid var(--border);">${u.college_name}</td>
      <td style="padding: 0.75rem; border-bottom: 1px solid var(--border);">${u.department}</td>
      <td style="padding: 0.75rem; border-bottom: 1px solid var(--border);">
        <span class="badge badge-${u.status === 'active' ? 'accepted' : 'rejected'}">${u.status}</span>
      </td>
      <td style="padding: 0.75rem; border-bottom: 1px solid var(--border);">
        <button class="btn btn-secondary btn-sm" onclick="toggleStudentStatus(${u.user_id}, '${u.status === 'active' ? 'suspended' : 'active'}')">
          ${u.status === 'active' ? 'Suspend' : 'Activate'}
        </button>
        <button class="btn btn-danger btn-sm" onclick="deleteStudent(${u.user_id})">Delete</button>
      </td>
    </tr>
  `).join('');
}

async function toggleStudentStatus(userId, newStatus) {
  const res = await apiCall(`/api/admin/users/${userId}/status`, {
    method: 'PUT',
    data: { status: newStatus }
  });
  if (res.ok) {
    showToast(res.message, 'info');
    loadAdminUsers();
  }
}

async function deleteStudent(userId) {
  if (!confirm('Are you sure you want to permanently delete this student account?')) return;
  const res = await apiCall(`/api/admin/users/${userId}`, { method: 'DELETE' });
  if (res.ok) {
    showToast(res.message, 'success');
    loadAdminUsers();
    loadAdminStats();
  }
}

async function loadAdminActivity() {
  const container = document.getElementById('admin-activity-list');
  if (!container) return;

  const res = await apiCall('/api/admin/activity');
  if (res.ok && res.recent_requests) {
    container.innerHTML = res.recent_requests.map(r => `
      <div style="padding: 0.65rem 0; border-bottom: 1px solid var(--border); font-size: 0.88rem;">
        <strong>${r.sender_name}</strong> proposed exchange to <strong>${r.receiver_name}</strong> (${r.skill_offered} ⇄ ${r.skill_requested}) - <span class="badge badge-${r.status}">${r.status}</span>
      </div>
    `).join('');
  }
}

function escapeQuotes(str) {
  if (!str) return '';
  return str.replace(/'/g, "\\'").replace(/"/g, '&quot;');
}

