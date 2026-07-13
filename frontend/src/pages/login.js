// Login Page Scaffold
export async function renderLogin(params) {
  const container = document.createElement('div');
  container.className = 'glass-card animate-fade-in';
  container.style.maxWidth = '400px';
  container.style.margin = '100px auto';
  container.style.padding = '32px';
  
  container.innerHTML = `
    <h2 style="margin-bottom: 24px; text-align: center; font-family: var(--font-heading);">로그인</h2>
    <p style="text-align: center; color: var(--text-secondary);">인프라 레이어 및 디자인 시스템 적용 중입니다.</p>
  `;
  return container;
}
