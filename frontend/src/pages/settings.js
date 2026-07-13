// Project Settings Page (per-agent LLM configurations)
import { api } from '../api/client.js';
import { showToast } from '../components/toast.js';
import { showSpinner, hideSpinner } from '../components/loading.js';

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
          <input class="form-control" type="text" id="edit-model-custom" placeholder="예: deepseek-chat, qwen-max">
        </div>

        <!-- Custom Base URL (hidden by default) -->
        <div class="form-group" id="edit-baseurl-container" style="display: none;">
          <label class="form-label" for="edit-baseurl">API Base URL</label>
          <input class="form-control" type="url" id="edit-baseurl" placeholder="예: https://api.deepseek.com/v1">
        </div>
        
        <div class="form-group" style="margin-bottom: 0;">
          <label class="form-label" for="edit-apikey">공통 API Key (선택)</label>
          <input class="form-control" type="password" id="edit-apikey" placeholder="이미 키가 암호화 적재되어 있는 경우 갱신할 때만 새로 입력해 주세요.">
        </div>
      </div>
      
      <!-- Per-Agent Advanced Configuration -->
      <div class="glass-card" style="padding: 24px;">
        <h4 style="font-family: var(--font-heading); font-size: 1.15rem; margin-bottom: 8px; display: flex; align-items: center; gap: 8px;">
          <span>🤖</span> 에이전트별 세부 오버라이드 설정
        </h4>
        <p style="color: var(--text-secondary); font-size: 0.85rem; margin-bottom: 20px;">
          기획, 집필, 일관성 평가 등 에이전트 역할별로 서로 다른 AI 모델과 고유 API 키를 오버라이드할 수 있습니다. (미선택 시 기본 모델 적용)
        </p>
        
        <div style="display: flex; flex-direction: column; gap: 16px;" id="agents-config-list">
          <!-- Populated dynamically -->
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

  const agents = [
    { key: 'plotter', name: '🎯 Plotter (시놉시스 분석 및 씬 기획 담당)' },
    { key: 'writer', name: '✍️ Writer (각 씬의 소설 본문 집필 담당)' },
    { key: 'judge', name: '⚖️ Judge (세계관 설정집 일관성 검사 담당)' },
    { key: 'editor', name: '📐 Editor (비평 피드백 반영 원고 퇴고 담당)' },
    { key: 'reviewer', name: '📝 Reviewer (집필 완료 후 종합 가독성 평가 담당)' }
  ];

  // Populate models list dynamically, handle custom value restoration
  function populateModelDropdown(selectElement, providerVal, currentVal = '', customInputContainer = null, customInputElement = null) {
    selectElement.innerHTML = '';
    const opts = modelOptions[providerVal] || [];
    
    // Check if current value is standard
    const isStandardVal = opts.some(opt => opt.value === currentVal);
    
    opts.forEach(opt => {
      const o = document.createElement('option');
      o.value = opt.value;
      o.textContent = opt.text;
      if (isStandardVal && opt.value === currentVal) {
        o.selected = true;
      }
      selectElement.appendChild(o);
    });
    
    if (providerVal === 'custom_openai') {
      const customOpt = selectElement.querySelector('option[value="custom-model"]');
      if (customOpt) customOpt.selected = true;
      if (customInputContainer) customInputContainer.style.display = 'block';
      if (customInputElement && currentVal) customInputElement.value = currentVal;
    } else if (currentVal && !isStandardVal && currentVal !== 'custom-model') {
      // It is a custom model name (e.g. gpt-4o-custom) under standard provider
      const customOpt = selectElement.querySelector('option[value="custom-model"]');
      if (customOpt) customOpt.selected = true;
      if (customInputContainer) {
        customInputContainer.style.display = 'block';
      }
      if (customInputElement) {
        customInputElement.value = currentVal;
      }
    } else if (currentVal === 'custom-model') {
      const customOpt = selectElement.querySelector('option[value="custom-model"]');
      if (customOpt) customOpt.selected = true;
      if (customInputContainer) customInputContainer.style.display = 'block';
    } else {
      if (customInputContainer) {
        customInputContainer.style.display = 'none';
      }
    }
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
      const data = projectData[agent.key] || {};
      const hasOverride = !!(data.llm_provider || data.llm_model);
      
      const el = document.createElement('div');
      el.className = 'agent-card';
      el.style.border = '1px solid var(--border-color)';
      el.style.borderRadius = 'var(--radius-sm)';
      el.style.padding = '16px';
      el.style.backgroundColor = 'var(--bg-app)';
      
      const hasKeyField = `has_${agent.key}_api_key`;
      const hasKey = !!projectData[hasKeyField];

      const keyVal = data.api_key_override || '';
      const { apiKey, baseUrl } = parseApiKeyField(keyVal);

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
        if (chk.checked && !provSelect.value) {
          provSelect.value = 'openai';
          populateModelDropdown(modSelect, 'openai', data.llm_model || '', customModelCont, customModelIn);
        }
        toggleAgentCustomFields();
      });

      // Handle provider change
      provSelect.addEventListener('change', () => {
        populateModelDropdown(modSelect, provSelect.value, data.llm_model || '', customModelCont, customModelIn);
        toggleAgentCustomFields();
      });

      // Handle model selection change (custom model visibility toggle)
      modSelect.addEventListener('change', () => {
        toggleAgentCustomFields();
      });

      // Initial populate
      if (hasOverride) {
        provSelect.value = data.llm_provider || 'openai';
        populateModelDropdown(modSelect, provSelect.value, data.llm_model || '', customModelCont, customModelIn);
        
        if (provSelect.value === 'custom_openai') {
          baseurlIn.value = baseUrl || '';
        }
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
    
    let llm_model = modelSelect.value;
    if (llm_model === 'custom-model' || llm_provider === 'custom_openai') {
      llm_model = customModelInput.value.trim() || 'custom-model';
    }

    let raw_api_key = container.querySelector('#edit-apikey').value.trim();
    let api_key_override = raw_api_key || undefined;

    if (llm_provider === 'custom_openai') {
      const base_url = baseurlInput.value.trim();
      if (base_url) {
        api_key_override = `${raw_api_key}::${base_url}`;
      }
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
      api_key_override
    };

    // Construct agent overrides
    agents.forEach(agent => {
      const chk = container.querySelector(`#chk-override-${agent.key}`);
      if (chk && chk.checked) {
        const provider = container.querySelector(`#override-prov-${agent.key}`).value;
        let model = container.querySelector(`#override-model-${agent.key}`).value;
        
        if (model === 'custom-model' || provider === 'custom_openai') {
          model = container.querySelector(`#override-model-custom-${agent.key}`).value.trim() || 'custom-model';
        }

        let raw_key = container.querySelector(`#override-key-${agent.key}`).value.trim();
        let api_key = raw_key || undefined;

        if (provider === 'custom_openai') {
          const base_url = container.querySelector(`#override-baseurl-${agent.key}`).value.trim();
          if (base_url) {
            api_key = `${raw_key}::${base_url}`;
          }
        }

        payload[agent.key] = {
          llm_provider: provider,
          llm_model: model,
          api_key_override: api_key
        };
      } else {
        payload[agent.key] = null;
      }
    });

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

  loadProjectDetails();
  return container;
}
