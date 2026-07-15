import { api } from '../api/client.js';
import { getCurrentUser } from '../utils/auth.js';

export async function renderAdmin() {
  const me = getCurrentUser();
  if (!me || !me.is_admin) {
    window.location.hash = '#/';
    return;
  }

  // Inject Styles once
  if (!document.getElementById('admin-page-styles')) {
    const style = document.createElement('style');
    style.id = 'admin-page-styles';
    style.textContent = `
      .admin-container {
        padding: 40px;
        max-width: 1200px;
        margin: 0 auto;
        display: flex;
        flex-direction: column;
        gap: 32px;
        color: var(--text-primary);
      }
      .admin-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
      }
      .admin-title {
        font-size: 2rem;
        font-family: var(--font-heading);
        font-weight: 700;
        background: linear-gradient(135deg, var(--primary), var(--secondary));
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
      }
      .stats-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
        gap: 20px;
      }
      .stat-card {
        background: var(--bg-card, #ffffff);
        border: 1px solid var(--border-color);
        padding: 24px;
        border-radius: var(--radius-md);
        box-shadow: var(--shadow-sm);
        display: flex;
        flex-direction: column;
        gap: 8px;
        transition: transform 0.2s, box-shadow 0.2s;
      }
      .stat-card:hover {
        transform: translateY(-4px);
        box-shadow: var(--shadow-md);
      }
      .stat-label {
        font-size: 0.85rem;
        color: var(--text-secondary);
        font-weight: 600;
      }
      .stat-value {
        font-size: 2.2rem;
        font-weight: 800;
        color: var(--primary);
      }
      .management-section {
        background: var(--bg-card, #ffffff);
        border: 1px solid var(--border-color);
        border-radius: var(--radius-md);
        box-shadow: var(--shadow-sm);
        overflow: hidden;
      }
      .section-header {
        padding: 20px 24px;
        border-bottom: 1px solid var(--border-color);
        display: flex;
        justify-content: space-between;
        align-items: center;
        flex-wrap: wrap;
        gap: 16px;
      }
      .section-title {
        font-size: 1.2rem;
        font-weight: 700;
      }
      .controls {
        display: flex;
        gap: 12px;
        flex-wrap: wrap;
      }
      .search-input {
        padding: 8px 16px;
        border: 1px solid var(--border-color);
        border-radius: var(--radius-sm);
        background: transparent;
        color: var(--text-primary);
        font-size: 0.9rem;
        outline: none;
        width: 240px;
      }
      .search-input:focus {
        border-color: var(--primary);
      }
      .filter-select {
        padding: 8px 12px;
        border: 1px solid var(--border-color);
        border-radius: var(--radius-sm);
        background: var(--bg-card);
        color: var(--text-primary);
        font-size: 0.9rem;
        outline: none;
        cursor: pointer;
      }
      .admin-table-wrapper {
        overflow-x: auto;
      }
      .admin-table {
        width: 100%;
        border-collapse: collapse;
        text-align: left;
        font-size: 0.95rem;
      }
      .admin-table th, .admin-table td {
        padding: 16px 24px;
        border-bottom: 1px solid var(--border-color);
      }
      .admin-table th {
        background: var(--bg-sidebar);
        font-weight: 600;
        color: var(--text-secondary);
      }
      .admin-table tr:hover {
        background: var(--primary-light);
      }
      .badge {
        display: inline-flex;
        align-items: center;
        padding: 4px 10px;
        border-radius: 20px;
        font-size: 0.8rem;
        font-weight: 600;
      }
      .badge-active {
        background: #e6fcf5;
        color: #0ca678;
      }
      .badge-pending {
        background: #fff9db;
        color: #f08c00;
      }
      .badge-rejected {
        background: #ffe3e3;
        color: #f03e3e;
      }
      .btn-group {
        display: flex;
        gap: 6px;
      }
      .btn-sm {
        padding: 6px 12px;
        border-radius: var(--radius-sm);
        font-size: 0.82rem;
        font-weight: 600;
        cursor: pointer;
        border: 1px solid transparent;
        transition: all 0.2s;
      }
      .btn-approve {
        background: var(--primary);
        color: #ffffff;
      }
      .btn-approve:hover {
        opacity: 0.9;
      }
      .btn-reject {
        background: transparent;
        border-color: var(--accent);
        color: var(--accent);
      }
      .btn-reject:hover {
        background: var(--accent-light);
      }
      .btn-suspend {
        background: transparent;
        border-color: var(--border-color);
        color: var(--text-secondary);
      }
      .btn-suspend:hover {
        background: var(--border-color);
      }
      .btn-role {
        background: transparent;
        border-color: var(--secondary);
        color: var(--secondary);
      }
      .btn-role:hover {
        background: var(--secondary-light);
      }
      .pagination {
        padding: 20px 24px;
        display: flex;
        justify-content: space-between;
        align-items: center;
        border-top: 1px solid var(--border-color);
      }
      .pagination-info {
        font-size: 0.9rem;
        color: var(--text-secondary);
      }
      .pagination-btns {
        display: flex;
        gap: 8px;
      }
      .pagination-btn {
        padding: 6px 12px;
        border: 1px solid var(--border-color);
        background: transparent;
        color: var(--text-primary);
        border-radius: var(--radius-sm);
        cursor: pointer;
      }
      .pagination-btn:disabled {
        opacity: 0.4;
        cursor: not-allowed;
      }
    `;
    document.head.appendChild(style);
  }

  const root = document.createElement('div');
  root.className = 'animate-fade-in';
  root.style.width = '100%';

  root.innerHTML = `
    <div class="admin-container">
      <div class="admin-header" style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 24px;">
        <h1 class="admin-title" style="margin: 0;">⚙️ 운영자 관리 포털</h1>
        <div style="display: flex; gap: 12px; align-items: center;">
          <button class="btn btn-secondary" id="btn-system-backup" style="height: 38px; border-color: var(--primary); color: var(--primary); font-weight: 600; font-size: 0.85rem; display: flex; align-items: center; gap: 6px;">
            💾 전체 데이터 백업
          </button>
          <button class="btn btn-secondary" id="btn-system-restore" style="height: 38px; border-color: var(--accent); color: var(--accent); font-weight: 600; font-size: 0.85rem; display: flex; align-items: center; gap: 6px;">
            ♻️ 데이터 복원 (Restore)
          </button>
          <!-- Hidden File Input for Restore Upload -->
          <input type="file" id="system-restore-file" accept=".json" style="display: none;">
        </div>
      </div>
      
      <!-- Stats Dashboard -->
      <div class="stats-grid" id="stats-container">
        <div class="stat-card">
          <span class="stat-label">👥 총 회원 수</span>
          <span class="stat-value" id="stat-total-users">-</span>
        </div>
        <div class="stat-card">
          <span class="stat-label">⏳ 승인 대기 회원</span>
          <span class="stat-value" id="stat-pending-users">-</span>
        </div>
        <div class="stat-card">
          <span class="stat-label">📖 생성 소설 프로젝트</span>
          <span class="stat-value" id="stat-total-projects">-</span>
        </div>
        <div class="stat-card">
          <span class="stat-label">✍️ 발행 에피소드 수</span>
          <span class="stat-value" id="stat-total-episodes">-</span>
        </div>
      </div>

      <!-- User Management Section -->
      <div class="management-section">
        <div class="section-header">
          <h2 class="section-title">회원 권한 및 상태 관리</h2>
          <div class="controls">
            <input type="text" class="search-input" id="admin-search-input" placeholder="이름 또는 이메일 검색...">
            <select class="filter-select" id="admin-filter-select">
              <option value="">모든 상태</option>
              <option value="pending">승인 대기</option>
              <option value="active">승인 완료</option>
              <option value="rejected">가입 거절</option>
            </select>
          </div>
        </div>

        <div class="admin-table-wrapper">
          <table class="admin-table">
            <thead>
              <tr>
                <th>ID</th>
                <th>사용자이름</th>
                <th>이메일</th>
                <th>권한</th>
                <th>상태</th>
                <th>가입일</th>
                <th>관리 액션</th>
              </tr>
            </thead>
            <tbody id="admin-users-table-body">
              <tr>
                <td colspan="7" style="text-align: center; color: var(--text-muted);">회원 목록을 불러오는 중...</td>
              </tr>
            </tbody>
          </table>
        </div>

        <div class="pagination">
          <div class="pagination-info" id="admin-pagination-info">Page 1 of 1 (Total: 0)</div>
          <div class="pagination-btns">
            <button class="pagination-btn" id="admin-prev-btn" disabled>이전</button>
            <button class="pagination-btn" id="admin-next-btn" disabled>다음</button>
          </div>
        </div>
      </div>
    </div>
  `;

  // Pagination states
  let currentPage = 1;
  const pageSize = 15;
  let totalCount = 0;

  // Bind Events on root element
  const searchInput = root.querySelector('#admin-search-input');
  const filterSelect = root.querySelector('#admin-filter-select');
  const prevBtn = root.querySelector('#admin-prev-btn');
  const nextBtn = root.querySelector('#admin-next-btn');

  // Smart backup & restore button event handlers (Phase 3)
  const backupBtn = root.querySelector('#btn-system-backup');
  const restoreBtn = root.querySelector('#btn-system-restore');
  const restoreFileInput = root.querySelector('#system-restore-file');

  backupBtn.onclick = async () => {
    showSpinner('시스템 데이터 백업을 생성하는 중...');
    try {
      const token = localStorage.getItem('access_token');
      const response = await fetch('/api/admin/backup', {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      
      if (!response.ok) throw new Error('백업 생성 실패');
      
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      
      const disposition = response.headers.get('content-disposition');
      let filename = `novel_system_backup_${new Date().toISOString().slice(0,10)}.json`;
      if (disposition && disposition.indexOf('attachment') !== -1) {
        const filenameRegex = /filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/;
        const matches = filenameRegex.exec(disposition);
        if (matches != null && matches[1]) {
          filename = matches[1].replace(/['"]/g, '');
        }
      }
      
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
      
      hideSpinner();
      showToast('💾 시스템 백업 다운로드가 완료되었습니다.', 'success');
    } catch (err) {
      hideSpinner();
      showToast(`백업 실패: ${err.message}`, 'error');
    }
  };

  restoreBtn.onclick = () => {
    restoreFileInput.click();
  };

  restoreFileInput.onchange = async (e) => {
    const file = e.target.files[0];
    if (!file) return;
    
    const conf = confirm("⚠️ 경고 [데이터 복원]\n\n정말로 전체 데이터를 복구하시겠습니까?\n기존에 생성된 소설 프로젝트, 에피소드, 씬, 캐릭터, 고증 참고자료는 전부 삭제되고 복구 파일의 내용으로 완전히 대체됩니다. 이 작업은 되돌릴 수 없습니다!");
    if (!conf) {
      restoreFileInput.value = '';
      return;
    }
    
    showSpinner('시스템 데이터를 복원하고 데이터베이스를 재구축하는 중...');
    try {
      const formData = new FormData();
      formData.append('file', file);
      
      const token = localStorage.getItem('access_token');
      const response = await fetch('/api/admin/restore', {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}` },
        body: formData
      });
      
      const resJson = await response.json();
      if (!response.ok) throw new Error(resJson.detail || '복원 작업 중 서버 오류 발생');
      
      hideSpinner();
      showToast('♻️ 전체 데이터베이스 복원이 성공적으로 완료되었습니다!', 'success');
      
      setTimeout(() => {
        window.location.reload();
      }, 1500);
    } catch (err) {
      hideSpinner();
      showToast(`복원 실패: ${err.message}`, 'error');
      restoreFileInput.value = '';
    }
  };

  // Search input debounce/trigger
  let searchTimeout;
  searchInput.addEventListener('input', () => {
    clearTimeout(searchTimeout);
    searchTimeout = setTimeout(() => {
      currentPage = 1;
      loadUsers();
    }, 400);
  });

  filterSelect.addEventListener('change', () => {
    currentPage = 1;
    loadUsers();
  });

  prevBtn.addEventListener('click', () => {
    if (currentPage > 1) {
      currentPage--;
      loadUsers();
    }
  });

  nextBtn.addEventListener('click', () => {
    if (currentPage * pageSize < totalCount) {
      currentPage++;
      loadUsers();
    }
  });

  // Load functions
  async function loadStats() {
    try {
      const stats = await api.get('/admin/stats');
      root.querySelector('#stat-total-users').textContent = stats.total_users;
      root.querySelector('#stat-pending-users').textContent = stats.pending_users;
      root.querySelector('#stat-total-projects').textContent = stats.total_projects;
      root.querySelector('#stat-total-episodes').textContent = stats.total_episodes;
    } catch (e) {
      console.error('Failed to load admin stats:', e);
    }
  }

  async function loadUsers() {
    const tableBody = root.querySelector('#admin-users-table-body');
    const searchVal = searchInput.value;
    const filterVal = filterSelect.value;

    try {
      tableBody.innerHTML = `<tr><td colspan="7" style="text-align: center; color: var(--text-muted);">회원 정보를 조회하는 중...</td></tr>`;

      let queryPath = `/admin/users?page=${currentPage}&size=${pageSize}`;
      if (searchVal) queryPath += `&search=${encodeURIComponent(searchVal)}`;
      if (filterVal) queryPath += `&status_filter=${filterVal}`;

      const res = await api.get(queryPath);
      totalCount = res.total;
      
      // Update pagination UI
      const totalPages = Math.ceil(totalCount / pageSize) || 1;
      root.querySelector('#admin-pagination-info').textContent = `페이지 ${currentPage} / ${totalPages} (총 ${totalCount}명)`;
      prevBtn.disabled = currentPage <= 1;
      nextBtn.disabled = currentPage >= totalPages;

      if (res.items.length === 0) {
        tableBody.innerHTML = `<tr><td colspan="7" style="text-align: center; color: var(--text-muted);">조건에 부합하는 회원이 없습니다.</td></tr>`;
        return;
      }

      tableBody.innerHTML = res.items.map(user => {
        let statusBadge = '';
        if (user.is_active) {
          statusBadge = '<span class="badge badge-active">승인 완료</span>';
        } else if (user.rejected_at) {
          statusBadge = '<span class="badge badge-rejected">가입 거절</span>';
        } else {
          statusBadge = '<span class="badge badge-pending">승인 대기</span>';
        }

        const roleText = user.is_admin ? '운영 관리자' : '일반 작가';
        const formattedDate = new Date(user.created_at).toLocaleDateString();

        // Control Buttons
        let actionButtons = '';
        const isSelf = user.id === me.id;

        if (isSelf) {
          actionButtons = `<span style="font-size: 0.85rem; color: var(--text-muted);">로그인 본인</span>`;
        } else {
          if (!user.is_active && !user.rejected_at) {
            actionButtons += `
              <button class="btn-sm btn-approve" data-id="${user.id}" data-action="approve">승인</button>
              <button class="btn-sm btn-reject" data-id="${user.id}" data-action="reject">거절</button>
            `;
          } else if (user.rejected_at) {
            actionButtons += `
              <button class="btn-sm btn-approve" data-id="${user.id}" data-action="approve">승인</button>
            `;
          } else {
            actionButtons += `
              <button class="btn-sm btn-suspend" data-id="${user.id}" data-action="suspend">정지</button>
            `;
          }

          const toggleRoleText = user.is_admin ? '작가로 강등' : '어드민 승격';
          const nextRoleAdmin = !user.is_admin;
          actionButtons += `
            <button class="btn-sm btn-role" data-id="${user.id}" data-role="${nextRoleAdmin}">${toggleRoleText}</button>
          `;
        }

        return `
          <tr>
            <td>${user.id}</td>
            <td style="font-weight: 600;">${user.username}</td>
            <td>${user.email || '-'}</td>
            <td>${roleText}</td>
            <td>${statusBadge}</td>
            <td>${formattedDate}</td>
            <td>
              <div class="btn-group">
                ${actionButtons}
              </div>
            </td>
          </tr>
        `;
      }).join('');

      // Bind button events
      tableBody.querySelectorAll('button[data-action]').forEach(btn => {
        btn.addEventListener('click', async () => {
          const id = btn.getAttribute('data-id');
          const action = btn.getAttribute('data-action');
          if (confirm(`해당 회원을 정말로 ${action === 'approve' ? '승인' : action === 'reject' ? '거절' : '정지'}하시겠습니까?`)) {
            try {
              await api.patch(`/admin/users/${id}/status`, { action });
              loadStats();
              loadUsers();
            } catch (err) {
              alert(`회원 상태 수정 실패: ${err.message}`);
            }
          }
        });
      });

      tableBody.querySelectorAll('button[data-role]').forEach(btn => {
        btn.addEventListener('click', async () => {
          const id = btn.getAttribute('data-id');
          const is_admin = btn.getAttribute('data-role') === 'true';
          if (confirm(`해당 회원의 직급을 ${is_admin ? '운영 관리자로 승격' : '일반 작가로 강등'}하시겠습니까?`)) {
            try {
              await api.patch(`/admin/users/${id}/role`, { is_admin });
              loadUsers();
            } catch (err) {
              alert(`직급 수정 실패: ${err.message}`);
            }
          }
        });
      });

    } catch (e) {
      tableBody.innerHTML = `<tr><td colspan="7" style="text-align: center; color: var(--accent);">회원 정보를 불러오지 못했습니다: ${e.message}</td></tr>`;
    }
  }

  // Initial Run
  loadStats();
  loadUsers();

  return root;
}
