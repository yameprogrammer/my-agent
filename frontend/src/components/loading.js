// Loading components including fullscreen spinner and skeletal loaders
let spinnerOverlay = null;

export function showSpinner(message = '로딩 중...') {
  if (spinnerOverlay) {
    spinnerOverlay.querySelector('.spinner-text').textContent = message;
    return;
  }
  
  spinnerOverlay = document.createElement('div');
  spinnerOverlay.id = 'spinner-overlay';
  
  const style = document.createElement('style');
  style.textContent = `
    #spinner-overlay {
      position: fixed;
      top: 0;
      left: 0;
      width: 100vw;
      height: 100vh;
      background: rgba(15, 23, 42, 0.6);
      backdrop-filter: blur(4px);
      -webkit-backdrop-filter: blur(4px);
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      gap: 16px;
      z-index: 10000;
      color: #ffffff;
      opacity: 0;
      transition: opacity 0.25s ease;
    }
    #spinner-overlay.show {
      opacity: 1;
    }
    .spinner-ring {
      width: 48px;
      height: 48px;
      border: 4px solid rgba(255, 255, 255, 0.1);
      border-left-color: var(--primary, #8b5cf6);
      border-radius: 50%;
      animation: spin 0.8s linear infinite;
    }
    .spinner-text {
      font-family: var(--font-heading, sans-serif);
      font-weight: 500;
      font-size: 1.1rem;
      text-shadow: 0 2px 4px rgba(0,0,0,0.2);
    }
  `;
  document.head.appendChild(style);
  
  spinnerOverlay.innerHTML = `
    <div class="spinner-ring"></div>
    <div class="spinner-text">${message}</div>
  `;
  
  document.body.appendChild(spinnerOverlay);
  
  requestAnimationFrame(() => {
    spinnerOverlay.classList.add('show');
  });
}

export function hideSpinner() {
  if (!spinnerOverlay) return;
  spinnerOverlay.classList.remove('show');
  setTimeout(() => {
    if (spinnerOverlay) {
      spinnerOverlay.remove();
      spinnerOverlay = null;
    }
  }, 250);
}

export function createSkeleton(width = '100%', height = '20px', count = 1) {
  const container = document.createElement('div');
  container.className = 'skeleton-group';
  container.style.display = 'flex';
  container.style.flexDirection = 'column';
  container.style.gap = '8px';
  container.style.width = '100%';
  
  // Inject style once
  if (!document.getElementById('skeleton-styles')) {
    const style = document.createElement('style');
    style.id = 'skeleton-styles';
    style.textContent = `
      .skeleton-loader {
        background: linear-gradient(90deg, var(--border-color, #e2e8f0) 25%, var(--primary-light, #f5f3ff) 50%, var(--border-color, #e2e8f0) 75%);
        background-size: 200% 100%;
        animation: loading-skeleton 1.5s infinite;
      }
      @keyframes loading-skeleton {
        0% { background-position: 200% 0; }
        100% { background-position: -200% 0; }
      }
    `;
    document.head.appendChild(style);
  }
  
  for (let i = 0; i < count; i++) {
    const el = document.createElement('div');
    el.className = 'skeleton-loader';
    el.style.width = width;
    el.style.height = height;
    el.style.borderRadius = 'var(--radius-sm, 8px)';
    container.appendChild(el);
  }
  
  return container;
}
