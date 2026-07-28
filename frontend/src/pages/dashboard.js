// Project Dashboard Page
import { api } from '../api/client.js';
import { showToast } from '../components/toast.js';
import { showSpinner, hideSpinner } from '../components/loading.js';
import { createModal } from '../components/modal.js';
import { openNovelDownloadModal } from './project.js';
import { openProjectExportModal, openProjectImportPicker } from '../utils/migration.js';

export async function renderDashboard() {
  const root = document.createElement('div');
  root.className = 'animate-fade-in';
  root.style.width = '100%';
  
  // Dashboard HTML Scaffold
  root.innerHTML = `
    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 32px; gap: 16px; flex-wrap: wrap;" class="flex-row-responsive">
      <div>
        <h1 style="font-family: var(--font-heading); font-size: 2.25rem; font-weight: 700; color: var(--text-primary); margin: 0;">집필 공간</h1>
        <p style="color: var(--text-secondary); margin-top: 4px;">진행 중인 소설 프로젝트를 관리하세요</p>
      </div>
      <div style="display: flex; gap: 10px; flex-wrap: wrap;">
        <button class="btn btn-secondary" id="btn-import-project" style="height: 44px;" title="JSON 백업에서 프로젝트 복원">
          📥 프로젝트 가져오기
        </button>
        <button class="btn btn-secondary" id="btn-from-template" style="height: 44px;" title="장르 템플릿">
          📋 템플릿으로 시작
        </button>
        <button class="btn btn-primary" id="btn-create-project" style="height: 44px;">
          <span>✨</span> 새 소설 집필 시작
        </button>
      </div>
    </div>
    
    <div id="projects-grid" style="display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap: 24px;">
      <!-- Projects will be loaded here -->
    </div>
  `;

  const grid = root.querySelector('#projects-grid');
  const createBtn = root.querySelector('#btn-create-project');
  const importBtn = root.querySelector('#btn-import-project');
  const templateBtn = root.querySelector('#btn-from-template');

  templateBtn?.addEventListener('click', async () => {
    try {
      showSpinner('템플릿 목록…');
      const res = await api.get('/project-templates');
      hideSpinner();
      const tpls = res.templates || [];
      const body = document.createElement('div');
      body.innerHTML = `
        <p style="font-size:0.9rem;color:var(--text-secondary);margin:0 0 12px;">장르별 시놉시스·캐릭터·1~2화 스켈레톤이 생성됩니다.</p>
        <div style="display:flex;flex-direction:column;gap:8px;">
          ${tpls.map(t => `
            <button type="button" class="btn btn-secondary tpl-pick" data-id="${t.id}"
              style="text-align:left;height:auto;padding:12px;display:flex;flex-direction:column;gap:4px;">
              <strong>${t.title}</strong>
              <span style="font-size:0.78rem;color:var(--text-muted);font-weight:400;">${t.synopsis || ''}</span>
            </button>`).join('')}
        </div>`;
      const modal = createModal({ title: '📋 템플릿으로 프로젝트 생성', content: body, showFooter: false });
      body.querySelectorAll('.tpl-pick').forEach(btn => {
        btn.addEventListener('click', async () => {
          showSpinner('프로젝트 생성 중…');
          try {
            const p = await api.post('/projects/from-template', { template_id: btn.dataset.id });
            hideSpinner();
            modal.close();
            showToast(`「${p.title}」 생성됨`, 'success');
            window.location.hash = `#/projects/${p.id}`;
          } catch (e) {
            hideSpinner();
            showToast(e.message || '생성 실패', 'error');
          }
        });
      });
    } catch (e) {
      hideSpinner();
      showToast(e.message || '템플릿 목록 실패', 'error');
    }
  });

  importBtn.addEventListener('click', () => {
    openProjectImportPicker({
      onSuccess: (result) => {
        if (result.new_project_id) {
          loadProjects();
          window.location.hash = `#/projects/${result.new_project_id}`;
        } else {
          loadProjects();
        }
      },
    });
  });

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
    if (prov === 'nvidia' || prov.includes('nvidia')) {
      return '🟩 <span class="badge badge-secondary" style="background-color: #e8f5e9; color: #1b5e20;">NVIDIA NIM</span>';
    }
    if (prov === 'custom_openai' || prov.includes('custom_openai')) {
      return '🔌 <span class="badge badge-secondary">Custom OpenAI</span>';
    }
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
      
      <div style="display: flex; justify-content: space-between; align-items: center; border-top: 1px solid var(--border-color); padding-top: 16px; margin-top: auto; gap: 8px;">
        <div style="display: flex; flex-direction: column; gap: 4px;">
          <span style="font-size: 0.75rem; color: var(--text-muted);">메인 AI 모델</span>
          <div style="font-size: 0.85rem; font-weight: 500; display: flex; align-items: center; gap: 6px;">
            ${getProviderIcon(project.llm_provider)}
          </div>
        </div>
        <div style="display: flex; flex-direction: column; align-items: flex-end; gap: 6px;">
          <div style="display: flex; gap: 4px; flex-wrap: wrap; justify-content: flex-end;">
            <button type="button" class="btn btn-secondary btn-card-export" style="padding: 4px 8px; font-size: 0.72rem; min-height: auto;" title="원고 파일 다운로드">
              📄 원고
            </button>
            <button type="button" class="btn btn-secondary btn-card-backup" style="padding: 4px 8px; font-size: 0.72rem; min-height: auto;" title="프로젝트 JSON 백업">
              📦 백업
            </button>
          </div>
          <span style="font-size: 0.8rem; color: var(--text-muted);">${dateStr}</span>
        </div>
      </div>
      
      <button class="btn-delete-project" title="프로젝트 삭제" style="position: absolute; top: 20px; right: 20px; background: none; border: none; font-size: 1.1rem; cursor: pointer; color: var(--text-muted); transition: color var(--transition-fast); padding: 4px;">
        🗑️
      </button>
    `;

    // Click card to navigate
    card.addEventListener('click', (e) => {
      if (
        e.target.closest('.btn-delete-project') ||
        e.target.closest('.btn-card-export') ||
        e.target.closest('.btn-card-backup')
      ) {
        return;
      }
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

    card.querySelector('.btn-card-export').addEventListener('click', (e) => {
      e.stopPropagation();
      openNovelDownloadModal(project.id, project.title);
    });

    card.querySelector('.btn-card-backup').addEventListener('click', (e) => {
      e.stopPropagation();
      openProjectExportModal(project.id, project.title);
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

      <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-bottom: 16px;" class="grid-cols-2">
        <div class="form-group">
          <label class="form-label" for="new-provider">LLM 프로바이더</label>
          <select class="form-control" id="new-provider">
            <option value="openai">OpenAI (GPT)</option>
            <option value="google">Google (Gemini)</option>
            <option value="anthropic">Anthropic (Claude)</option>
            <option value="nvidia">NVIDIA NIM (build.nvidia.com)</option>
            <option value="ollama">Ollama (로컬 LLM)</option>
            <option value="custom_openai">OpenAI 호환 API (Custom)</option>
          </select>
        </div>
        <div class="form-group">
          <label class="form-label" for="new-model">기본 AI 모델</label>
          <select class="form-control" id="new-model">
            <!-- Models populated dynamically -->
          </select>
        </div>
      </div>
      
      <!-- Custom model text input (hidden by default, shown for custom model selection) -->
      <div class="form-group" id="new-custom-model-container" style="display: none;">
        <label class="form-label" for="new-model-custom">모델명 직접 입력</label>
        <input class="form-control" type="text" id="new-model-custom" placeholder="예: meta/llama-3.1-8b-instruct, deepseek-chat">
      </div>

      <!-- Custom Base URL (hidden by default, shown only for custom_openai) -->
      <div class="form-group" id="new-baseurl-container" style="display: none;">
        <label class="form-label" for="new-baseurl">API Base URL</label>
        <input class="form-control" type="url" id="new-baseurl" placeholder="예: https://api.deepseek.com/v1">
      </div>
      
      <div class="form-group">
        <label class="form-label" for="new-apikey">API Key Override (선택)</label>
        <input class="form-control" type="password" id="new-apikey" placeholder="NVIDIA: nvapi-... / 미입력 시 서버 .env 키 사용">
        <p style="font-size: 0.75rem; color: var(--text-muted); margin-top: 6px; line-height: 1.4;">
          NVIDIA NIM 키는 <a href="https://build.nvidia.com/settings/api-keys" target="_blank" rel="noopener">build.nvidia.com</a>에서 발급합니다. 개발용 레이트 리밋이 있을 수 있습니다.
        </p>
      </div>
    `;

    const providerSelect = formContainer.querySelector('#new-provider');
    const modelSelect = formContainer.querySelector('#new-model');

    const modelOptions = {
      openai: [
        { value: 'gpt-4o-mini', text: 'gpt-4o-mini (속도/비용 최적)' },
        { value: 'gpt-4o', text: 'gpt-4o (고성능)' },
        { value: 'o3-mini', text: 'o3-mini (최신 추론)' },
        { value: 'o1', text: 'o1 (추론 특화)' },
        { value: 'o1-mini', text: 'o1-mini (경량 추론)' },
        { value: 'gpt-4-turbo', text: 'gpt-4-turbo' },
        { value: 'custom-model', text: '✏️ 직접 입력하기...' }
      ],
      google: [
        { value: 'gemini-2.5-flash', text: 'gemini-2.5-flash (2025 최신 경량)' },
        { value: 'gemini-2.5-pro', text: 'gemini-2.5-pro (2025 최신 고성능)' },
        { value: 'gemini-2.0-flash', text: 'gemini-2.0-flash (속도 최강)' },
        { value: 'gemini-2.0-pro-exp-02-05', text: 'gemini-2.0-pro-exp (추론/지식 특화)' },
        { value: 'gemini-1.5-pro', text: 'gemini-1.5-pro (대형 콘텍스트)' },
        { value: 'gemini-1.5-flash', text: 'gemini-1.5-flash' },
        { value: 'custom-model', text: '✏️ 직접 입력하기...' }
      ],
      anthropic: [
        { value: 'claude-3-7-sonnet-20250219', text: 'claude-3-7-sonnet (최신 1위)' },
        { value: 'claude-3-5-sonnet-20241022', text: 'claude-3-5-sonnet' },
        { value: 'claude-3-5-haiku-20241022', text: 'claude-3-5-haiku' },
        { value: 'custom-model', text: '✏️ 직접 입력하기...' }
      ],
      ollama: [
        { value: 'deepseek-r1:8b', text: 'deepseek-r1:8b (추론 로컬)' },
        { value: 'deepseek-r1:1.5b', text: 'deepseek-r1:1.5b' },
        { value: 'llama3.3:70b', text: 'Llama 3.3 (70B)' },
        { value: 'llama3.2:3b', text: 'Llama 3.2 (3B)' },
        { value: 'llama3.1:8b', text: 'Llama 3.1 (8B)' },
        { value: 'gemma2:9b', text: 'Gemma 2 (9B)' },
        { value: 'qwen2.5:7b', text: 'Qwen 2.5 (7B)' },
        { value: 'custom-model', text: '✏️ 직접 입력하기...' }
      ],
      // NVIDIA NIM 호스티드 (model id = org/name). 카탈로그: build.nvidia.com/models
      nvidia: [
        { value: 'meta/llama-3.1-8b-instruct', text: 'Llama 3.1 8B Instruct (경량/빠름)' },
        { value: 'meta/llama-3.1-70b-instruct', text: 'Llama 3.1 70B Instruct (고품질)' },
        { value: 'meta/llama-3.3-70b-instruct', text: 'Llama 3.3 70B Instruct' },
        { value: 'nvidia/nemotron-3-nano-30b-a3b', text: 'Nemotron 3 Nano 30B (효율)' },
        { value: 'nvidia/llama-3.3-nemotron-super-49b-v1.5', text: 'Nemotron Super 49B v1.5' },
        { value: 'mistralai/mistral-nemotron', text: 'Mistral Nemotron' },
        { value: 'qwen/qwen3-next-80b-a3b-instruct', text: 'Qwen3 Next 80B Instruct' },
        { value: 'moonshotai/kimi-k2-instruct', text: 'Kimi K2 Instruct' },
        { value: 'openai/gpt-oss-20b', text: 'GPT-OSS 20B' },
        { value: 'custom-model', text: '✏️ 직접 입력하기 (org/model)...' }
      ],
      custom_openai: [
        { value: 'custom-model', text: '✏️ 직접 입력하기...' }
      ]
    };

    const customModelContainer = formContainer.querySelector('#new-custom-model-container');
    const customModelInput = formContainer.querySelector('#new-model-custom');
    const baseurlContainer = formContainer.querySelector('#new-baseurl-container');
    const baseurlInput = formContainer.querySelector('#new-baseurl');

    function toggleCustomModelVisibility() {
      const isCustomModel = modelSelect.value === 'custom-model';
      const isCustomProvider = providerSelect.value === 'custom_openai';
      
      if (isCustomModel || isCustomProvider) {
        customModelContainer.style.display = 'block';
      } else {
        customModelContainer.style.display = 'none';
      }
    }

    function updateModels() {
      const selected = providerSelect.value;
      modelSelect.innerHTML = '';
      
      // Toggle Custom Base URL visibility
      if (selected === 'custom_openai') {
        baseurlContainer.style.display = 'block';
      } else {
        baseurlContainer.style.display = 'none';
      }
      
      (modelOptions[selected] || []).forEach(opt => {
        const o = document.createElement('option');
        o.value = opt.value;
        o.textContent = opt.text;
        modelSelect.appendChild(o);
      });

      toggleCustomModelVisibility();
    }

    providerSelect.addEventListener('change', updateModels);
    modelSelect.addEventListener('change', toggleCustomModelVisibility);
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
        
        let llm_model = modelSelect.value;
        if (llm_model === 'custom-model' || llm_provider === 'custom_openai') {
          llm_model = customModelInput.value.trim();
        }
        
        let raw_api_key = formContainer.querySelector('#new-apikey').value.trim();
        let api_key_override = raw_api_key || undefined;
        
        // Custom Base URL merge for OpenAI Compatible APIs
        if (llm_provider === 'custom_openai') {
          const base_url = baseurlInput.value.trim();
          if (base_url) {
            // Store as API_KEY::BASE_URL (even if API key is blank)
            api_key_override = `${raw_api_key}::${base_url}`;
          }
        }

        if (!title) {
          showToast('소설 제목을 입력해주세요.', 'error');
          return false; // Prevent modal closing
        }
        if (!llm_model || llm_model === 'custom-model') {
          showToast('모델명을 선택하거나 직접 입력해 주세요.', 'error');
          return false;
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
