import './style.css';
import { router } from './utils/router.js';
import { renderSidebar } from './components/sidebar.js';
import { renderLogin } from './pages/login.js';
import { renderDashboard } from './pages/dashboard.js';
import { renderProject } from './pages/project.js';
import { renderWritingMonitor } from './pages/writing-monitor.js';
import { renderAdmin } from './pages/admin.js';

// Setup routes
router.addRoute('/login', renderLogin, false);
router.addRoute('/', renderDashboard, true);
router.addRoute('/projects/:id', renderProject, true);
router.addRoute('/projects/:id/episodes/:eid/write', renderWritingMonitor, true);
router.addRoute('/admin', renderAdmin, true);

// Initialize application on DOMContentLoaded
document.addEventListener('DOMContentLoaded', () => {
  const mainContent = document.getElementById('main-content');
  
  // Set up auth listeners to refresh sidebar on state changes
  window.addEventListener('hashchange', () => {
    renderSidebar();
    updateMainLayoutSpacing();
  });
  
  // Initial render setup
  renderSidebar();
  router.init(mainContent);
  updateMainLayoutSpacing();

  // 2분(120,000ms)마다 백그라운드 Keep-Alive 핑을 발송하여 ngrok 터널 및 세션 유실 차단
  setInterval(async () => {
    const { isAuthenticated } = await import('./utils/auth.js');
    if (isAuthenticated()) {
      try {
        const { api } = await import('./api/client.js');
        await api.get('/users/me');
      } catch (e) {
        console.warn('백그라운드 세션 핑 실패:', e);
      }
    }
  }, 120000);
});

// Dynamic layout padding based on sidebar presence
function updateMainLayoutSpacing() {
  const sidebar = document.getElementById('app-sidebar');
  const layout = document.getElementById('app-layout');
  if (layout) {
    if (sidebar) {
      layout.style.paddingLeft = 'var(--sidebar-width)';
    } else {
      layout.style.paddingLeft = '0';
    }
  }
}
