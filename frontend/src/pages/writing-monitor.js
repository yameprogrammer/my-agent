// Writing Monitor Page Scaffold
export async function renderWritingMonitor(params) {
  const container = document.createElement('div');
  container.className = 'glass-card animate-fade-in';
  container.style.padding = '32px';
  
  container.innerHTML = `
    <h2 style="margin-bottom: 16px; font-family: var(--font-heading);">실시간 집필 모니터</h2>
    <p style="color: var(--text-secondary);">프로젝트 ID: ${params.id}, 에피소드 ID: ${params.eid}</p>
  `;
  return container;
}
