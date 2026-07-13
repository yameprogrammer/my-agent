import './style.css';
import { router } from './utils/router.js';
import { renderSidebar } from './components/sidebar.js';
import { renderLogin } from './pages/login.js';
import { renderDashboard } from './pages/dashboard.js';
import { renderProject } from './pages/project.js';
import { renderWritingMonitor } from './pages/writing-monitor.js';

// Setup routes
router.addRoute('/login', renderLogin, false);
router.addRoute('/', renderDashboard, true);
router.addRoute('/projects/:id', renderProject, true);
router.addRoute('/projects/:id/episodes/:eid/write', renderWritingMonitor, true);

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
