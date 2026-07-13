// Login and Registration Page
import { login, register } from '../utils/auth.js';
import { showToast } from '../components/toast.js';
import { router } from '../utils/router.js';

export async function renderLogin() {
  const container = document.createElement('div');
  container.className = 'glass-card animate-fade-in';
  container.style.maxWidth = '460px';
  container.style.margin = '80px auto';
  container.style.padding = '40px 32px';
  container.style.borderRadius = 'var(--radius-lg)';

  let isRegisterMode = false;

  function updateView() {
    if (isRegisterMode) {
      container.innerHTML = `
        <div style="text-align: center; margin-bottom: 32px;">
          <span style="font-size: 3rem;">📝</span>
          <h2 style="font-family: var(--font-heading); font-size: 1.75rem; margin-top: 16px; color: var(--text-primary);">작가 등록</h2>
          <p style="color: var(--text-secondary); font-size: 0.9rem; margin-top: 8px;">소설 집필 에이전틱 머신에 합류하세요</p>
        </div>
        
        <form id="auth-form">
          <div class="form-group">
            <label class="form-label" for="username">사용자명</label>
            <input class="form-control" type="text" id="username" placeholder="3자 이상 입력하세요" required minlength="3">
          </div>
          
          <div class="form-group">
            <label class="form-label" for="email">이메일 (선택)</label>
            <input class="form-control" type="email" id="email" placeholder="email@example.com">
          </div>
          
          <div class="form-group" style="margin-bottom: 24px;">
            <label class="form-label" for="password">비밀번호</label>
            <input class="form-control" type="password" id="password" placeholder="6자 이상 입력하세요" required minlength="6">
          </div>
          
          <div id="error-message" style="color: var(--accent); font-size: 0.85rem; margin-bottom: 16px; min-height: 20px; display: none;"></div>
          
          <button class="btn btn-primary" type="submit" style="width: 100%; height: 48px;">가입 신청</button>
        </form>
        
        <div style="text-align: center; margin-top: 24px; font-size: 0.9rem;">
          <span style="color: var(--text-secondary);">이미 계정이 있으신가요?</span>
          <a href="#" id="toggle-auth" style="margin-left: 8px; font-weight: 600;">로그인하기</a>
        </div>
      `;
    } else {
      container.innerHTML = `
        <div style="text-align: center; margin-bottom: 32px;">
          <span style="font-size: 3rem;">📖</span>
          <h2 style="font-family: var(--font-heading); font-size: 1.75rem; margin-top: 16px; color: var(--text-primary);">에이전트 집필실</h2>
          <p style="color: var(--text-secondary); font-size: 0.9rem; margin-top: 8px;">소설 집필 에이전틱 머신</p>
        </div>
        
        <form id="auth-form">
          <div class="form-group">
            <label class="form-label" for="username">사용자명</label>
            <input class="form-control" type="text" id="username" placeholder="사용자명을 입력하세요" required>
          </div>
          
          <div class="form-group" style="margin-bottom: 24px;">
            <label class="form-label" for="password">비밀번호</label>
            <input class="form-control" type="password" id="password" placeholder="비밀번호를 입력하세요" required>
          </div>
          
          <div id="error-message" style="color: var(--accent); font-size: 0.85rem; margin-bottom: 16px; min-height: 20px; display: none;"></div>
          
          <button class="btn btn-primary" type="submit" style="width: 100%; height: 48px;">로그인</button>
        </form>
        
        <div style="text-align: center; margin-top: 24px; font-size: 0.9rem;">
          <span style="color: var(--text-secondary);">처음이신가요?</span>
          <a href="#" id="toggle-auth" style="margin-left: 8px; font-weight: 600;">작가 가입 신청</a>
        </div>
      `;
    }

    // Bind event listeners
    container.querySelector('#toggle-auth').addEventListener('click', (e) => {
      e.preventDefault();
      isRegisterMode = !isRegisterMode;
      updateView();
    });

    container.querySelector('#auth-form').addEventListener('submit', async (e) => {
      e.preventDefault();
      const username = container.querySelector('#username').value.trim();
      const password = container.querySelector('#password').value;
      const errorDiv = container.querySelector('#error-message');
      
      errorDiv.style.display = 'none';
      errorDiv.textContent = '';
      
      const submitBtn = container.querySelector('button[type="submit"]');
      const originalBtnText = submitBtn.textContent;
      submitBtn.disabled = true;
      submitBtn.textContent = '처리 중...';
      
      try {
        if (isRegisterMode) {
          const email = container.querySelector('#email').value.trim() || undefined;
          await register(username, password, email);
          
          // Successful registration -> Show telegram approval alert
          container.innerHTML = `
            <div style="text-align: center; padding: 20px 0;">
              <span style="font-size: 4rem; display: block; margin-bottom: 24px; animation: bounce 2s infinite;">✉️</span>
              <h2 style="font-family: var(--font-heading); font-size: 1.5rem; color: var(--text-primary); margin-bottom: 16px;">가입 신청 완료</h2>
              <p style="color: var(--text-secondary); line-height: 1.6; margin-bottom: 24px; font-size: 0.95rem;">
                등록 신청이 정상적으로 완료되었습니다.<br>
                현재 **텔레그램 관리자 승인 대기 중**입니다.<br>
                승인이 완료되면 등록하신 계정으로 로그인이 가능합니다.
              </p>
              <button class="btn btn-primary" id="back-to-login" style="width: 100%;">로그인 화면으로 돌아가기</button>
            </div>
          `;
          
          container.querySelector('#back-to-login').addEventListener('click', () => {
            isRegisterMode = false;
            updateView();
          });
          
          showToast('가입 신청이 전송되었습니다. 관리자 승인을 기다려주세요.', 'success');
        } else {
          await login(username, password);
          showToast(`어서오세요, ${username} 작가님!`, 'success');
          router.navigate('/');
        }
      } catch (err) {
        errorDiv.style.display = 'block';
        errorDiv.textContent = err.message || '인증 처리에 실패했습니다.';
        showToast(err.message || '인증 처리에 실패했습니다.', 'error');
        submitBtn.disabled = false;
        submitBtn.textContent = originalBtnText;
      }
    });
  }

  updateView();
  return container;
}
