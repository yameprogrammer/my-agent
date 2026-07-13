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
      { value: 'gpt-4o-mini', text: 'gpt-4o-mini (속도/비용 효율)' },
      { value: 'gpt-4o', text: 'gpt-4o (고성능)' },
      { value: 'o1-mini', text: 'o1-mini (추론 특화)' }
    ],
    google: [
      { value: 'gemini-1.5-flash', text: 'gemini-1.5-flash (속도 최적)' },
      { value: 'gemini-1.5-pro', text: 'gemini-1.5-pro (대형 콘텍스트)' }
    ],
    anthropic: [
      { value: 'claude-3-5-haiku-20241022', text: 'claude-3-5-haiku (빠른 윤문)' },
      { value: 'claude-3-5-sonnet-20241022', text: 'claude-3-5-sonnet (종합 1위)' }
    ],
    ollama: [
      { value: 'llama3:8b', text: 'Llama 3 (8B)' },
      { value: 'gemma2:9b', text: 'Gemma 2 (9B)' },
      { value: 'mistral', text: 'Mistral' }
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
            </select>
          </div>
          <div class="form-group">
            <label class="form-label" for="edit-model">기본 모델</label>
            <select class="form-control" id="edit-model"></select>
          </div>
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
          <!-- Populated with plotter, writer, judge, editor, reviewer panels -->
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
  const agentsList = container.querySelector('#agents-config-list');

  const agents = [
    { key: 'plotter', name: '🎯 Plotter (시놉시스 분석 및 씬 기획 담당)' },
    { key: 'writer', name: '✍️ Writer (각 씬의 소설 본문 집필 담당)' },
    { key: 'judge', name: '⚖️ Judge (세계관 설정집 일관성 검사 담당)' },
    { key: 'editor', name: '📐 Editor (비평 피드백 반영 원고 퇴고 담당)' },
    { key: 'reviewer', name: '📝 Reviewer (집필 완료 후 종합 가독성 평가 담당)' }
  ];

  function populateModelDropdown(selectElement, providerVal, currentVal = '') {
    selectElement.innerHTML = '';
    (modelOptions[providerVal] || []).forEach(opt => {
      const o = document.createElement('option');
      o.value = opt.value;
      o.textContent = opt.text;
      if (opt.value === currentVal) o.selected = true;
      selectElement.appendChild(o);
    });
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
      
      providerSelect.value = projectData.llm_provider || 'openai';
      populateModelDropdown(modelSelect, providerSelect.value, projectData.llm_model);
      
      if (projectData.has_api_key) {
        container.querySelector('#edit-apikey').placeholder = '🔑 API 키가 이미 등록되어 있습니다. (덮어쓸 경우만 새로 입력)';
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
      // Find override state for this agent in projectData
      // The schema returns has_plotter_api_key, has_writer_api_key etc.
      // And plotter, writer sub-objects (usually containing provider/model)
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
            </select>
          </div>
          <div class="form-group" style="margin-bottom: 0;">
            <label class="form-label" style="font-size: 0.8rem;" for="override-model-${agent.key}">모델명</label>
            <select class="form-control" id="override-model-${agent.key}" style="padding: 6px 10px; font-size: 0.85rem;"></select>
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

      // Handle checkbox change
      chk.addEventListener('change', () => {
        panel.style.display = chk.checked ? 'grid' : 'none';
        if (chk.checked && !provSelect.value) {
          provSelect.value = 'openai';
          populateModelDropdown(modSelect, 'openai', data.llm_model || '');
        }
      });

      // Handle provider change
      provSelect.addEventListener('change', () => {
        populateModelDropdown(modSelect, provSelect.value, data.llm_model || '');
      });

      // Initial populate
      if (hasOverride) {
        provSelect.value = data.llm_provider || 'openai';
        populateModelDropdown(modSelect, provSelect.value, data.llm_model || '');
      }

      agentsList.appendChild(el);
    });
  }

  // Handle global provider change
  providerSelect.addEventListener('change', () => {
    populateModelDropdown(modelSelect, providerSelect.value);
  });

  // Handle form submit
  form.addEventListener('submit', async (e) => {
    e.preventDefault();

    const title = container.querySelector('#edit-title').value.trim();
    const synopsis = container.querySelector('#edit-synopsis').value.trim() || undefined;
    const llm_provider = providerSelect.value;
    const llm_model = modelSelect.value;
    const api_key_override = container.querySelector('#edit-apikey').value.trim() || undefined;

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
        const model = container.querySelector(`#override-model-${agent.key}`).value;
        const api_key = container.querySelector(`#override-key-${agent.key}`).value.trim() || undefined;

        payload[agent.key] = {
          llm_provider: provider,
          llm_model: model,
          api_key_override: api_key
        };
      } else {
        // If override is off, explicitly set to null/empty values or omit to fallback
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
