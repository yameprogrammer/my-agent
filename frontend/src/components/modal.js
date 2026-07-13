// Common Modal dialogue component

export function createModal({
  title,
  content,
  onConfirm = null,
  onCancel = null,
  confirmText = '확인',
  cancelText = '취소',
  showFooter = true,
  isDangerous = false
}) {
  const modalWrapper = document.createElement('div');
  modalWrapper.className = 'modal-backdrop';
  
  // Inject style once
  if (!document.getElementById('modal-styles')) {
    const style = document.createElement('style');
    style.id = 'modal-styles';
    style.textContent = `
      .modal-backdrop {
        position: fixed;
        top: 0;
        left: 0;
        width: 100vw;
        height: 100vh;
        background: rgba(15, 23, 42, 0.4);
        backdrop-filter: blur(8px);
        -webkit-backdrop-filter: blur(8px);
        display: flex;
        align-items: center;
        justify-content: center;
        z-index: 9900;
        opacity: 0;
        transition: opacity 0.2s ease;
      }
      .modal-backdrop.show {
        opacity: 1;
      }
      .modal-container {
        width: 480px;
        max-width: calc(100vw - 32px);
        background: var(--bg-sidebar, #ffffff);
        border: 1px solid var(--glass-border, rgba(255, 255, 255, 0.4));
        border-radius: var(--radius-md, 12px);
        box-shadow: var(--shadow-lg, 0 10px 15px -3px rgba(0,0,0,0.1));
        display: flex;
        flex-direction: column;
        overflow: hidden;
        transform: translateY(20px);
        transition: transform 0.2s cubic-bezier(0.16, 1, 0.3, 1);
        color: var(--text-primary);
      }
      .modal-backdrop.show .modal-container {
        transform: translateY(0);
      }
      .modal-header {
        padding: 20px 24px;
        border-bottom: 1px solid var(--border-color, #e2e8f0);
        display: flex;
        justify-content: space-between;
        align-items: center;
      }
      .modal-title {
        font-family: var(--font-heading, sans-serif);
        font-size: 1.2rem;
        font-weight: 600;
      }
      .modal-close {
        background: none;
        border: none;
        font-size: 1.5rem;
        cursor: pointer;
        color: var(--text-secondary);
        display: flex;
        align-items: center;
        justify-content: center;
        line-height: 1;
        width: 28px;
        height: 28px;
        border-radius: 50%;
        transition: background 0.15s;
      }
      .modal-close:hover {
        background: var(--primary-light, #f5f3ff);
        color: var(--primary);
      }
      .modal-content {
        padding: 24px;
        font-size: 0.95rem;
        color: var(--text-secondary);
        overflow-y: auto;
        max-height: 60vh;
      }
      .modal-footer {
        padding: 16px 24px;
        border-top: 1px solid var(--border-color, #e2e8f0);
        display: flex;
        justify-content: flex-end;
        gap: 12px;
        background: var(--bg-app, #f8fafc);
      }
    `;
    document.head.appendChild(style);
  }
  
  const contentHtml = content instanceof HTMLElement ? '' : content;
  
  modalWrapper.innerHTML = `
    <div class="modal-container">
      <div class="modal-header">
        <h3 class="modal-title">${title}</h3>
        <button class="modal-close">&times;</button>
      </div>
      <div class="modal-content">${contentHtml}</div>
      ${showFooter ? `
        <div class="modal-footer">
          <button class="btn btn-secondary modal-cancel-btn">${cancelText}</button>
          <button class="btn ${isDangerous ? 'btn-danger' : 'btn-primary'} modal-confirm-btn">${confirmText}</button>
        </div>
      ` : ''}
    </div>
  `;
  
  if (content instanceof HTMLElement) {
    modalWrapper.querySelector('.modal-content').appendChild(content);
  }
  
  const closeBtn = modalWrapper.querySelector('.modal-close');
  const cancelBtn = modalWrapper.querySelector('.modal-cancel-btn');
  const confirmBtn = modalWrapper.querySelector('.modal-confirm-btn');
  
  function dismiss() {
    modalWrapper.classList.remove('show');
    setTimeout(() => {
      modalWrapper.remove();
    }, 200);
  }
  
  closeBtn.addEventListener('click', () => {
    if (onCancel) onCancel();
    dismiss();
  });
  
  if (cancelBtn) {
    cancelBtn.addEventListener('click', () => {
      if (onCancel) onCancel();
      dismiss();
    });
  }
  
  if (confirmBtn) {
    confirmBtn.addEventListener('click', () => {
      let preventDismiss = false;
      if (onConfirm) {
        // If onConfirm returns false, don't dismiss the modal
        preventDismiss = onConfirm(dismiss) === false;
      }
      if (!preventDismiss) {
        dismiss();
      }
    });
  }
  
  // Click backdrop to dismiss
  modalWrapper.addEventListener('click', (e) => {
    if (e.target === modalWrapper) {
      if (onCancel) onCancel();
      dismiss();
    }
  });
  
  document.body.appendChild(modalWrapper);
  
  // Trigger animations
  requestAnimationFrame(() => {
    modalWrapper.classList.add('show');
  });
  
  return dismiss;
}
