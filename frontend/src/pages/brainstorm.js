// AI Planning Partner - Brainstorming page
import { api } from '../api/client.js';
import { showToast } from '../components/toast.js';
import { showSpinner, hideSpinner } from '../components/loading.js';
import { createModal } from '../components/modal.js';

export async function renderBrainstorm(projectId) {
  const container = document.createElement('div');
  container.className = 'animate-fade-in';
  
  container.innerHTML = `
    <div class="glass-card" style="padding: 28px; margin-bottom: 24px;">
      <h3 style="font-family: var(--font-heading); font-size: 1.3rem; margin-bottom: 12px; display: flex; align-items: center; gap: 8px;">
        <span>💡</span> AI 기획 파트너
      </h3>
      <p style="color: var(--text-secondary); font-size: 0.9rem; line-height: 1.5; margin-bottom: 20px;">
        시놉시스를 바탕으로 세계관·캐릭터를 추천합니다.
        <strong>추가 지시(피드백)</strong>에 기존 설정/인물 수정이 필요하면, AI가 동일 키워드·이름으로
        <strong>수정안(update)</strong>을 만들어 주고. 적용 시 DB에 반영됩니다.
      </p>
      
      <div class="form-group">
        <label class="form-label" for="brainstorm-instruction">AI에게 보낼 추가 지시 / 피드백 (선택)</label>
        <textarea class="form-control" id="brainstorm-instruction" placeholder="예: '주인공 아셀을 소심하고 내향적으로 바꿔줘. 마법 체계는 더 엄격한 대가로 작동하게 수정해줘. 라이벌 캐릭터 1명 추가.'" style="height: 90px; resize: none;"></textarea>
      </div>
      
      <div style="display: flex; flex-direction: column; gap: 10px;">
        <button class="btn btn-primary" id="btn-run-brainstorm" style="width: 100%; height: 44px; font-weight: 600;">
          🤖 AI 기획 추천 / 수정안 생성
        </button>
        <button class="btn btn-secondary" id="btn-audit-planning" style="width: 100%; height: 44px; font-weight: 600; border-color: var(--primary); color: var(--primary);">
          🔍 기획 &amp; 인물 검수 에이전트
        </button>
      </div>
      <p style="color: var(--text-muted); font-size: 0.78rem; margin-top: 10px; line-height: 1.4;">
        생성 시 DB에 저장된 설정·캐릭터와 아래 미적용 추천안을 함께 참고합니다.
        배지 <strong>✏️ 기존 수정</strong> 항목을 적용하면 저장본 설명이 교체됩니다.
      </p>
    </div>
    
    <div id="brainstorm-results" style="display: none;" class="animate-fade-in">
      <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 24px; margin-bottom: 24px;" class="grid-cols-2">
        
        <!-- Lore suggestions panel -->
        <div class="glass-card" style="padding: 24px;">
          <h4 style="font-family: var(--font-heading); font-size: 1.1rem; margin-bottom: 16px; display: flex; align-items: center; justify-content: space-between;">
            <span>🌍 추천·수정 세계관</span>
            <button class="btn btn-secondary" id="btn-select-all-lores" style="padding: 4px 10px; font-size: 0.8rem;">전체 선택</button>
          </h4>
          <div id="lore-suggestions-list" style="display: flex; flex-direction: column; gap: 12px; max-height: 400px; overflow-y: auto; padding-right: 4px;">
            <!-- Lore items -->
          </div>
        </div>
        
        <!-- Character suggestions panel -->
        <div class="glass-card" style="padding: 24px;">
          <h4 style="font-family: var(--font-heading); font-size: 1.1rem; margin-bottom: 16px; display: flex; align-items: center; justify-content: space-between;">
            <span>👥 추천·수정 캐릭터</span>
            <button class="btn btn-secondary" id="btn-select-all-chars" style="padding: 4px 10px; font-size: 0.8rem;">전체 선택</button>
          </h4>
          <div id="char-suggestions-list" style="display: flex; flex-direction: column; gap: 12px; max-height: 400px; overflow-y: auto; padding-right: 4px;">
            <!-- Character items -->
          </div>
        </div>
        
      </div>
      
      <div style="display: flex; justify-content: flex-end; gap: 12px; padding: 16px 24px; flex-wrap: wrap;" class="glass-card">
        <button class="btn btn-secondary" id="btn-reset-suggestions">초기화</button>
        <button class="btn btn-primary" id="btn-apply-suggestions" style="font-weight: 600;">
          📥 선택 항목 적용 (신규 등록 / 기존 수정)
        </button>
      </div>
    </div>
  `;

  const runBtn = container.querySelector('#btn-run-brainstorm');
  const auditBtn = container.querySelector('#btn-audit-planning');
  const resultsDiv = container.querySelector('#brainstorm-results');
  const loresList = container.querySelector('#lore-suggestions-list');
  const charsList = container.querySelector('#char-suggestions-list');
  const applyBtn = container.querySelector('#btn-apply-suggestions');
  const resetBtn = container.querySelector('#btn-reset-suggestions');
  const selectAllLoresBtn = container.querySelector('#btn-select-all-lores');
  const selectAllCharsBtn = container.querySelector('#btn-select-all-chars');

  let suggestedLores = [];
  let suggestedChars = [];

  function stripMeta(item) {
    // apply API에는 핵심 필드만 전달
    if (item.keyword !== undefined) {
      return {
        keyword: item.keyword,
        category: item.category,
        description: item.description
      };
    }
    return {
      name: item.name,
      importance: item.importance,
      description: item.description
    };
  }

  function getSelectedSuggestions() {
    const selectedLores = [];
    const selectedChars = [];

    loresList.querySelectorAll('input[type="checkbox"]:checked').forEach(chk => {
      const idx = parseInt(chk.getAttribute('data-index'), 10);
      if (!Number.isNaN(idx) && suggestedLores[idx]) {
        selectedLores.push(stripMeta(suggestedLores[idx]));
      }
    });

    charsList.querySelectorAll('input[type="checkbox"]:checked').forEach(chk => {
      const idx = parseInt(chk.getAttribute('data-index'), 10);
      if (!Number.isNaN(idx) && suggestedChars[idx]) {
        selectedChars.push(stripMeta(suggestedChars[idx]));
      }
    });

    return { selectedLores, selectedChars };
  }

  function changeTypeBadge(item) {
    if (item.change_type === 'update') {
      return `<span class="badge" style="font-size:0.7rem; background:var(--accent); color:#fff;">✏️ 기존 수정</span>`;
    }
    return `<span class="badge badge-success" style="font-size:0.7rem;">✨ 신규</span>`;
  }

  function escapeHtml(text) {
    return String(text ?? '')
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  function showPlanningAuditModal(report) {
    const score = report.score ?? 0;
    const scoreColor = score >= 80 ? 'var(--secondary)' : score >= 60 ? 'var(--primary)' : 'var(--accent)';
    const statusBadge = report.is_passed
      ? `<span class="badge badge-success" style="font-size:0.85rem; padding:4px 8px;">검수 통과 (Passed)</span>`
      : `<span class="badge" style="font-size:0.85rem; padding:4px 8px; background:var(--accent); color:#fff;">보완 필요 (Warning)</span>`;

    const listSection = (title, items, emptyLabel, accent) => {
      if (!items || items.length === 0) {
        return `
          <div style="margin-bottom:14px;">
            <strong style="font-size:0.85rem; color:${accent}; display:block; margin-bottom:6px;">${title}</strong>
            <p style="font-size:0.78rem; color:var(--text-muted); margin:0; font-style:italic;">${emptyLabel}</p>
          </div>`;
      }
      return `
        <div style="margin-bottom:14px;">
          <strong style="font-size:0.85rem; color:${accent}; display:block; margin-bottom:6px;">${title}</strong>
          <ul style="margin:0 0 0 18px; padding:0; font-size:0.8rem; color:var(--text-secondary); line-height:1.5;">
            ${items.map(i => `<li>${escapeHtml(i)}</li>`).join('')}
          </ul>
        </div>`;
    };

    createModal({
      title: '🔍 기획 & 인물 검수 진단서',
      content: `
        <div style="display:flex; align-items:center; justify-content:space-between; margin-bottom:16px; background:var(--bg-app); padding:12px 16px; border-radius:var(--radius-sm);">
          <div>
            <span style="font-size:0.75rem; color:var(--text-muted); display:block; margin-bottom:2px;">사전 진단 결과</span>
            ${statusBadge}
          </div>
          <div style="text-align:right;">
            <span style="font-size:0.75rem; color:var(--text-muted); display:block; margin-bottom:2px;">기획 신뢰도 점수</span>
            <strong style="font-size:1.8rem; color:${scoreColor}; font-family:var(--font-heading);">${score} / 100</strong>
          </div>
        </div>

        <div style="margin-bottom:18px;">
          <strong style="font-size:0.9rem; color:var(--primary); display:block; margin-bottom:6px;">📝 종합 검수 리포트</strong>
          <p style="font-size:0.82rem; color:var(--text-secondary); line-height:1.6; background:rgba(var(--primary-rgb),0.02); border-left:4px solid var(--primary); padding:10px 14px; margin:0; border-radius:0 var(--radius-sm) var(--radius-sm) 0; white-space:pre-wrap;">${escapeHtml(report.summary || '의견 없음')}</p>
        </div>

        <div style="max-height:300px; overflow-y:auto; padding-right:4px;">
          ${listSection('👤 인물 설계 이슈', report.character_issues, '인물 설계 문제는 발견되지 않았습니다.', 'var(--accent)')}
          ${listSection('🌍 세계관 설정 이슈', report.lore_issues, '세계관 설정 문제는 발견되지 않았습니다.', 'var(--primary)')}
          ${listSection('⚡ 교차 모순 / 충돌', report.contradictions, '설정 간 모순은 발견되지 않았습니다.', 'var(--accent)')}
          ${listSection('💡 개선 제안', report.suggestions, '추가 제안 사항이 없습니다.', 'var(--secondary)')}
        </div>
      `,
      confirmText: '확인',
      cancelText: '닫기',
      onConfirm: () => {}
    });
  }

  // Generate brainstorm results (create + update of existing)
  runBtn.addEventListener('click', async () => {
    const instruction = container.querySelector('#brainstorm-instruction').value.trim();
    showSpinner('AI가 기존 기획을 참고해 추천·수정안을 작성 중입니다...');
    
    try {
      // 화면에 떠 있는 미적용 추천도 컨텍스트로 전달 → 연속 피드백 루프 지원
      const data = await api.post(`/projects/${projectId}/brainstorm`, {
        user_instruction: instruction || undefined,
        current_lores: suggestedLores.map(stripMeta),
        current_characters: suggestedChars.map(stripMeta)
      });
      hideSpinner();
      
      suggestedLores = data.lores || [];
      suggestedChars = data.characters || [];
      
      if (suggestedLores.length === 0 && suggestedChars.length === 0) {
        showToast('AI가 기획 제안을 생성하지 못했습니다. 시놉시스나 피드백을 보강해 주세요.', 'info');
        return;
      }
      
      renderSuggestions();
      resultsDiv.style.display = 'block';
      resultsDiv.scrollIntoView({ behavior: 'smooth' });

      const updates = data.update_count ?? (
        [...suggestedLores, ...suggestedChars].filter(x => x.change_type === 'update').length
      );
      const creates = data.create_count ?? (
        [...suggestedLores, ...suggestedChars].filter(x => x.change_type !== 'update').length
      );

      if (updates > 0) {
        showToast(`기획안 준비 완료 — 기존 수정 ${updates}건, 신규 ${creates}건. 적용 시 DB에 반영됩니다.`, 'success');
      } else {
        showToast(`신규 기획 추천 ${creates}건이 생성되었습니다.`, 'success');
      }
    } catch (err) {
      hideSpinner();
      showToast(`기획 추천 실패: ${err.message}`, 'error');
    }
  });

  // Planning & character audit
  auditBtn.addEventListener('click', async () => {
    const { selectedLores, selectedChars } = getSelectedSuggestions();

    showSpinner('기획 & 인물 검수 에이전트가 설정집과 캐릭터를 교차 진단 중입니다...');
    try {
      const report = await api.post(`/projects/${projectId}/brainstorm/audit`, {
        lores: selectedLores,
        characters: selectedChars
      });
      hideSpinner();
      showToast('기획·인물 사전 검수가 완료되었습니다.', 'success');
      showPlanningAuditModal(report);
    } catch (err) {
      hideSpinner();
      showToast(err.message || '기획·인물 검수에 실패했습니다.', 'error');
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
      const isUpdate = lore.change_type === 'update';
      el.style.border = isUpdate ? '1px solid var(--accent)' : '1px solid var(--border-color)';
      el.style.borderRadius = 'var(--radius-sm)';
      el.style.padding = '12px';
      el.style.backgroundColor = isUpdate ? 'rgba(var(--primary-rgb), 0.04)' : 'var(--bg-app)';
      el.style.display = 'flex';
      el.style.gap = '12px';
      
      const summary = lore.change_summary
        ? `<p style="color: var(--text-muted); font-size: 0.78rem; margin-top: 6px; font-style: italic;">→ ${escapeHtml(lore.change_summary)}</p>`
        : '';

      el.innerHTML = `
        <input type="checkbox" id="lore-chk-${idx}" class="suggestion-chk" data-type="lore" data-index="${idx}" checked style="margin-top: 4px; cursor: pointer;">
        <label for="lore-chk-${idx}" style="cursor: pointer; flex: 1;">
          <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 4px; gap: 8px; flex-wrap: wrap;">
            <strong style="color: var(--text-primary); font-size: 0.95rem;">${escapeHtml(lore.keyword)}</strong>
            <span style="display:flex; gap:6px; align-items:center;">
              ${changeTypeBadge(lore)}
              <span class="badge badge-primary" style="font-size: 0.7rem;">${escapeHtml(lore.category)}</span>
            </span>
          </div>
          <p style="color: var(--text-secondary); font-size: 0.85rem; line-height: 1.4; margin:0;">${escapeHtml(lore.description)}</p>
          ${summary}
        </label>
      `;
      loresList.appendChild(el);
    });

    suggestedChars.forEach((char, idx) => {
      const el = document.createElement('div');
      const isUpdate = char.change_type === 'update';
      el.style.border = isUpdate ? '1px solid var(--accent)' : '1px solid var(--border-color)';
      el.style.borderRadius = 'var(--radius-sm)';
      el.style.padding = '12px';
      el.style.backgroundColor = isUpdate ? 'rgba(var(--primary-rgb), 0.04)' : 'var(--bg-app)';
      el.style.display = 'flex';
      el.style.gap = '12px';
      
      let importanceBadge = `<span class="badge badge-secondary">${escapeHtml(char.importance)}</span>`;
      if (char.importance === 'protagonist') importanceBadge = '<span class="badge badge-primary">주인공</span>';
      else if (char.importance === 'deuteragonist') importanceBadge = '<span class="badge badge-success">조연</span>';

      const summary = char.change_summary
        ? `<p style="color: var(--text-muted); font-size: 0.78rem; margin-top: 6px; font-style: italic;">→ ${escapeHtml(char.change_summary)}</p>`
        : '';
      
      el.innerHTML = `
        <input type="checkbox" id="char-chk-${idx}" class="suggestion-chk" data-type="char" data-index="${idx}" checked style="margin-top: 4px; cursor: pointer;">
        <label for="char-chk-${idx}" style="cursor: pointer; flex: 1;">
          <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 4px; gap: 8px; flex-wrap: wrap;">
            <strong style="color: var(--text-primary); font-size: 0.95rem;">${escapeHtml(char.name)}</strong>
            <span style="display:flex; gap:6px; align-items:center;">
              ${changeTypeBadge(char)}
              ${importanceBadge}
            </span>
          </div>
          <p style="color: var(--text-secondary); font-size: 0.85rem; line-height: 1.4; margin:0;">${escapeHtml(char.description)}</p>
          ${summary}
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

  // Apply selected elements to Project Database (create + upsert update)
  applyBtn.addEventListener('click', async () => {
    const { selectedLores, selectedChars } = getSelectedSuggestions();

    if (selectedLores.length === 0 && selectedChars.length === 0) {
      showToast('선택된 항목이 없습니다. 적용할 기획 요소를 1개 이상 체크해 주세요.', 'error');
      return;
    }

    showSpinner('선택한 기획 요소를 등록·수정 반영 중...');
    
    try {
      const response = await api.post(`/projects/${projectId}/brainstorm/apply`, {
        lores: selectedLores,
        characters: selectedChars
      });
      hideSpinner();
      
      const addedLores = response.added_lores || 0;
      const updatedLores = response.updated_lores || 0;
      const addedChars = response.added_characters || 0;
      const updatedChars = response.updated_characters || 0;
      
      showToast(
        `적용 완료 — 설정 신규 ${addedLores}/수정 ${updatedLores}, 캐릭터 신규 ${addedChars}/수정 ${updatedChars}`,
        'success'
      );
      
      // Clear results display
      resultsDiv.style.display = 'none';
      suggestedLores = [];
      suggestedChars = [];
      container.querySelector('#brainstorm-instruction').value = '';
    } catch (err) {
      hideSpinner();
      showToast(`기획 적용 실패: ${err.message}`, 'error');
    }
  });

  return container;
}
