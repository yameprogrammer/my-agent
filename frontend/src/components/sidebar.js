// Navigation sidebar component with theme toggle and user profile card
import { getTheme, setTheme } from '../utils/state.js';
import { logout, getCurrentUser, isAuthenticated } from '../utils/auth.js';

export function renderSidebar() {
  const user = getCurrentUser();
  const isAuth = isAuthenticated();
  
  if (!user || !isAuth) {
    // If not authenticated, remove sidebar if exists
    const existing = document.getElementById('app-sidebar');
    if (existing) existing.remove();
    return;
  }
  
  let sidebar = document.getElementById('app-sidebar');
  if (!sidebar) {
    sidebar = document.createElement('aside');
    sidebar.id = 'app-sidebar';
    
    // Inject style once
    if (!document.getElementById('sidebar-styles')) {
      const style = document.createElement('style');
      style.id = 'sidebar-styles';
      style.textContent = `
        #app-sidebar {
          width: var(--sidebar-width, 260px);
          background: var(--bg-sidebar);
          border-right: 1px solid var(--border-color);
          display: flex;
          flex-direction: column;
          height: 100vh;
          position: fixed;
          top: 0;
          left: 0;
          z-index: 100;
          transition: transform var(--transition-normal), background-color var(--transition-normal);
        }
        .sidebar-header {
          padding: 24px;
          display: flex;
          align-items: center;
          gap: 12px;
          border-bottom: 1px solid var(--border-color);
        }
        .logo-icon {
          font-size: 1.8rem;
        }
        .logo-text {
          font-family: var(--font-heading);
          font-weight: 700;
          font-size: 1.15rem;
          background: linear-gradient(135deg, var(--primary), var(--secondary));
          -webkit-background-clip: text;
          -webkit-text-fill-color: transparent;
        }
        .sidebar-menu {
          flex: 1;
          padding: 24px 16px;
          display: flex;
          flex-direction: column;
          gap: 8px;
          overflow-y: auto;
        }
        .menu-item {
          display: flex;
          align-items: center;
          gap: 12px;
          padding: 10px 16px;
          border-radius: var(--radius-sm);
          color: var(--text-secondary);
          font-weight: 500;
          font-size: 0.95rem;
          transition: all var(--transition-fast);
          cursor: pointer;
        }
        .menu-item:hover, .menu-item.active {
          color: var(--primary);
          background-color: var(--primary-light);
        }
        .menu-item.active {
          font-weight: 600;
        }
        .sidebar-footer {
          padding: 16px;
          border-top: 1px solid var(--border-color);
          display: flex;
          flex-direction: column;
          gap: 12px;
        }
        .user-card {
          display: flex;
          align-items: center;
          gap: 12px;
          padding: 8px;
          border-radius: var(--radius-sm);
        }
        .user-avatar {
          width: 36px;
          height: 36px;
          border-radius: 50%;
          background: var(--primary-light);
          color: var(--primary);
          display: flex;
          align-items: center;
          justify-content: center;
          font-weight: 700;
          font-size: 1rem;
        }
        .user-info {
          flex: 1;
          min-width: 0;
        }
        .user-name {
          font-weight: 600;
          font-size: 0.9rem;
          white-space: nowrap;
          overflow: hidden;
          text-overflow: ellipsis;
        }
        .user-role {
          font-size: 0.75rem;
          color: var(--text-muted);
        }
        .sidebar-actions {
          display: flex;
          justify-content: space-between;
          align-items: center;
          gap: 8px;
        }
        .theme-toggle-btn {
          flex: 1;
          padding: 8px;
          border-radius: var(--radius-sm);
          border: 1px solid var(--border-color);
          background: transparent;
          color: var(--text-secondary);
          cursor: pointer;
          font-size: 0.85rem;
          font-weight: 500;
          display: flex;
          align-items: center;
          justify-content: center;
          gap: 6px;
          transition: all var(--transition-fast);
        }
        .theme-toggle-btn:hover {
          background: var(--primary-light);
          color: var(--primary);
        }
        .logout-btn {
          padding: 8px;
          border-radius: var(--radius-sm);
          border: 1px solid transparent;
          background: transparent;
          color: var(--text-muted);
          cursor: pointer;
          transition: all var(--transition-fast);
          display: flex;
          align-items: center;
          justify-content: center;
        }
        .logout-btn:hover {
          color: var(--accent);
          background: var(--accent-light);
        }
        
        /* Mobile toggle styles */
        .mobile-header {
          display: none;
          height: var(--header-height);
          background: var(--bg-sidebar);
          border-bottom: 1px solid var(--border-color);
          padding: 0 16px;
          align-items: center;
          justify-content: space-between;
          position: fixed;
          top: 0;
          left: 0;
          width: 100vw;
          z-index: 90;
        }
        .menu-toggle {
          background: none;
          border: none;
          font-size: 1.5rem;
          color: var(--text-primary);
          cursor: pointer;
        }
        
        @media (max-width: 1024px) {
          #app-sidebar {
            transform: translateX(-100%);
          }
          #app-sidebar.open {
            transform: translateX(0);
          }
          .mobile-header {
            display: flex;
          }
          #app-layout {
            padding-top: var(--header-height);
          }
        }
      `;
      document.head.appendChild(style);
    }
    
    document.body.appendChild(sidebar);
  }
  
  // Render sidebar HTML
  const currentTheme = getTheme();
  const initial = user.username ? user.username.charAt(0).toUpperCase() : 'U';
  
  sidebar.innerHTML = `
    <div class="sidebar-header">
      <span class="logo-icon">📖</span>
      <span class="logo-text">소설 집필 에이전트</span>
    </div>
    <nav class="sidebar-menu">
      <div class="menu-item ${(!window.location.hash || window.location.hash === '#/') ? 'active' : ''}" data-path="#/">
        <span>🏠</span>
        <span>프로젝트 대시보드</span>
      </div>
      ${user.is_admin ? `
      <div class="menu-item ${window.location.hash.startsWith('#/admin') ? 'active' : ''}" data-path="#/admin">
        <span>⚙️</span>
        <span>운영 관리 도구</span>
      </div>
      ` : ''}
    </nav>
    <div class="sidebar-footer">
      <div class="user-card">
        <div class="user-avatar">${initial}</div>
        <div class="user-info">
          <div class="user-name">${user.username}</div>
          <div class="user-role">${user.is_admin ? '관리자' : '작가'}</div>
        </div>
      </div>
      <div class="sidebar-actions">
        <button class="theme-toggle-btn">
          <span>${currentTheme === 'dark' ? '☀️ 라이트 모드' : '🌙 다크 모드'}</span>
        </button>
        <button class="logout-btn" title="로그아웃">
          <span>🚪</span>
        </button>
      </div>
    </div>
  `;
  
  // Create mobile header if not exists
  let mobileHeader = document.getElementById('app-mobile-header');
  if (!mobileHeader) {
    mobileHeader = document.createElement('div');
    mobileHeader.id = 'app-mobile-header';
    mobileHeader.className = 'mobile-header';
    mobileHeader.innerHTML = `
      <button class="menu-toggle">☰</button>
      <span class="logo-text">소설 집필 에이전트</span>
      <div style="width: 24px;"></div> <!-- Spacer -->
    `;
    document.body.appendChild(mobileHeader);
    
    // Toggle event
    mobileHeader.querySelector('.menu-toggle').addEventListener('click', (e) => {
      e.stopPropagation();
      sidebar.classList.toggle('open');
    });
    
    // Dismiss mobile sidebar when clicking elsewhere
    document.addEventListener('click', () => {
      sidebar.classList.remove('open');
    });
    sidebar.addEventListener('click', (e) => {
      e.stopPropagation();
    });
  }
  
  // Bind navigation links
  sidebar.querySelectorAll('.menu-item').forEach(item => {
    item.addEventListener('click', () => {
      const path = item.getAttribute('data-path');
      if (path) {
        window.location.hash = path;
        sidebar.classList.remove('open');
      }
    });
  });
  
  // Theme toggle binding
  sidebar.querySelector('.theme-toggle-btn').addEventListener('click', () => {
    const nextTheme = getTheme() === 'dark' ? 'light' : 'dark';
    setTheme(nextTheme);
    renderSidebar(); // Re-render to update toggle text
  });
  
  // Logout binding
  sidebar.querySelector('.logout-btn').addEventListener('click', () => {
    logout();
  });
}
