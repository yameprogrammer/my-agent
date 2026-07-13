// Project Dashboard Page
import { api } from '../api/client.js';
import { showToast } from '../components/toast.js';
import { showSpinner, hideSpinner } from '../components/loading.js';
import { createModal } from '../components/modal.js';

export async function renderDashboard() {
  const root = document.createElement('div');
  root.className = 'animate-fade-in';
  root.style.width = '100%';
  
  // Dashboard HTML Scaffold
  root.innerHTML = `
    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 32px;" class="flex-row-responsive">
      <div>
        <h1 style="font-family: var(--font-heading); font-size: 2.25rem; font-weight: 700; color: var(--text-primary); margin: 0;">집필 공간</h1>
        <p style="color: var(--text-secondary); margin-top: 4px;">진행 중인 소설 프로젝트를 관리하세요</p>
      </div>
      <button class="btn btn-primary" id="btn-create-project" style="height: 44px;">
        <span>✨</span> 새 소설 집필 시작
      </button>
    </div>
    
    <div id="projects-grid" style="display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap: 24px;">
      <!-- Projects will be loaded here -->
    </div>
  `;

  const grid = root.querySelector('#projects-grid');
  const createBtn = root.querySelector('#btn-create-project');

  // Load projects from API
  async function loadProjects() {
    grid.innerHTML = '';
    showSpinner('소설 목록을 불러오는 중...');
    
    try {
      const projects = await api.get('/projects');
      hideSpinner();
      
      if (!projects || projects.length === 0) {
        renderEmptyState();
        return;
      }
      
      projects.forEach(project => {
        const card = createProjectCard(project);
        grid.appendChild(card);
      });
    } catch (err) {
      hideSpinner();
      grid.innerHTML = `
        <div style="grid-column: 1/-1; padding: 40px; text-align: center; color: var(--accent);">
          <span style="font-size: 2.5rem;">⚠️</span>
          <p style="margin-top: 12px; font-weight: 500;">프로젝트 목록을 불러오는 데 실패했습니다.</p>
          <p style="font-size: 0.85rem; color: var(--text-muted); margin-top: 4px;">${err.message}</p>
          <button class="btn btn-secondary" id="btn-retry-load" style="margin-top: 16px;">다시 시도</button>
        </div>
      `;
      grid.querySelector('#btn-retry-load').addEventListener('click', loadProjects);
    }
  }

  function renderEmptyState() {
    grid.innerHTML = `
      <div style="grid-column: 1/-1; padding: 80px 24px; text-align: center;" class="glass-card">
        <span style="font-size: 4rem; display: block; margin-bottom: 20px;">🖋️</span>
        <h3 style="font-family: var(--font-heading); font-size: 1.3rem; margin-bottom: 8px;">아직 집필 중인 소설이 없습니다</h3>
        <p style="color: var(--text-secondary); max-width: 420px; margin: 0 auto 24px; font-size: 0.95rem; line-height: 1.5;">
          에이전트와 함께 흥미진진한 첫 소설 프로젝트를 시작해 보세요. 세계관 설정부터 챕터 집필까지 편리하게 진행됩니다.
        </p>
        <button class="btn btn-primary" id="btn-empty-create">첫 소설 시작하기</button>
      </div>
    `;
    
    grid.querySelector('#btn-empty-create').addEventListener('click', openCreateModal);
  }

  function getProviderIcon(provider) {
    const prov = (provider || '').toLowerCase();
    if (prov.includes('openai')) return '🤖 <span class="badge badge-primary">OpenAI</span>';
    if (prov.includes('google')) return '♊ <span class="badge badge-success">Google</span>';
    if (prov.includes('anthropic')) return '🧬 <span class="badge badge-secondary" style="background-color: #ffeedd; color: #cc6600;">Anthropic</span>';
    if (prov.includes('ollama')) return '🦙 <span class="badge badge-secondary">Ollama</span>';
    return '🔌 ' + provider;
  }

  function createProjectCard(project) {
    const card = document.createElement('div');
    card.className = 'glass-card';
    card.style.padding = '24px';
    card.style.position = 'relative';
    card.style.display = 'flex';
    card.style.flexDirection = 'column';
    card.style.justifyContent = 'space-between';
    card.style.minHeight = '200px';
    card.style.cursor = 'pointer';
    
    const dateStr = new Date(project.created_at).toLocaleDateString('ko-KR', {
      year: 'numeric',
      month: 'long',
      day: 'numeric'
    });

    card.innerHTML = `
      <div>
        <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 12px; padding-right: 28px;">
          <h3 class="project-title" style="font-family: var(--font-heading); font-size: 1.25rem; font-weight: 600; color: var(--text-primary); margin: 0;">${project.title}</h3>
        </div>
        <p style="color: var(--text-secondary); font-size: 0.9rem; line-height: 1.5; margin-bottom: 16px; overflow: hidden; display: -webkit-box; -webkit-line-clamp: 3; -webkit-box-orient: vertical;">
          ${project.synopsis || '등록된 시놉시스가 없습니다.'}
        </p>
      </div>
      
      <div style="display: flex; justify-content: space-between; align-items: center; border-top: 1px solid var(--border-color); padding-top: 16px; margin-top: auto;">
        <div style="display: flex; flex-direction: column; gap: 4px;">
          <span style="font-size: 0.75rem; color: var(--text-muted);">메인 AI 모델</span>
          <div style="font-size: 0.85rem; font-weight: 500; display: flex; align-items: center; gap: 6px;">
            ${getProviderIcon(project.llm_provider)}
          </div>
        </div>
        <span style="font-size: 0.8rem; color: var(--text-muted);">${dateStr}</span>
      </div>
      
      <button class="btn-delete-project" title="프로젝트 삭제" style="position: absolute; top: 20px; right: 20px; background: none; border: none; font-size: 1.1rem; cursor: pointer; color: var(--text-muted); transition: color var(--transition-fast); padding: 4px;">
        🗑️
      </button>
    `;

    // Click card to navigate
    card.addEventListener('click', (e) => {
      if (e.target.closest('.btn-delete-project')) return;
      window.location.hash = `#/projects/${project.id}`;
    });

    // Delete project event
    const deleteBtn = card.querySelector('.btn-delete-project');
    deleteBtn.addEventListener('mouseenter', () => { deleteBtn.style.color = 'var(--accent)'; });
    deleteBtn.addEventListener('mouseleave', () => { deleteBtn.style.color = 'var(--text-muted)'; });
    
    deleteBtn.addEventListener('click', (e) => {
      e.stopPropagation();
      confirmDelete(project, card);
    });

    return card;
  }

  function confirmDelete(project, cardElement) {
    createModal({
      title: '프로젝트 삭제',
      content: `정말로 소설 <strong>"${project.title}"</strong> 프로젝트를 삭제하시겠습니까?<br><span style="color: var(--accent); font-size: 0.85rem; display: block; margin-top: 8px;">⚠️ 이 작업은 되돌릴 수 없으며 모든 캐릭터, 설정집, 에피소드 및 집필 본문이 영구 삭제됩니다.</span>`,
      confirmText: '삭제',
      cancelText: '취소',
      isDangerous: true,
      onConfirm: async () => {
        showSpinner('프로젝트를 삭제하는 중...');
        try {
          await api.delete(`/projects/${project.id}`);
          hideSpinner();
          showToast(`"${project.title}" 소설을 성공적으로 삭제했습니다.`, 'success');
          
          // Animate card removal
          cardElement.style.transform = 'scale(0.9)';
          cardElement.style.opacity = '0';
          setTimeout(() => {
            cardElement.remove();
            // Check if grid is empty now
            if (grid.children.length === 0) {
              renderEmptyState();
            }
          }, 300);
        } catch (err) {
          hideSpinner();
          showToast(`삭제 실패: ${err.message}`, 'error');
        }
      }
    });
  }

  function openCreateModal() {
    const formContainer = document.createElement('div');
    formContainer.innerHTML = `
      <div class="form-group">
        <label class="form-label" for="new-title">소설 제목</label>
        <input class="form-control" type="text" id="new-title" placeholder="예: 우주 저편의 서재" required minlength="1" maxlength="100">
      </div>
      
      <div class="form-group">
        <label class="form-label" for="new-synopsis">시놉시스 / 줄거리 개요</label>
        <textarea class="form-control" id="new-synopsis" placeholder="소설의 중심 소재나 시놉시스를 자유롭게 적어주세요. AI 기획 및 초안 작성에 반영됩니다." style="height: 120px; resize: none;"></textarea>
      </div>
      
      <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 16px;">
        <div class="form-group">
          <label class="form-label" for="new-provider">기본 AI 프로바이더</label>
          <select class="form-control" id="new-provider">
            <option value="openai">OpenAI (GPT)</option>
            <option value="google">Google (Gemini)</option>
            <option value="anthropic">Anthropic (Claude)</option>
            <option value="ollama">Ollama (로컬 LLM)</option>
          </select>
        </div>
        <div class="form-group">
          <label class="form-label" for="new-model">기본 AI 모델</label>
          <select class="form-control" id="new-model">
            <!-- Models populated dynamically -->
          </select>
        </div>
      </div>
      
      <div class="form-group">
        <label class="form-label" for="new-apikey">API Key Override (선택)</label>
        <input class="form-control" type="password" id="new-apikey" placeholder="지정하지 않을 시 홈 서버 설정값을 사용합니다">
      </div>
    `;

    const providerSelect = formContainer.querySelector('#new-provider');
    const modelSelect = formContainer.querySelector('#new-model');

    const modelOptions = {
      openai: [
        { value: 'gpt-4o-mini', text: 'gpt-4o-mini (권장)' },
        { value: 'gpt-4o', text: 'gpt-4o' },
        { value: 'o1-mini', text: 'o1-mini' }
      ],
      google: [
        { value: 'gemini-1.5-flash', text: 'gemini-1.5-flash (권장)' },
        { value: 'gemini-1.5-pro', text: 'gemini-1.5-pro' }
      ],
      anthropic: [
        { value: 'claude-3-5-haiku-20241022', text: 'claude-3-5-haiku (권장)' },
        { value: 'claude-3-5-sonnet-20241022', text: 'claude-3-5-sonnet' }
      ],
      ollama: [
        { value: 'llama3:8b', text: 'Llama 3 (8B)' },
        { value: 'gemma2:9b', text: 'Gemma 2 (9B)' },
        { value: 'mistral', text: 'Mistral' }
      ]
    };

    function updateModels() {
      const selected = providerSelect.value;
      modelSelect.innerHTML = '';
      (modelOptions[selected] || []).forEach(opt => {
        const o = document.createElement('option');
        o.value = opt.value;
        o.textContent = opt.text;
        modelSelect.appendChild(o);
      });
    }

    providerSelect.addEventListener('change', updateModels);
    updateModels(); // Initial run

    createModal({
      title: '새 소설 프로젝트 시작',
      content: formContainer,
      confirmText: '생성',
      cancelText: '취소',
      onConfirm: async (dismiss) => {
        const title = formContainer.querySelector('#new-title').value.trim();
        const synopsis = formContainer.querySelector('#new-synopsis').value.trim() || undefined;
        const llm_provider = providerSelect.value;
        const llm_model = modelSelect.value;
        const api_key_override = formContainer.querySelector('#new-apikey').value.trim() || undefined;

        if (!title) {
          showToast('소설 제목을 입력해주세요.', 'error');
          return false; // Prevent modal closing
        }

        showSpinner('새 프로젝트 생성 중...');
        try {
          const newProj = await api.post('/projects', {
            title,
            synopsis,
            llm_provider,
            llm_model,
            api_key_override
          });
          hideSpinner();
          dismiss(); // Manual dismiss
          showToast(`소설 "${title}" 프로젝트가 시작되었습니다!`, 'success');
          loadProjects(); // Reload list
        } catch (err) {
          hideSpinner();
          showToast(`생성 실패: ${err.message}`, 'error');
          return false; // Prevent modal closing
        }
      }
    });
  }

  createBtn.addEventListener('click', openCreateModal);
  loadProjects();

  return root;
}
