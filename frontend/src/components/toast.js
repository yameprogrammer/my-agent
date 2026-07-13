// Toast notification component for dynamic alerts
let toastContainer = null;

function initContainer() {
  if (toastContainer) return;
  toastContainer = document.createElement('div');
  toastContainer.id = 'toast-container';
  
  const style = document.createElement('style');
  style.textContent = `
    #toast-container {
      position: fixed;
      bottom: 24px;
      right: 24px;
      display: flex;
      flex-direction: column;
      gap: 12px;
      z-index: 9999;
      pointer-events: none;
      max-width: 380px;
      width: calc(100vw - 48px);
    }
    .toast-item {
      padding: 12px 20px;
      border-radius: var(--radius-sm, 8px);
      background: var(--bg-sidebar, #ffffff);
      color: var(--text-primary, #0f172a);
      border: 1px solid var(--border-color, #e2e8f0);
      box-shadow: var(--shadow-lg, 0 10px 15px -3px rgba(0,0,0,0.1));
      display: flex;
      align-items: center;
      gap: 12px;
      font-size: 0.9rem;
      font-weight: 500;
      pointer-events: auto;
      transform: translateY(20px);
      opacity: 0;
      transition: transform 0.3s cubic-bezier(0.175, 0.885, 0.32, 1.275), opacity 0.3s ease;
    }
    .toast-item.show {
      transform: translateY(0);
      opacity: 1;
    }
    .toast-icon {
      font-size: 1.2rem;
      flex-shrink: 0;
    }
    .toast-success {
      border-left: 4px solid var(--secondary, #0d9488);
    }
    .toast-error {
      border-left: 4px solid var(--accent, #f43f5e);
    }
    .toast-info {
      border-left: 4px solid var(--primary, #6366f1);
    }
  `;
  document.head.appendChild(style);
  document.body.appendChild(toastContainer);
}

export function showToast(message, type = 'info', duration = 3000) {
  initContainer();
  
  const toast = document.createElement('div');
  toast.className = `toast-item toast-${type}`;
  
  let icon = 'ℹ️';
  if (type === 'success') icon = '✅';
  else if (type === 'error') icon = '❌';
  
  toast.innerHTML = `
    <span class="toast-icon">${icon}</span>
    <span class="toast-message">${message}</span>
  `;
  
  toastContainer.appendChild(toast);
  
  // Trigger animation next frame
  requestAnimationFrame(() => {
    toast.classList.add('show');
  });
  
  setTimeout(() => {
    toast.classList.remove('show');
    toast.style.transform = 'translateY(-20px)';
    toast.style.opacity = '0';
    setTimeout(() => {
      toast.remove();
    }, 3000);
  }, duration);
}
