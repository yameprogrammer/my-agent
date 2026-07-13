// Project Detail Page Scaffold
export async function renderProject(params) {
  const container = document.createElement('div');
  container.className = 'glass-card animate-fade-in';
  container.style.padding = '32px';
  
  container.innerHTML = `
    <h2 style="margin-bottom: 16px; font-family: var(--font-heading);">프로젝트 상세</h2>
    <p style="color: var(--text-secondary);">프로젝트 ID: ${params.id}</p>
  `;
  return container;
}
