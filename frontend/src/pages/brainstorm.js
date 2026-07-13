// AI Planning Partner - Brainstorming page
import { api } from '../api/client.js';
import { showToast } from '../components/toast.js';
import { showSpinner, hideSpinner } from '../components/loading.js';

export async function renderBrainstorm(projectId) {
  const container = document.createElement('div');
  container.className = 'animate-fade-in';
  
  container.innerHTML = `
    <div class="glass-card" style="padding: 28px; margin-bottom: 24px;">
      <h3 style="font-family: var(--font-heading); font-size: 1.3rem; margin-bottom: 12px; display: flex; align-items: center; gap: 8px;">
        <span>💡</span> AI 기획 파트너
      </h3>
      <p style="color: var(--text-secondary); font-size: 0.9rem; line-height: 1.5; margin-bottom: 20px;">
        작성된 소설 시놉시스를 바탕으로 AI가 어울리는 세계관 설정과 주요 캐릭터 후보를 추천합니다. 추가 지시 사항을 입력하여 제안 방향을 조율할 수 있습니다.
      </p>
      
      <div class="form-group">
        <label class="form-label" for="brainstorm-instruction">AI에게 보낼 추가 지시 사항 (선택)</label>
        <textarea class="form-control" id="brainstorm-instruction" placeholder="예: '주인공은 소심하지만 특별한 초능력을 가졌고, 디스토피아 분위기의 미래 도시를 배경으로 해줘.'" style="height: 80px; resize: none;"></textarea>
      </div>
      
      <button class="btn btn-primary" id="btn-run-brainstorm" style="width: 100%; height: 44px; font-weight: 600;">
        🤖 AI 기획 추천 생성 시작
      </button>
    </div>
    
    <div id="brainstorm-results" style="display: none;" class="animate-fade-in">
      <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 24px; margin-bottom: 24px;" class="grid-cols-2">
        
        <!-- Lore suggestions panel -->
        <div class="glass-card" style="padding: 24px;">
          <h4 style="font-family: var(--font-heading); font-size: 1.1rem; margin-bottom: 16px; display: flex; align-items: center; justify-content: space-between;">
            <span>🌍 추천 세계관 설정집</span>
            <button class="btn btn-secondary" id="btn-select-all-lores" style="padding: 4px 10px; font-size: 0.8rem;">전체 선택</button>
          </h4>
          <div id="lore-suggestions-list" style="display: flex; flex-direction: column; gap: 12px; max-height: 400px; overflow-y: auto; padding-right: 4px;">
            <!-- Lore items -->
          </div>
        </div>
        
        <!-- Character suggestions panel -->
        <div class="glass-card" style="padding: 24px;">
          <h4 style="font-family: var(--font-heading); font-size: 1.1rem; margin-bottom: 16px; display: flex; align-items: center; justify-content: space-between;">
            <span>👥 추천 캐릭터 시트</span>
            <button class="btn btn-secondary" id="btn-select-all-chars" style="padding: 4px 10px; font-size: 0.8rem;">전체 선택</button>
          </h4>
          <div id="char-suggestions-list" style="display: flex; flex-direction: column; gap: 12px; max-height: 400px; overflow-y: auto; padding-right: 4px;">
            <!-- Character items -->
          </div>
        </div>
        
      </div>
      
      <div style="display: flex; justify-content: flex-end; gap: 12px; padding: 16px 24px;" class="glass-card">
        <button class="btn btn-secondary" id="btn-reset-suggestions">초기화</button>
        <button class="btn btn-primary" id="btn-apply-suggestions" style="font-weight: 600;">
          📥 선택한 기획 요소를 세계관/캐릭터에 적용하기
        </button>
      </div>
    </div>
  `;

  const runBtn = container.querySelector('#btn-run-brainstorm');
  const resultsDiv = container.querySelector('#brainstorm-results');
  const loresList = container.querySelector('#lore-suggestions-list');
  const charsList = container.querySelector('#char-suggestions-list');
  const applyBtn = container.querySelector('#btn-apply-suggestions');
  const resetBtn = container.querySelector('#btn-reset-suggestions');
  const selectAllLoresBtn = container.querySelector('#btn-select-all-lores');
  const selectAllCharsBtn = container.querySelector('#btn-select-all-chars');

  let suggestedLores = [];
  let suggestedChars = [];

  // Generate brainstorm results
  runBtn.addEventListener('click', async () => {
    const instruction = container.querySelector('#brainstorm-instruction').value.trim();
    showSpinner('AI가 세계관과 캐릭터 기획을 추천하는 중입니다...');
    
    try {
      const data = await api.post(`/projects/${projectId}/brainstorm`, {
        user_instruction: instruction || undefined
      });
      hideSpinner();
      
      suggestedLores = data.lores || [];
      suggestedChars = data.characters || [];
      
      if (suggestedLores.length === 0 && suggestedChars.length === 0) {
        showToast('AI가 기획 제안을 생성하지 못했습니다. 시놉시스를 보강해 주세요.', 'info');
        return;
      }
      
      renderSuggestions();
      resultsDiv.style.display = 'block';
      resultsDiv.scrollIntoView({ behavior: 'smooth' });
      showToast('AI 기획 추천안이 생성되었습니다.', 'success');
    } catch (err) {
      hideSpinner();
      showToast(`기획 추천 실패: ${err.message}`, 'error');
    }
  });

  function renderSuggestions() {
    loresList.innerHTML = suggestedLores.length === 0 
      ? '<p style="color: var(--text-muted); font-size: 0.9rem; text-align: center; padding: 20px;">제안된 설정이 없습니다.</p>' 
      : '';
      
    charsList.innerHTML = suggestedChars.length === 0 
      ? '<p style="color: var(--text-muted); font-size: 0.9rem; text-align: center; padding: 20px;">제안된 캐릭터가 없습니다.</p>' 
      : '';

    suggestedLores.forEach((lore, idx) => {
      const el = document.createElement('div');
      el.style.border = '1px solid var(--border-color)';
      el.style.borderRadius = 'var(--radius-sm)';
      el.style.padding = '12px';
      el.style.backgroundColor = 'var(--bg-app)';
      el.style.display = 'flex';
      el.style.gap = '12px';
      
      el.innerHTML = `
        <input type="checkbox" id="lore-chk-${idx}" class="suggestion-chk" data-type="lore" data-index="${idx}" checked style="margin-top: 4px; cursor: pointer;">
        <label for="lore-chk-${idx}" style="cursor: pointer; flex: 1;">
          <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 4px;">
            <strong style="color: var(--text-primary); font-size: 0.95rem;">${lore.keyword}</strong>
            <span class="badge badge-primary" style="font-size: 0.7rem;">${lore.category}</span>
          </div>
          <p style="color: var(--text-secondary); font-size: 0.85rem; line-height: 1.4;">${lore.description}</p>
        </label>
      `;
      loresList.appendChild(el);
    });

    suggestedChars.forEach((char, idx) => {
      const el = document.createElement('div');
      el.style.border = '1px solid var(--border-color)';
      el.style.borderRadius = 'var(--radius-sm)';
      el.style.padding = '12px';
      el.style.backgroundColor = 'var(--bg-app)';
      el.style.display = 'flex';
      el.style.gap = '12px';
      
      let importanceBadge = 'minor';
      if (char.importance === 'protagonist') importanceBadge = '<span class="badge badge-primary">주인공</span>';
      else if (char.importance === 'deuteragonist') importanceBadge = '<span class="badge badge-success">조연</span>';
      else importanceBadge = `<span class="badge badge-secondary">${char.importance}</span>`;
      
      el.innerHTML = `
        <input type="checkbox" id="char-chk-${idx}" class="suggestion-chk" data-type="char" data-index="${idx}" checked style="margin-top: 4px; cursor: pointer;">
        <label for="char-chk-${idx}" style="cursor: pointer; flex: 1;">
          <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 4px;">
            <strong style="color: var(--text-primary); font-size: 0.95rem;">${char.name}</strong>
            ${importanceBadge}
          </div>
          <p style="color: var(--text-secondary); font-size: 0.85rem; line-height: 1.4;">${char.description}</p>
        </label>
      `;
      charsList.appendChild(el);
    });
  }

  // Select all handlers
  let allLoresChecked = true;
  selectAllLoresBtn.addEventListener('click', () => {
    allLoresChecked = !allLoresChecked;
    loresList.querySelectorAll('input[type="checkbox"]').forEach(chk => {
      chk.checked = allLoresChecked;
    });
    selectAllLoresBtn.textContent = allLoresChecked ? '전체 해제' : '전체 선택';
  });

  let allCharsChecked = true;
  selectAllCharsBtn.addEventListener('click', () => {
    allCharsChecked = !allCharsChecked;
    charsList.querySelectorAll('input[type="checkbox"]').forEach(chk => {
      chk.checked = allCharsChecked;
    });
    selectAllCharsBtn.textContent = allCharsChecked ? '전체 해제' : '전체 선택';
  });

  resetBtn.addEventListener('click', () => {
    resultsDiv.style.display = 'none';
    loresList.innerHTML = '';
    charsList.innerHTML = '';
    suggestedLores = [];
    suggestedChars = [];
    container.querySelector('#brainstorm-instruction').value = '';
  });

  // Apply selected elements to Project Database
  applyBtn.addEventListener('click', async () => {
    const selectedLores = [];
    const selectedChars = [];

    loresList.querySelectorAll('input[type="checkbox"]:checked').forEach(chk => {
      const idx = parseInt(chk.getAttribute('data-index'));
      selectedLores.push(suggestedLores[idx]);
    });

    charsList.querySelectorAll('input[type="checkbox"]:checked').forEach(chk => {
      const idx = parseInt(chk.getAttribute('data-index'));
      selectedChars.push(suggestedChars[idx]);
    });

    if (selectedLores.length === 0 && selectedChars.length === 0) {
      showToast('선택된 항목이 없습니다. 적용할 기획 요소를 1개 이상 체크해 주세요.', 'error');
      return;
    }

    showSpinner('선택한 기획 요소를 데이터베이스에 등록 중...');
    
    try {
      const response = await api.post(`/projects/${projectId}/brainstorm/apply`, {
        lores: selectedLores,
        characters: selectedChars
      });
      hideSpinner();
      
      const addedLores = response.added_lores || 0;
      const addedChars = response.added_characters || 0;
      
      showToast(`성공적으로 적용되었습니다! (설정집: ${addedLores}건, 캐릭터: ${addedChars}건 등록)`, 'success');
      
      // Clear results display
      resultsDiv.style.display = 'none';
      container.querySelector('#brainstorm-instruction').value = '';
    } catch (err) {
      hideSpinner();
      showToast(`기획 적용 실패: ${err.message}`, 'error');
    }
  });

  return container;
}
