// Project Settings Page (per-agent LLM configurations)
import { api } from '../api/client.js';
import { showToast } from '../components/toast.js';
import { showSpinner, hideSpinner } from '../components/loading.js';
import { openProjectExportModal, openProjectImportPicker } from '../utils/migration.js';

export async function renderSettings(projectId) {
  const container = document.createElement('div');
  container.className = 'animate-fade-in';
  
  let projectData = null;

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
    // NVIDIA NIM (org/model). 카탈로그: https://build.nvidia.com/models
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

  container.innerHTML = `
    <form id="project-settings-form" style="display: flex; flex-direction: column; gap: 24px;">
      
      <!-- Basic Info Card -->
      <div class="glass-card" style="padding: 24px;">
        <h4 style="font-family: var(--font-heading); font-size: 1.15rem; margin-bottom: 20px; display: flex; align-items: center; gap: 8px;">
          <span>📝</span> 소설 기본 정보
        </h4>
        
        <div class="form-group">
          <label class="form-label" for="edit-title">소설 제목</label>
          <input class="form-control" type="text" id="edit-title" required maxlength="100">
        </div>
        
        <div class="form-group" style="margin-bottom: 0;">
          <label class="form-label" for="edit-synopsis">시놉시스 / 줄거리</label>
          <textarea class="form-control" id="edit-synopsis" style="height: 120px; resize: none;"></textarea>
        </div>
        <div class="form-group" style="margin-top: 16px; margin-bottom: 0;">
          <label class="form-label" for="edit-style-guide">문체 스타일 가이드 (IDEA-08)</label>
          <textarea class="form-control" id="edit-style-guide" style="height: 100px; resize: vertical;" placeholder="문체 샘플 문단 또는 어조 지시 (Writer/Editor 주입)"></textarea>
        </div>
        <div style="display: flex; flex-wrap: wrap; gap: 16px; margin-top: 14px;">
          <label style="display: flex; align-items: center; gap: 8px; font-size: 0.9rem; cursor: pointer;">
            <input type="checkbox" id="edit-low-cost"> 저비용 모드 (Plotter/Judge 등 소형 모델, Writer 유지)
          </label>
          <label style="display: flex; align-items: center; gap: 8px; font-size: 0.9rem; cursor: pointer;">
            <input type="checkbox" id="edit-force-hook"> 말미 훅 강제 (회차 끝 클리프행어)
          </label>
        </div>
      </div>

      <!-- Usage summary IDEA-11 -->
      <div class="glass-card" style="padding: 24px;">
        <h4 style="font-family: var(--font-heading); font-size: 1.15rem; margin-bottom: 12px;">📊 토큰·호출 요약 (대략)</h4>
        <div id="usage-summary-box" style="font-size: 0.85rem; color: var(--text-secondary);">불러오는 중…</div>
        <button type="button" class="btn btn-secondary" id="btn-refresh-usage" style="margin-top: 12px; font-size: 0.85rem;">새로고침</button>
      </div>
      
      <!-- Global LLM Defaults Card -->
      <div class="glass-card" style="padding: 24px;">
        <h4 style="font-family: var(--font-heading); font-size: 1.15rem; margin-bottom: 20px; display: flex; align-items: center; gap: 8px;">
          <span>🌐</span> 공통 AI 기본 모델 설정
        </h4>
        
        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-bottom: 16px;" class="grid-cols-2">
          <div class="form-group">
            <label class="form-label" for="edit-provider">기본 프로바이더</label>
            <select class="form-control" id="edit-provider">
              <option value="openai">OpenAI (GPT)</option>
              <option value="google">Google (Gemini)</option>
              <option value="anthropic">Anthropic (Claude)</option>
              <option value="nvidia">NVIDIA NIM (build.nvidia.com)</option>
              <option value="ollama">Ollama (로컬 LLM)</option>
              <option value="custom_openai">OpenAI 호환 API (Custom)</option>
            </select>
          </div>
          <div class="form-group">
            <label class="form-label" for="edit-model">기본 모델</label>
            <select class="form-control" id="edit-model"></select>
          </div>
        </div>
        
        <!-- Custom Model input (hidden by default) -->
        <div class="form-group" id="edit-custom-model-container" style="display: none;">
          <label class="form-label" for="edit-model-custom">모델명 직접 입력</label>
          <input class="form-control" type="text" id="edit-model-custom" placeholder="예: meta/llama-3.1-8b-instruct, deepseek-chat">
        </div>

        <!-- Custom Base URL (hidden by default) -->
        <div class="form-group" id="edit-baseurl-container" style="display: none;">
          <label class="form-label" for="edit-baseurl">API Base URL</label>
          <input class="form-control" type="url" id="edit-baseurl" placeholder="예: https://api.deepseek.com/v1 또는 https://ollama.com/v1">
          <p style="font-size: 0.75rem; color: var(--text-muted); margin-top: 6px; line-height: 1.45;">
            <strong>Ollama Cloud</strong>: 프로바이더=OpenAI 호환,
            Base URL=<code>https://ollama.com</code> 또는 <code>https://ollama.com/v1</code> (둘 다 인식),
            API Key=<a href="https://ollama.com/settings/keys" target="_blank" rel="noopener">ollama.com 키</a>를
            <strong>매번 키+URL 함께 저장</strong>,
            모델=클라우드 id (예: <code>gpt-oss:120b</code>).
            서버는 ollama.com 감지 시 공식 네이티브 API(<code>/api/chat</code>+Bearer)로 호출합니다.
          </p>
        </div>
        
        <div class="form-group" style="margin-bottom: 0;">
          <label class="form-label" for="edit-apikey">공통 API Key (선택)</label>
          <input class="form-control" type="password" id="edit-apikey" placeholder="NVIDIA: nvapi-... / Ollama Cloud: ollama.com 키 / 호환 API 키">
          <p style="font-size: 0.75rem; color: var(--text-muted); margin-top: 6px; line-height: 1.4;">
            NVIDIA NIM은 Base URL이 자동 고정됩니다.
            <strong>OpenAI 호환·Ollama Cloud</strong>는 저장할 때마다 <strong>API 키 + Base URL을 함께</strong> 다시 입력하세요
            (키만 비우고 URL만 바꾸면 401이 납니다).
            Ollama 키:
            <a href="https://ollama.com/settings/keys" target="_blank" rel="noopener">ollama.com/settings/keys</a>
            · NVIDIA:
            <a href="https://build.nvidia.com/settings/api-keys" target="_blank" rel="noopener">build.nvidia.com</a>
          </p>
        </div>
      </div>
      
      <!-- Per-Agent Advanced Configuration -->
      <div class="glass-card" style="padding: 24px;">
        <h4 style="font-family: var(--font-heading); font-size: 1.15rem; margin-bottom: 8px; display: flex; align-items: center; gap: 8px;">
          <span>🤖</span> 에이전트별 세부 오버라이드 설정
        </h4>
        <p style="color: var(--text-secondary); font-size: 0.85rem; margin-bottom: 20px;">
          기획, 집필, 일관성 평가 등 에이전트 역할별로 서로 다른 AI 모델과 고유 API 키를 오버라이드할 수 있습니다. (예: Writer=NVIDIA Llama 70B, Judge=Gemini Flash). 미선택 시 기본 모델 적용.
        </p>
        
        <div style="display: flex; flex-direction: column; gap: 16px;" id="agents-config-list">
          <!-- Populated dynamically -->
        </div>
      </div>
      
      <!-- Migration / Backup (IMP-02) -->
      <div class="glass-card" style="padding: 24px;">
        <h4 style="font-family: var(--font-heading); font-size: 1.15rem; margin-bottom: 8px; display: flex; align-items: center; gap: 8px;">
          <span>📦</span> 프로젝트 백업 · 마이그레이션
        </h4>
        <p style="color: var(--text-secondary); font-size: 0.85rem; margin-bottom: 16px; line-height: 1.5;">
          이 프로젝트 전체를 JSON으로 내보내거나, 백업 파일을 가져와 새 프로젝트로 복원합니다.
          기본 export 는 <strong>API 키를 포함하지 않습니다</strong>.
        </p>
        <div style="display: flex; gap: 10px; flex-wrap: wrap;">
          <button type="button" class="btn btn-secondary" id="btn-settings-export">
            📦 이 프로젝트 내보내기
          </button>
          <button type="button" class="btn btn-secondary" id="btn-settings-import">
            📥 JSON 가져오기 (새 프로젝트)
          </button>
        </div>
      </div>

      <!-- Form Actions -->
      <div style="display: flex; justify-content: flex-end; gap: 12px; margin-bottom: 40px;">
        <button class="btn btn-primary" type="submit" style="font-weight: 600; padding: 12px 28px;">
          💾 설정 변경 내용 저장
        </button>
      </div>
      
    </form>
  `;

  const form = container.querySelector('#project-settings-form');
  const providerSelect = container.querySelector('#edit-provider');
  const modelSelect = container.querySelector('#edit-model');
  const customModelContainer = container.querySelector('#edit-custom-model-container');
  const customModelInput = container.querySelector('#edit-model-custom');
  const baseurlContainer = container.querySelector('#edit-baseurl-container');
  const baseurlInput = container.querySelector('#edit-baseurl');
  
  const agentsList = container.querySelector('#agents-config-list');

  container.querySelector('#btn-settings-export')?.addEventListener('click', () => {
    const title = container.querySelector('#edit-title')?.value || projectData?.title || 'project';
    openProjectExportModal(projectId, title);
  });
  container.querySelector('#btn-settings-import')?.addEventListener('click', () => {
    openProjectImportPicker();
  });

  const agents = [
    { key: 'plotter', name: '🎯 Plotter (시놉시스 분석 및 씬 기획 담당)' },
    { key: 'writer', name: '✍️ Writer (각 씬의 소설 본문 집필 담당)' },
    { key: 'judge', name: '⚖️ Judge (세계관 설정집 일관성 검사 담당)' },
    { key: 'editor', name: '📐 Editor (비평 피드백 반영 원고 퇴고 담당)' },
    { key: 'reviewer', name: '📝 Reviewer (집필 완료 후 종합 가독성 평가 담당)' }
  ];

  // Populate models list dynamically, handle custom value restoration.
  // Sentinel value "custom-model" is UI-only — DB 에는 실제 모델명 문자열만 저장한다.
  function populateModelDropdown(selectElement, providerVal, currentVal = '', customInputContainer = null, customInputElement = null) {
    selectElement.innerHTML = '';
    const opts = modelOptions[providerVal] || modelOptions.openai;
    const val = (currentVal || '').trim();
    // 프리셋 목록에 있는 실제 모델명 (직접입력 sentinel 제외)
    const isPresetModel = !!val && val !== 'custom-model' && opts.some(opt => opt.value === val && opt.value !== 'custom-model');
    const useCustomInput = providerVal === 'custom_openai' || (!!val && !isPresetModel) || val === 'custom-model';

    opts.forEach(opt => {
      const o = document.createElement('option');
      o.value = opt.value;
      o.textContent = opt.text;
      selectElement.appendChild(o);
    });

    if (useCustomInput) {
      const customOpt = selectElement.querySelector('option[value="custom-model"]');
      if (customOpt) {
        customOpt.selected = true;
      }
      if (customInputContainer) customInputContainer.style.display = 'block';
      if (customInputElement) {
        // DB 에 저장된 실제 모델명 복원 (sentinel 은 입력란에 넣지 않음)
        customInputElement.value = (val && val !== 'custom-model') ? val : '';
      }
    } else {
      if (isPresetModel) {
        selectElement.value = val;
      } else if (opts.length) {
        // 기본: 목록 첫 실제 모델 (custom-model 제외)
        const first = opts.find(o => o.value !== 'custom-model') || opts[0];
        selectElement.value = first.value;
      }
      if (customInputContainer) customInputContainer.style.display = 'none';
      if (customInputElement && !val) customInputElement.value = '';
    }
  }

  function resolveModelForSave(selectEl, customInputEl, provider) {
    const selected = selectEl.value;
    if (selected === 'custom-model' || provider === 'custom_openai') {
      const typed = (customInputEl?.value || '').trim();
      return typed;
    }
    return selected;
  }

  function parseApiKeyField(rawField) {
    if (rawField && rawField.includes('::')) {
      const parts = rawField.split('::', 2);
      return { apiKey: parts[0], baseUrl: parts[1] };
    }
    return { apiKey: rawField, baseUrl: '' };
  }

  // Load project details
  async function loadProjectDetails() {
    showSpinner('설정 데이터를 불러오는 중...');
    try {
      projectData = await api.get(`/projects/${projectId}`);
      hideSpinner();
      
      // Populate fields
      container.querySelector('#edit-title').value = projectData.title || '';
      container.querySelector('#edit-synopsis').value = projectData.synopsis || '';
      const sg = container.querySelector('#edit-style-guide');
      if (sg) sg.value = projectData.style_guide || '';
      const lc = container.querySelector('#edit-low-cost');
      if (lc) lc.checked = !!projectData.low_cost_mode;
      const fh = container.querySelector('#edit-force-hook');
      if (fh) fh.checked = !!projectData.force_ending_hook;
      loadUsageSummary();
      
      const provider = projectData.llm_provider || 'openai';
      providerSelect.value = provider;
      
      // Toggle custom settings visibility
      if (provider === 'custom_openai') {
        baseurlContainer.style.display = 'block';
      } else {
        baseurlContainer.style.display = 'none';
      }

      populateModelDropdown(modelSelect, provider, projectData.llm_model, customModelContainer, customModelInput);
      
      if (projectData.api_key_override) {
        const { apiKey, baseUrl } = parseApiKeyField(projectData.api_key_override);
        baseurlInput.value = baseUrl || '';
        
        if (projectData.has_api_key) {
          container.querySelector('#edit-apikey').placeholder = '🔑 API 키 등록됨 (덮어쓸 경우만 새로 입력)';
        }
      } else if (projectData.has_api_key) {
        container.querySelector('#edit-apikey').placeholder = '🔑 API 키 등록됨 (덮어쓸 경우만 새로 입력)';
      }
      
      renderAgentsConfig();
    } catch (err) {
      hideSpinner();
      showToast(`설정 조회 실패: ${err.message}`, 'error');
    }
  }

  function renderAgentsConfig() {
    agentsList.innerHTML = '';
    
    agents.forEach(agent => {
      // API 는 flat 필드 (plotter_provider / plotter_model …) — nested projectData.plotter 아님
      const agentProvider = projectData[`${agent.key}_provider`] || null;
      const agentModel = projectData[`${agent.key}_model`] || null;
      const hasOverride = !!(agentProvider || agentModel);
      
      const el = document.createElement('div');
      el.className = 'agent-card';
      el.style.border = '1px solid var(--border-color)';
      el.style.borderRadius = 'var(--radius-sm)';
      el.style.padding = '16px';
      el.style.backgroundColor = 'var(--bg-app)';
      
      const hasKeyField = `has_${agent.key}_api_key`;
      const hasKey = !!projectData[hasKeyField];

      el.innerHTML = `
        <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 12px;">
          <strong style="color: var(--text-primary); font-size: 0.95rem;">${agent.name}</strong>
          <label style="display: flex; align-items: center; gap: 6px; font-size: 0.85rem; font-weight: 500; cursor: pointer;">
            <input type="checkbox" id="chk-override-${agent.key}" ${hasOverride ? 'checked' : ''} style="cursor: pointer;">
            <span>개별 오버라이드 사용</span>
          </label>
        </div>
        
        <div id="panel-override-${agent.key}" style="display: ${hasOverride ? 'grid' : 'none'}; grid-template-columns: 1fr 1fr; gap: 12px; margin-top: 12px;" class="grid-cols-2">
          <div class="form-group" style="margin-bottom: 0;">
            <label class="form-label" style="font-size: 0.8rem;" for="override-prov-${agent.key}">프로바이더</label>
            <select class="form-control" id="override-prov-${agent.key}" style="padding: 6px 10px; font-size: 0.85rem;">
              <option value="openai">OpenAI (GPT)</option>
              <option value="google">Google (Gemini)</option>
              <option value="anthropic">Anthropic (Claude)</option>
              <option value="nvidia">NVIDIA NIM (build.nvidia.com)</option>
              <option value="ollama">Ollama (로컬 LLM)</option>
              <option value="custom_openai">OpenAI 호환 API (Custom)</option>
            </select>
          </div>
          <div class="form-group" style="margin-bottom: 0;">
            <label class="form-label" style="font-size: 0.8rem;" for="override-model-${agent.key}">모델명</label>
            <select class="form-control" id="override-model-${agent.key}" style="padding: 6px 10px; font-size: 0.85rem;"></select>
          </div>

          <!-- Custom Model directly input -->
          <div class="form-group" id="override-custom-model-container-${agent.key}" style="grid-column: 1/-1; margin-bottom: 0; display: none;">
            <label class="form-label" style="font-size: 0.8rem;" for="override-model-custom-${agent.key}">모델명 직접 입력</label>
            <input class="form-control" type="text" id="override-model-custom-${agent.key}" style="padding: 6px 10px; font-size: 0.85rem;" placeholder="예: deepseek-chat, qwen-max">
          </div>

          <!-- Custom Base URL for Agent -->
          <div class="form-group" id="override-baseurl-container-${agent.key}" style="grid-column: 1/-1; margin-bottom: 0; display: none;">
            <label class="form-label" style="font-size: 0.8rem;" for="override-baseurl-${agent.key}">API Base URL</label>
            <input class="form-control" type="url" id="override-baseurl-${agent.key}" style="padding: 6px 10px; font-size: 0.85rem;" placeholder="예: https://api.deepseek.com/v1">
          </div>

          <div class="form-group" style="grid-column: 1/-1; margin-bottom: 0; margin-top: 8px;">
            <label class="form-label" style="font-size: 0.8rem;" for="override-key-${agent.key}">전용 API Key (선택)</label>
            <input class="form-control" type="password" id="override-key-${agent.key}" style="padding: 6px 10px; font-size: 0.85rem;" placeholder="${hasKey ? '🔑 API 키 등록됨 (덮어쓸 경우만 입력)' : '전용 API 키 입력'}">
          </div>
        </div>
      `;

      const chk = el.querySelector(`#chk-override-${agent.key}`);
      const panel = el.querySelector(`#panel-override-${agent.key}`);
      const provSelect = el.querySelector(`#override-prov-${agent.key}`);
      const modSelect = el.querySelector(`#override-model-${agent.key}`);
      const customModelCont = el.querySelector(`#override-custom-model-container-${agent.key}`);
      const customModelIn = el.querySelector(`#override-model-custom-${agent.key}`);
      const baseurlCont = el.querySelector(`#override-baseurl-container-${agent.key}`);
      const baseurlIn = el.querySelector(`#override-baseurl-${agent.key}`);

      function toggleAgentCustomFields() {
        if (provSelect.value === 'custom_openai') {
          baseurlCont.style.display = 'block';
        } else {
          baseurlCont.style.display = 'none';
        }

        if (modSelect.value === 'custom-model' || provSelect.value === 'custom_openai') {
          customModelCont.style.display = 'block';
        } else {
          customModelCont.style.display = 'none';
        }
      }

      // Handle checkbox change
      chk.addEventListener('change', () => {
        panel.style.display = chk.checked ? 'grid' : 'none';
        if (chk.checked) {
          if (!provSelect.value) provSelect.value = 'openai';
          populateModelDropdown(modSelect, provSelect.value, agentModel || '', customModelCont, customModelIn);
        }
        toggleAgentCustomFields();
      });

      // Handle provider change
      provSelect.addEventListener('change', () => {
        populateModelDropdown(modSelect, provSelect.value, '', customModelCont, customModelIn);
        toggleAgentCustomFields();
      });

      // Handle model selection change (custom model visibility toggle)
      modSelect.addEventListener('change', () => {
        toggleAgentCustomFields();
      });

      // Initial populate
      if (hasOverride) {
        provSelect.value = agentProvider || 'openai';
        populateModelDropdown(modSelect, provSelect.value, agentModel || '', customModelCont, customModelIn);
        toggleAgentCustomFields();
      }

      agentsList.appendChild(el);
    });
  }

  // Handle global provider change
  providerSelect.addEventListener('change', () => {
    const selected = providerSelect.value;
    
    if (selected === 'custom_openai') {
      baseurlContainer.style.display = 'block';
    } else {
      baseurlContainer.style.display = 'none';
    }

    populateModelDropdown(modelSelect, selected, '', customModelContainer, customModelInput);
  });

  // Handle global model selection change
  modelSelect.addEventListener('change', () => {
    if (modelSelect.value === 'custom-model' || providerSelect.value === 'custom_openai') {
      customModelContainer.style.display = 'block';
    } else {
      customModelContainer.style.display = 'none';
    }
  });

  // Handle form submit
  form.addEventListener('submit', async (e) => {
    e.preventDefault();

    const title = container.querySelector('#edit-title').value.trim();
    const synopsis = container.querySelector('#edit-synopsis').value.trim() || undefined;
    const llm_provider = providerSelect.value;

    const llm_model = resolveModelForSave(modelSelect, customModelInput, llm_provider);
    if (!llm_model) {
      showToast('모델명을 입력하거나 목록에서 선택해 주세요. (직접 입력 시 모델명 필수)', 'error');
      return;
    }
    // UI sentinel 이 DB 에 들어가면 안 됨
    if (llm_model === 'custom-model') {
      showToast('「직접 입력」을 선택한 경우 실제 모델명(예: gpt-4o-mini, meta/llama-3.1-8b-instruct)을 입력하세요.', 'error');
      return;
    }

    let raw_api_key = container.querySelector('#edit-apikey').value.trim();
    let api_key_override = raw_api_key || undefined;

    if (llm_provider === 'custom_openai') {
      const base_url = baseurlInput.value.trim();
      // 키와 Base URL 은 반드시 한 덩어리(KEY::URL)로 저장된다.
      // 키 칸을 비운 채 URL 만 저장하면 "::https://…" 가 되어 401 이 난다.
      if (!base_url) {
        showToast(
          'OpenAI 호환 사용 시 API Base URL 이 필요합니다. (Ollama Cloud: https://ollama.com/v1)',
          'error'
        );
        return;
      }
      if (!raw_api_key) {
        showToast(
          'OpenAI 호환/Ollama Cloud 는 API 키를 다시 입력해야 저장됩니다. '
          + '(키는 URL과 함께 묶여 저장되며, 빈 칸으로 두면 인증 정보가 깨집니다.) '
          + 'ollama.com/settings/keys 키를 복사해 붙여 넣으세요.',
          'error'
        );
        return;
      }
      api_key_override = `${raw_api_key}::${base_url}`;
    }

    if (!title) {
      showToast('소설 제목은 필수 항목입니다.', 'error');
      return;
    }

    const payload = {
      title,
      synopsis,
      llm_provider,
      llm_model,
      style_guide: container.querySelector('#edit-style-guide')?.value?.trim() || null,
      low_cost_mode: !!container.querySelector('#edit-low-cost')?.checked,
      force_ending_hook: !!container.querySelector('#edit-force-hook')?.checked,
    };
    // 키 미입력 시 기존 키 유지 (undefined 필드 제외)
    if (api_key_override !== undefined) {
      payload.api_key_override = api_key_override;
    }

    // 에이전트 오버라이드 → API flat 필드 (plotter_provider, plotter_model, plotter_api_key …)
    for (const agent of agents) {
      const chk = container.querySelector(`#chk-override-${agent.key}`);
      if (chk && chk.checked) {
        const provider = container.querySelector(`#override-prov-${agent.key}`).value;
        const modSelect = container.querySelector(`#override-model-${agent.key}`);
        const customIn = container.querySelector(`#override-model-custom-${agent.key}`);
        const model = resolveModelForSave(modSelect, customIn, provider);
        if (!model || model === 'custom-model') {
          showToast(`${agent.name}: 오버라이드 모델명을 입력해 주세요.`, 'error');
          return;
        }

        let raw_key = container.querySelector(`#override-key-${agent.key}`).value.trim();
        let api_key = raw_key || undefined;
        if (provider === 'custom_openai') {
          const base_url = container.querySelector(`#override-baseurl-${agent.key}`).value.trim();
          if (base_url) {
            api_key = `${raw_key}::${base_url}`;
          }
        }

        payload[`${agent.key}_provider`] = provider;
        payload[`${agent.key}_model`] = model;
        if (api_key !== undefined) {
          payload[`${agent.key}_api_key`] = api_key;
        }
      } else {
        // 오버라이드 해제
        payload[`${agent.key}_provider`] = null;
        payload[`${agent.key}_model`] = null;
        payload[`${agent.key}_api_key`] = null;
      }
    }

    showSpinner('소설 프로젝트 설정을 저장하는 중...');
    
    try {
      await api.put(`/projects/${projectId}`, payload);
      hideSpinner();
      showToast('프로젝트 설정이 성공적으로 저장되었습니다.', 'success');
      loadProjectDetails(); // Reload state
    } catch (err) {
      hideSpinner();
      showToast(`저장 실패: ${err.message}`, 'error');
    }
  });

  async function loadUsageSummary() {
    const box = container.querySelector('#usage-summary-box');
    if (!box) return;
    try {
      const rows = await api.get(`/projects/${projectId}/usage/summary`);
      if (!rows?.length) {
        box.textContent = '아직 기록된 에이전트 호출이 없습니다. 집필을 실행하면 Writer 등이 기록됩니다.';
        return;
      }
      box.innerHTML = `
        <table style="width:100%; border-collapse: collapse; font-size: 0.82rem;">
          <thead><tr style="text-align:left; border-bottom:1px solid var(--border-color);">
            <th style="padding:6px;">역할</th><th>호출</th><th>≈in tok</th><th>≈out tok</th><th>평균 ms</th><th>실패</th>
          </tr></thead>
          <tbody>
            ${rows.map(r => `<tr style="border-bottom:1px solid var(--border-color);">
              <td style="padding:6px;">${r.agent_role}</td>
              <td>${r.calls}</td><td>${r.est_input_tokens}</td><td>${r.est_output_tokens}</td>
              <td>${r.avg_latency_ms}</td><td>${r.failures}</td>
            </tr>`).join('')}
          </tbody>
        </table>`;
    } catch (e) {
      box.textContent = `사용량 조회 실패: ${e.message}`;
    }
  }
  container.querySelector('#btn-refresh-usage')?.addEventListener('click', loadUsageSummary);

  loadProjectDetails();
  return container;
}
