// Hash-based SPA Router for client-side navigation
import { isAuthenticated } from './auth.js';

class Router {
  constructor() {
    this.routes = [];
    this.container = null;
    this.currentView = null;
    
    window.addEventListener('hashchange', () => this.handleRoute());
  }

  init(container) {
    this.container = container;
    this.handleRoute();
  }

  addRoute(path, renderFn, requiresAuth = true) {
    // Convert path template like '/projects/:id' to regex
    // e.g. /projects/:id -> ^#/projects/([^/]+)$
    const paramNames = [];
    const pattern = path
      .replace(/:([a-zA-Z0-9_]+)/g, (_, name) => {
        paramNames.push(name);
        return '([^/]+)';
      })
      .replace(/\//g, '\\/');
    
    const regex = new RegExp(`^#${pattern}$`);
    
    this.routes.push({
      path,
      regex,
      paramNames,
      renderFn,
      requiresAuth
    });
  }

  navigate(path) {
    window.location.hash = path;
  }

  handleRoute() {
    const hash = window.location.hash || '#/';
    
    // Auth Guard
    const isAuth = isAuthenticated();
    
    // Special handling for login route
    if (hash === '#/login' && isAuth) {
      this.navigate('/');
      return;
    }
    
    // Find matching route
    let match = null;
    for (const route of this.routes) {
      const result = hash.match(route.regex);
      if (result) {
        const params = {};
        route.paramNames.forEach((name, index) => {
          params[name] = result[index + 1];
        });
        match = { route, params };
        break;
      }
    }
    
    if (!match) {
      console.warn(`No route matches: ${hash}. Redirecting to dashboard.`);
      this.navigate('/');
      return;
    }
    
    // Auth redirection
    if (match.route.requiresAuth && !isAuth) {
      console.log('Authentication required. Redirecting to login.');
      this.navigate('/login');
      return;
    }
    
    // Render view
    this.render(match.route.renderFn, match.params);
  }

  async render(renderFn, params) {
    if (!this.container) return;
    
    // Dispatch destroy event to existing elements to cleanup WebSockets etc.
    const currentView = this.container.firstElementChild;
    if (currentView) {
      try {
        currentView.dispatchEvent(new CustomEvent('destroyed'));
      } catch (err) {
        console.error('Error during view destruction cleanup:', err);
      }
    }
    
    // Clear container
    this.container.innerHTML = '';
    
    // Apply slide/fade transition wrapper
    const viewWrapper = document.createElement('div');
    viewWrapper.className = 'animate-fade-in';
    viewWrapper.style.width = '100%';
    viewWrapper.style.height = '100%';
    this.container.appendChild(viewWrapper);
    
    try {
      // Execute the render function which should append HTML or modify viewWrapper
      const viewElement = await renderFn(params);
      if (viewElement) {
        if (viewElement instanceof HTMLElement) {
          viewWrapper.appendChild(viewElement);
        } else if (typeof viewElement === 'string') {
          viewWrapper.innerHTML = viewElement;
        }
      }
    } catch (e) {
      console.error('Routing render error:', e);
      viewWrapper.innerHTML = `
        <div style="padding: 40px; text-align: center; color: var(--accent);">
          <h2>⚠️ 페이지 로드 오류</h2>
          <p style="margin-top: 8px;">${e.message || '알 수 없는 오류가 발생했습니다.'}</p>
          <button class="btn btn-secondary" style="margin-top: 16px;" onclick="window.location.reload()">새로고침</button>
        </div>
      `;
    }
  }
}

export const router = new Router();
