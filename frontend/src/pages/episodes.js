// Episode and Version Management Page
import { api } from '../api/client.js';
import { showToast } from '../components/toast.js';
import { showSpinner, hideSpinner } from '../components/loading.js';
import { createModal } from '../components/modal.js';
import { renderDiffRowsHtml, getTextareaSelection } from '../utils/diff.js';

export async function renderEpisodes(projectId) {
  const container = document.createElement('div');
  container.className = 'animate-fade-in';
  
  let allEpisodes = [];
  let selectedEpisodeId = null;
  let allContents = []; // Content versions for selected episode

  container.innerHTML = `
    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 28px;" class="grid-cols-2">
      
      <!-- Left Column: Episode List -->
      <div class="glass-card" style="padding: 24px; display: flex; flex-direction: column; gap: 16px;">
        <div style="display: flex; justify-content: space-between; align-items: center;">
          <h3 style="font-family: var(--font-heading); font-size: 1.25rem; margin: 0; display: flex; align-items: center; gap: 8px;">
            <span>📚</span> 회차 관리 (Episodes)
          </h3>
          <button class="btn btn-primary" id="btn-add-episode" style="height: 36px; padding: 4px 12px; font-size: 0.85rem;">
            <span>➕</span> 새 회차 추가
          </button>
        </div>
        
        <div id="episodes-list" style="display: flex; flex-direction: column; gap: 12px; max-height: 550px; overflow-y: auto; padding-right: 4px;">
          <!-- Episode elements -->
        </div>
      </div>
      
      <!-- Right Column: Selected Episode Content Versions -->
      <div class="glass-card" style="padding: 24px; display: flex; flex-direction: column; gap: 16px;" id="contents-panel">
        <div style="text-align: center; padding: 120px 20px; color: var(--text-muted);" id="contents-empty-state">
          <span style="font-size: 3rem; display: block; margin-bottom: 12px;">📁</span>
          <p>좌측에서 회차를 선택하면 작성된 본문 버전 정보 및 집필실 입장 메뉴가 표시됩니다.</p>
        </div>
        
        <div id="contents-panel-body" style="display: none; height: 100%;">
          <div style="display: flex; justify-content: space-between; align-items: flex-start; border-bottom: 1px solid var(--border-color); padding-bottom: 16px; margin-bottom: 16px;" class="flex-row-responsive">
            <div>
              <h4 id="selected-episode-title" style="font-family: var(--font-heading); font-size: 1.2rem; color: var(--text-primary); margin: 0;">제 1화. 소설의 시작</h4>
              <p id="selected-episode-outline" style="color: var(--text-secondary); font-size: 0.85rem; margin-top: 4px; line-height: 1.4;"></p>
            </div>
            <div style="display: flex; gap: 8px; flex-shrink: 0; flex-wrap: wrap; justify-content: flex-end;" class="flex-row-responsive">
              <button class="btn btn-secondary" id="btn-write-draft" style="font-weight: 600; padding: 8px 14px; font-size: 0.85rem;" title="AI 없이 작가 초안을 직접 작성">
                ✍️ 직접 초안 작성
              </button>
              <button class="btn btn-secondary" id="btn-rag-settings" style="border-color: var(--secondary); color: var(--secondary); font-weight: 600; padding: 8px 14px; font-size: 0.85rem;">
                ⚙️ RAG 고증 설정
              </button>
              <button class="btn btn-secondary" id="btn-audit-plot-tab" style="border-color: var(--primary); color: var(--primary); font-weight: 600; padding: 8px 14px; font-size: 0.85rem;">
                🔍 기획 & 인물 검수
              </button>
              <button class="btn btn-danger" id="btn-enter-monitor" style="background-color: var(--primary); border-color: var(--primary); font-weight: 600; padding: 8px 14px; font-size: 0.85rem; flex-shrink: 0;">
                ⚡ 실시간 집필실 입장
              </button>
            </div>
          </div>
          
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; gap: 8px; flex-wrap: wrap;">
            <h5 style="font-size: 0.95rem; font-weight: 600; margin: 0;">원고 히스토리 및 버전 트리</h5>
            <div style="display: flex; align-items: center; gap: 8px;">
              <div style="display: flex; border: 1px solid var(--border-color); border-radius: var(--radius-sm); overflow: hidden;">
                <button type="button" class="btn btn-secondary" id="btn-view-list" style="padding: 2px 10px; font-size: 0.72rem; min-height: auto; border: none; border-radius: 0;">목록</button>
                <button type="button" class="btn btn-secondary" id="btn-view-tree" style="padding: 2px 10px; font-size: 0.72rem; min-height: auto; border: none; border-radius: 0; border-left: 1px solid var(--border-color);">트리</button>
              </div>
              <span style="font-size: 0.72rem; color: var(--text-muted);">편집·diff·롤백 지원</span>
            </div>
          </div>
          <div id="versions-list" style="display: flex; flex-direction: column; gap: 12px; max-height: 400px; overflow-y: auto; padding-right: 4px;">
            <!-- Content versions -->
          </div>
        </div>
      </div>
      
    </div>
  `;

  const epListDiv = container.querySelector('#episodes-list');
  const contentsPanelEmpty = container.querySelector('#contents-empty-state');
  const contentsPanelBody = container.querySelector('#contents-panel-body');
  const selectedEpTitle = container.querySelector('#selected-episode-title');
  const selectedEpOutline = container.querySelector('#selected-episode-outline');
  const versionsList = container.querySelector('#versions-list');
  
  const addEpBtn = container.querySelector('#btn-add-episode');
  const enterMonitorBtn = container.querySelector('#btn-enter-monitor');
  const auditPlotTabBtn = container.querySelector('#btn-audit-plot-tab');
  const ragSettingsBtn = container.querySelector('#btn-rag-settings');
  const writeDraftBtn = container.querySelector('#btn-write-draft');
  const btnViewList = container.querySelector('#btn-view-list');
  const btnViewTree = container.querySelector('#btn-view-tree');
  /** list | tree */
  let versionViewMode = 'list';

  function setVersionViewMode(mode) {
    versionViewMode = mode;
    if (btnViewList && btnViewTree) {
      btnViewList.style.background = mode === 'list' ? 'var(--primary-light)' : '';
      btnViewList.style.color = mode === 'list' ? 'var(--primary)' : '';
      btnViewTree.style.background = mode === 'tree' ? 'var(--primary-light)' : '';
      btnViewTree.style.color = mode === 'tree' ? 'var(--primary)' : '';
    }
    if (selectedEpisodeId) loadContents(selectedEpisodeId);
  }
  btnViewList?.addEventListener('click', () => setVersionViewMode('list'));
  btnViewTree?.addEventListener('click', () => setVersionViewMode('tree'));
  setVersionViewMode('list');

  /** 다음 version_tag 제안 */
  function suggestNextVersionTag(parentContent = null) {
    const n = (allContents || []).length + 1;
    if (!parentContent) return `v${n}.0-draft`;
    return `v${n}.0-human`;
  }

  function escapeHtml(str) {
    return String(str ?? '')
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  /**
   * 본문 편집 모달 — 새 Content 버전 저장 (H1 Human Edit)
   * @param {object|null} parentContent 부모 버전 (null 이면 루트 초안)
   * @param {{ approveAfter?: boolean }} options
   */
  function openContentEditor(parentContent = null, options = {}) {
    if (!selectedEpisodeId) {
      showToast('회차를 먼저 선택해 주세요.', 'error');
      return;
    }

    const isFork = !!parentContent;
    const initialText = isFork ? (parentContent.text || '') : '';
    const defaultTag = suggestNextVersionTag(parentContent);
    const defaultAuthor = isFork
      ? (parentContent.author_type === 'user' ? 'user' : 'hybrid')
      : 'user';

    const form = document.createElement('div');
    form.innerHTML = `
      <p style="font-size: 0.85rem; color: var(--text-secondary); margin: 0 0 12px; line-height: 1.5;">
        ${isFork
          ? `부모 버전 <strong>${escapeHtml(parentContent.version_tag)}</strong> 을(를) 기반으로 새 버전을 만듭니다. 원본은 그대로 유지됩니다.`
          : 'AI 없이 작가가 직접 초안을 작성합니다. 저장 후 집필실에서 윤문 모드로 이어갈 수 있습니다.'}
      </p>
      <div class="form-group">
        <label class="form-label" for="he-version-tag">버전 태그</label>
        <input class="form-control" type="text" id="he-version-tag" maxlength="50" value="${escapeHtml(defaultTag)}">
      </div>
      <div class="form-group">
        <label class="form-label" for="he-author-type">작성 주체</label>
        <select class="form-control" id="he-author-type">
          <option value="user" ${defaultAuthor === 'user' ? 'selected' : ''}>작가 (user)</option>
          <option value="hybrid" ${defaultAuthor === 'hybrid' ? 'selected' : ''}>혼합 — AI 기반 수정 (hybrid)</option>
          <option value="ai" ${defaultAuthor === 'ai' ? 'selected' : ''}>AI (ai)</option>
        </select>
      </div>
      <div class="form-group" style="margin-bottom: 0;">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px; flex-wrap: wrap; gap: 8px;">
          <label class="form-label" for="he-text" style="margin: 0;">본문</label>
          <span id="he-char-count" style="font-size: 0.75rem; color: var(--text-muted);">0자</span>
        </div>
        <textarea class="form-control" id="he-text" style="height: min(36vh, 300px); resize: vertical; font-family: var(--font-sans); line-height: 1.75; font-size: 0.95rem;" placeholder="여기에 원고를 작성하거나 수정하세요...">${escapeHtml(initialText)}</textarea>
      </div>
      <div class="form-group" style="margin-top: 12px; margin-bottom: 0; padding: 12px; background: var(--bg-app); border-radius: var(--radius-sm); border: 1px dashed var(--border-color);">
        <label class="form-label" style="font-size: 0.8rem;">H6 부분 재작성 — 본문에서 구간 선택 후 지시</label>
        <input class="form-control" type="text" id="he-span-instruction" placeholder="예: 이 문단을 더 긴장감 있게, 대사를 짧게" style="font-size: 0.85rem; margin-bottom: 8px;">
        <button type="button" class="btn btn-secondary" id="he-partial-rewrite" style="width: 100%; font-size: 0.82rem;">✨ 선택 구간 AI 수정</button>
      </div>
    `;

    const ta = form.querySelector('#he-text');
    const counter = form.querySelector('#he-char-count');
    const updateCount = () => {
      counter.textContent = `${(ta.value || '').length.toLocaleString('ko-KR')}자`;
    };
    ta.addEventListener('input', updateCount);
    updateCount();

    form.querySelector('#he-partial-rewrite').addEventListener('click', async () => {
      const sel = getTextareaSelection(ta);
      if (!sel || !sel.text.trim()) {
        showToast('본문에서 수정할 구간을 드래그해 선택해 주세요.', 'error');
        return;
      }
      const instruction = form.querySelector('#he-span-instruction').value.trim();
      if (!instruction) {
        showToast('수정 지시를 입력해 주세요.', 'error');
        return;
      }
      showSpinner('선택 구간을 AI가 재작성하는 중...');
      try {
        const res = await api.post(
          `/projects/${projectId}/episodes/${selectedEpisodeId}/contents/partial-rewrite`,
          {
            full_text: ta.value,
            selected_text: sel.text,
            instruction,
            save_as_version: false,
          }
        );
        hideSpinner();
        ta.value = res.full_text;
        updateCount();
        showToast('선택 구간이 수정되었습니다. 필요하면 저장하세요.', 'success');
      } catch (err) {
        hideSpinner();
        showToast(err.message || '부분 재작성 실패', 'error');
      }
    });

    async function saveVersion(approveAfter) {
      const text = ta.value;
      const version_tag = form.querySelector('#he-version-tag').value.trim();
      const author_type = form.querySelector('#he-author-type').value;
      if (!version_tag) {
        showToast('버전 태그를 입력해 주세요.', 'error');
        return false;
      }
      if (!text || !text.trim()) {
        showToast('본문이 비어 있습니다.', 'error');
        return false;
      }

      showSpinner(approveAfter ? '저장 후 최종본 승인 중...' : '새 버전 저장 중...');
      try {
        const created = await api.post(
          `/projects/${projectId}/episodes/${selectedEpisodeId}/contents`,
          {
            parent_id: isFork ? parentContent.id : null,
            version_tag,
            text,
            author_type,
          }
        );
        if (approveAfter && created?.id) {
          await api.put(
            `/projects/${projectId}/episodes/${selectedEpisodeId}/contents/${created.id}/approve`
          );
        }
        hideSpinner();
        showToast(
          approveAfter
            ? `"${version_tag}" 저장 및 최종본 승인 완료`
            : `"${version_tag}" 새 버전으로 저장했습니다`,
          'success'
        );
        await loadContents(selectedEpisodeId);
        return true;
      } catch (err) {
        hideSpinner();
        showToast(err.message || '저장 실패', 'error');
        return false;
      }
    }

    // 커스텀 푸터: 저장 / 저장 후 승인 / 취소
    const footerHost = document.createElement('div');
    footerHost.style.display = 'flex';
    footerHost.style.flexWrap = 'wrap';
    footerHost.style.gap = '8px';
    footerHost.style.justifyContent = 'flex-end';
    footerHost.style.marginTop = '16px';
    footerHost.innerHTML = `
      <button type="button" class="btn btn-secondary" id="he-cancel">취소</button>
      <button type="button" class="btn btn-primary" id="he-save">💾 새 버전 저장</button>
      <button type="button" class="btn btn-primary" id="he-save-approve" style="background-color: var(--secondary); border-color: var(--secondary);">✅ 저장 후 최종본 승인</button>
    `;
    form.appendChild(footerHost);

    const modal = createModal({
      title: isFork ? `✏️ 원고 편집 (${parentContent.version_tag})` : '✍️ 직접 초안 작성',
      content: form,
      showFooter: false,
    });

    footerHost.querySelector('#he-cancel').addEventListener('click', () => modal.close());
    footerHost.querySelector('#he-save').addEventListener('click', async () => {
      if (await saveVersion(false)) modal.close();
    });
    footerHost.querySelector('#he-save-approve').addEventListener('click', async () => {
      if (await saveVersion(true)) modal.close();
    });
  }

  writeDraftBtn.addEventListener('click', () => openContentEditor(null));

  async function loadEpisodes() {
    epListDiv.innerHTML = '';
    showSpinner('에피소드 정보를 불러오는 중...');
    
    try {
      allEpisodes = await api.get(`/projects/${projectId}/episodes`);
      hideSpinner();
      
      if (allEpisodes.length === 0) {
        epListDiv.innerHTML = '<p style="color: var(--text-muted); font-size: 0.9rem; text-align: center; padding: 40px 0;">등록된 회차가 없습니다. 새 회차를 추가해 주세요.</p>';
        return;
      }
      
      allEpisodes.forEach(ep => {
        const item = createEpisodeItem(ep);
        epListDiv.appendChild(item);
      });
      
      // Auto select first episode if previously selected is gone or none selected
      if (selectedEpisodeId) {
        const stillExists = allEpisodes.some(e => e.id === selectedEpisodeId);
        if (stillExists) {
          selectEpisode(selectedEpisodeId);
        } else {
          selectedEpisodeId = null;
          showEmptyContents();
        }
      }
    } catch (err) {
      hideSpinner();
      showToast(`에피소드 로드 실패: ${err.message}`, 'error');
    }
  }

  function showEmptyContents() {
    contentsPanelEmpty.style.display = 'block';
    contentsPanelBody.style.display = 'none';
  }

  function createEpisodeItem(ep) {
    const el = document.createElement('div');
    el.className = 'glass-card animate-fade-in';
    el.style.padding = '16px';
    el.style.cursor = 'pointer';
    el.style.borderLeft = selectedEpisodeId === ep.id ? '4px solid var(--primary)' : '1px solid var(--border-color)';
    el.style.backgroundColor = selectedEpisodeId === ep.id ? 'var(--primary-light)' : 'var(--bg-card)';
    
    el.innerHTML = `
      <div style="display: flex; justify-content: space-between; align-items: flex-start; gap: 8px;">
        <div style="flex: 1; min-width: 0;">
          <h4 style="font-size: 0.95rem; font-weight: 600; color: var(--text-primary); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; margin: 0;">
            제 ${ep.episode_number}화. ${ep.title}
          </h4>
          <p style="color: var(--text-secondary); font-size: 0.8rem; overflow: hidden; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; margin-top: 4px; line-height: 1.4;">
            ${ep.outline || '회차 줄거리가 지정되지 않았습니다.'}
          </p>
        </div>
        
        <div style="display: flex; gap: 4px; flex-shrink: 0;">
          <button class="btn-edit-ep" title="수정" style="background: none; border: none; font-size: 0.85rem; cursor: pointer; padding: 2px;">✏️</button>
          <button class="btn-delete-ep" title="삭제" style="background: none; border: none; font-size: 0.85rem; cursor: pointer; padding: 2px;">🗑️</button>
        </div>
      </div>
    `;

    el.addEventListener('click', (e) => {
      if (e.target.closest('.btn-edit-ep') || e.target.closest('.btn-delete-ep')) return;
      selectEpisode(ep.id);
    });

    el.querySelector('.btn-edit-ep').addEventListener('click', (e) => {
      e.stopPropagation();
      openEpModal(ep);
    });

    el.querySelector('.btn-delete-ep').addEventListener('click', (e) => {
      e.stopPropagation();
      confirmDeleteEp(ep, el);
    });

    return el;
  }

  async function selectEpisode(episodeId) {
    selectedEpisodeId = episodeId;
    
    // Highlight list
    Array.from(epListDiv.children).forEach((child, idx) => {
      const ep = allEpisodes[idx];
      if (ep) {
        child.style.borderLeft = ep.id === episodeId ? '4px solid var(--primary)' : '1px solid var(--border-color)';
        child.style.backgroundColor = ep.id === episodeId ? 'var(--primary-light)' : 'var(--bg-card)';
      }
    });

    const ep = allEpisodes.find(e => e.id === episodeId);
    if (!ep) return;

    selectedEpTitle.textContent = `제 ${ep.episode_number}화. ${ep.title}`;
    selectedEpOutline.textContent = ep.outline || '줄거리 및 씬 계획이 설정되지 않았습니다.';
    
    // Bind enter monitor button
    enterMonitorBtn.onclick = () => {
      window.location.hash = `#/projects/${projectId}/episodes/${episodeId}/write`;
    };

    // Bind RAG settings configuration button
    ragSettingsBtn.onclick = (e) => {
      e.stopPropagation();
      openRagSettingsModal(ep);
    };

    // Bind audit plot button
    auditPlotTabBtn.onclick = async (e) => {
      e.stopPropagation();
      showSpinner('에이전트가 스토리보드 및 인물 묘사를 심사하는 중...');
      try {
        const report = await api.post(`/projects/${projectId}/episodes/${episodeId}/audit-plot`);
        hideSpinner();
        showPlotAuditModal(report);
      } catch (err) {
        hideSpinner();
        showToast(err.message || '검수 중 오류가 발생했습니다. 집필실에서 기획을 먼저 생성해 주세요.', 'error');
      }
    };

    contentsPanelEmpty.style.display = 'none';
    contentsPanelBody.style.display = 'block';

    await loadContents(episodeId);
  }

  function openRagSettingsModal(ep) {
    const formEl = document.createElement('div');
    formEl.innerHTML = `
      <form id="form-rag-settings" style="display: flex; flex-direction: column; gap: 16px; padding: 8px 0;">
        <p style="font-size: 0.85rem; color: var(--text-secondary); margin: 0; line-height: 1.4;">
          집필 에이전트가 참고할 세계관 및 고증 데이터 매칭 필터링 방식을 세부 제어합니다.
        </p>
        
        <div>
          <label style="display: block; font-size: 0.88rem; font-weight: 600; margin-bottom: 6px; color: var(--text-primary);">
            RAG 유사도 임계치 (Similarity Threshold): <span id="threshold-val" style="color: var(--primary); font-weight: bold;">${ep.rag_threshold}</span>
          </label>
          <input type="range" id="rag-threshold-input" min="0" max="1" step="0.05" value="${ep.rag_threshold}" style="width: 100%; accent-color: var(--primary); cursor: pointer;">
          <span style="font-size: 0.75rem; color: var(--text-muted); display: block; margin-top: 4px;">
            임계치가 높을수록 씬(개요)과 고증 자료 간의 유사도가 매우 높은 고품질 자료만 선별해 옵니다. (추천: 0.4 ~ 0.6)
          </span>
        </div>

        <div>
          <label style="display: block; font-size: 0.88rem; font-weight: 600; margin-bottom: 6px; color: var(--text-primary);">
            최대 고증 검색 개수 (Retrieve Limit)
          </label>
          <input type="number" id="rag-limit-input" min="1" max="20" value="${ep.rag_limit}" class="search-input" style="width: 100%; height: 38px; padding: 0 12px; border: 1px solid var(--border-color); border-radius: var(--radius-sm); background: transparent; color: var(--text-primary);">
          <span style="font-size: 0.75rem; color: var(--text-muted); display: block; margin-top: 4px;">
            집필실 입장 시 프롬프트 문맥에 포함시킬 최대 고증 자료 조각 개수입니다.
          </span>
        </div>

        <div>
          <label style="display: block; font-size: 0.88rem; font-weight: 600; margin-bottom: 6px; color: var(--text-primary);">
            강제 참조 고증 자료 ID 목록 (Force Include IDs)
          </label>
          <input type="text" id="rag-force-ids-input" value="${ep.force_reference_ids || ''}" placeholder="예: 3, 5, 12" class="search-input" style="width: 100%; height: 38px; padding: 0 12px; border: 1px solid var(--border-color); border-radius: var(--radius-sm); background: transparent; color: var(--text-primary);">
          <span style="font-size: 0.75rem; color: var(--text-muted); display: block; margin-top: 4px;">
            임계치(유사도)와 상관없이 이 회차 집필 시 **무조건 프롬프트 컨텍스트 최상단에 강제 삽입**할 고증자료 레코드 ID 목록입니다. (쉼표로 구분)
          </span>
        </div>
      </form>
    `;

    // Real-time slider value label binding
    const thresholdInput = formEl.querySelector('#rag-threshold-input');
    const thresholdVal = formEl.querySelector('#threshold-val');
    thresholdInput.addEventListener('input', () => {
      thresholdVal.textContent = thresholdInput.value;
    });

    createModal({
      title: `⚙️ RAG 고증 설정 제어 - 제 ${ep.episode_number}화`,
      content: formEl,
      confirmText: '설정 저장',
      cancelText: '취소',
      onConfirm: async (dismiss) => {
        const threshold = parseFloat(thresholdInput.value);
        const limit = parseInt(formEl.querySelector('#rag-limit-input').value);
        const force_ids = formEl.querySelector('#rag-force-ids-input').value.trim();

        if (isNaN(limit) || limit < 1) {
          showToast('최대 고증 검색 개수는 1개 이상이어야 합니다.', 'warning');
          return false;
        }

        showSpinner('RAG 최적화 설정을 적용하는 중...');
        try {
          const updated = await api.put(`/projects/${projectId}/episodes/${ep.id}`, {
            episode_number: ep.episode_number,
            title: ep.title,
            outline: ep.outline,
            rag_threshold: threshold,
            rag_limit: limit,
            force_reference_ids: force_ids || null
          });
          
          hideSpinner();
          showToast('RAG 고증 가이드 파라미터가 성공적으로 반영되었습니다!', 'success');
          
          // Local state update
          const idx = allEpisodes.findIndex(e => e.id === ep.id);
          if (idx !== -1) {
            allEpisodes[idx] = updated;
          }
          
          dismiss();
        } catch (err) {
          hideSpinner();
          showToast(`설정 반영 실패: ${err.message}`, 'error');
          return false;
        }
      }
    });
  }

  function showPlotAuditModal(report) {
    const scoreColor = report.score >= 80 ? 'var(--secondary)' : report.score >= 60 ? 'var(--primary)' : 'var(--accent)';
    const statusBadge = report.is_passed 
      ? `<span class="badge badge-success" style="font-size:0.85rem; padding:4px 8px;">검수 통과 (Passed)</span>`
      : `<span class="badge" style="font-size:0.85rem; padding:4px 8px; background:var(--accent); color:#fff;">보완 필요 (Warning)</span>`;

    let scenesHtml = '';
    if (report.scene_audits && report.scene_audits.length > 0) {
      scenesHtml = report.scene_audits.map(s => {
        const scenePassed = s.is_passed 
          ? `<span style="color:var(--secondary); font-weight:bold;">🟢 정상</span>` 
          : `<span style="color:var(--accent); font-weight:bold;">🔴 붕괴 발견</span>`;
        
        let issuesHtml = '';
        if (s.ooc_issues && s.ooc_issues.length > 0) {
          issuesHtml += `<div style="margin-top:6px;"><strong style="color:var(--accent); font-size:0.8rem;">👤 인물 붕괴 (OOC):</strong>
            <ul style="margin:2px 0 0 16px; padding:0; font-size:0.78rem; list-style-type:circle;">
              ${s.ooc_issues.map(issue => `<li>${issue}</li>`).join('')}
            </ul></div>`;
        }
        if (s.plot_holes && s.plot_holes.length > 0) {
          issuesHtml += `<div style="margin-top:6px;"><strong style="color:var(--primary); font-size:0.8rem;">🧩 플롯 구멍 (Plot Hole):</strong>
            <ul style="margin:2px 0 0 16px; padding:0; font-size:0.78rem; list-style-type:circle;">
              ${s.plot_holes.map(hole => `<li>${hole}</li>`).join('')}
            </ul></div>`;
        }
        if (s.suggestions && s.suggestions.length > 0) {
          issuesHtml += `<div style="margin-top:6px;"><strong style="color:var(--text-secondary); font-size:0.8rem;">💡 추천 피드백 가이드:</strong>
            <ul style="margin:2px 0 0 16px; padding:0; font-size:0.78rem; list-style-type:square;">
              ${s.suggestions.map(sug => `<li style="font-style:italic;">${sug}</li>`).join('')}
            </ul></div>`;
        }

        return `
          <div style="border: 1px solid var(--border-color); border-radius: var(--radius-sm); padding: 12px; margin-bottom: 12px; background: rgba(0,0,0,0.01);">
            <div style="display:flex; justify-content:space-between; align-items:center; border-bottom:1px dashed var(--border-color); padding-bottom:6px; margin-bottom:6px;">
              <strong style="font-size:0.85rem; color:var(--text-primary);">씬 #${s.scene_index}: ${s.scene_title}</strong>
              ${scenePassed}
            </div>
            ${issuesHtml || '<div style="color:var(--text-muted); font-size:0.75rem; font-style:italic;">설정 및 성격 붕괴 요소가 발견되지 않았습니다.</div>'}
          </div>
        `;
      }).join('');
    } else {
      scenesHtml = `<div style="text-align:center; padding:20px; color:var(--text-muted); font-style:italic;">검수된 세부 씬 정보가 없습니다.</div>`;
    }

    createModal({
      title: '🔍 기획 및 인물 진단 결과서',
      content: `
        <div style="display:flex; align-items:center; justify-content:space-between; margin-bottom:16px; background:var(--bg-app); padding:12px 16px; border-radius:var(--radius-sm);">
          <div>
            <span style="font-size:0.75rem; color:var(--text-muted); display:block; margin-bottom:2px;">사전 진단 결과</span>
            ${statusBadge}
          </div>
          <div style="text-align:right;">
            <span style="font-size:0.75rem; color:var(--text-muted); display:block; margin-bottom:2px;">기획 신뢰도 점수</span>
            <strong style="font-size:1.8rem; color:${scoreColor}; font-family:var(--font-heading);">${report.score || 0} / 100</strong>
          </div>
        </div>
        
        <div style="margin-bottom:20px;">
          <strong style="font-size:0.9rem; color:var(--primary); display:block; margin-bottom:6px;">📝 종합 검수 리포트</strong>
          <p style="font-size:0.82rem; color:var(--text-secondary); line-height:1.6; background:rgba(var(--primary-rgb),0.02); border-left:4px solid var(--primary); padding:10px 14px; margin:0; border-radius:0 var(--radius-sm) var(--radius-sm) 0; white-space:pre-wrap;">${report.summary || '의견 없음'}</p>
        </div>

        <div style="max-height:280px; overflow-y:auto; padding-right:4px;">
          <strong style="font-size:0.9rem; color:var(--text-primary); display:block; margin-bottom:8px;">📌 씬별 캐릭터 및 개연성 진단</strong>
          ${scenesHtml}
        </div>
      `,
      confirmText: '확인',
      cancelText: '닫기',
      onConfirm: () => {}
    });
  }

  async function loadContents(episodeId) {
    versionsList.innerHTML = '';
    
    try {
      allContents = await api.get(`/projects/${projectId}/episodes/${episodeId}/contents`);
      
      if (!allContents || allContents.length === 0) {
        versionsList.innerHTML = `
          <div style="text-align: center; padding: 28px 16px; color: var(--text-muted);">
            <p style="font-size: 0.85rem; margin: 0 0 14px; line-height: 1.5;">
              작성된 본문 초안이 없습니다.<br>
              집필실에서 AI 집필을 시작하거나, 작가 초안을 직접 작성할 수 있습니다.
            </p>
            <button type="button" class="btn btn-primary" id="btn-empty-write-draft" style="font-size: 0.85rem;">
              ✍️ 직접 초안 작성
            </button>
          </div>`;
        versionsList.querySelector('#btn-empty-write-draft')?.addEventListener('click', () => {
          openContentEditor(null);
        });
        return;
      }

      if (versionViewMode === 'tree') {
        renderVersionTree(allContents);
      } else {
        // Sort content by date desc for user friendly viewing
        const sorted = [...allContents].reverse();
        sorted.forEach(content => {
          const item = createVersionItem(content, 0);
          versionsList.appendChild(item);
        });
      }
    } catch (err) {
      versionsList.innerHTML = `<p style="color: var(--accent); font-size: 0.85rem; text-align: center; padding: 20px 0;">원고 로딩 실패: ${err.message}</p>`;
    }
  }

  /** H6: parent_id 기반 트리 렌더 */
  function renderVersionTree(contents) {
    const byParent = new Map();
    contents.forEach(c => {
      const key = c.parent_id == null ? 'root' : String(c.parent_id);
      if (!byParent.has(key)) byParent.set(key, []);
      byParent.get(key).push(c);
    });
    // roots: parent null OR parent not in set
    const ids = new Set(contents.map(c => c.id));
    const roots = contents.filter(c => c.parent_id == null || !ids.has(c.parent_id));
    roots.sort((a, b) => new Date(a.created_at) - new Date(b.created_at));

    function walk(node, depth) {
      const item = createVersionItem(node, depth);
      versionsList.appendChild(item);
      const kids = byParent.get(String(node.id)) || [];
      kids.sort((a, b) => new Date(a.created_at) - new Date(b.created_at));
      kids.forEach(k => walk(k, depth + 1));
    }
    roots.forEach(r => walk(r, 0));
  }

  async function openDiffModal(leftContent, rightContent) {
    showSpinner('버전 비교 중...');
    try {
      const data = await api.get(
        `/projects/${projectId}/episodes/${selectedEpisodeId}/contents/${leftContent.id}/diff/${rightContent.id}`
      );
      hideSpinner();
      const wrap = document.createElement('div');
      wrap.innerHTML = `
        <p style="font-size:0.85rem;color:var(--text-secondary);margin:0 0 12px;">
          <strong>${escapeHtml(data.left_tag)}</strong> (#${data.left_id}, ${data.left_len}자)
          →
          <strong>${escapeHtml(data.right_tag)}</strong> (#${data.right_id}, ${data.right_len}자)
        </p>
        ${renderDiffRowsHtml(data.rows)}
      `;
      createModal({
        title: '📊 버전 대조 (Diff)',
        content: wrap,
        showFooter: false,
      });
    } catch (err) {
      hideSpinner();
      showToast(err.message || 'Diff 실패', 'error');
    }
  }

  async function rollbackToParent(content) {
    if (!content.parent_id) {
      showToast('부모 버전이 없어 롤백할 수 없습니다.', 'error');
      return;
    }
    const parent = allContents.find(c => c.id === content.parent_id);
    if (!parent) {
      showToast('부모 버전을 찾을 수 없습니다.', 'error');
      return;
    }
    createModal({
      title: '부모 버전으로 롤백',
      content: `현재 분기에서 <strong>${escapeHtml(parent.version_tag)}</strong> 본문을 새 버전으로 복제합니다. 기존 버전은 삭제되지 않습니다.`,
      confirmText: '롤백 버전 생성',
      cancelText: '취소',
      onConfirm: async () => {
        showSpinner('롤백 버전 저장 중...');
        try {
          await api.post(`/projects/${projectId}/episodes/${selectedEpisodeId}/contents`, {
            parent_id: content.id,
            version_tag: `v-rollback-${Date.now().toString().slice(-4)}`,
            text: parent.text,
            author_type: 'user',
          });
          hideSpinner();
          showToast('부모 본문을 새 버전으로 저장했습니다.', 'success');
          loadContents(selectedEpisodeId);
        } catch (err) {
          hideSpinner();
          showToast(err.message || '롤백 실패', 'error');
        }
      },
    });
  }

  function getAuthorBadge(type) {
    if (type === 'ai') return '<span class="badge badge-primary" style="font-size: 0.7rem; padding: 1px 6px;">AI 집필</span>';
    if (type === 'user') return '<span class="badge badge-success" style="font-size: 0.7rem; padding: 1px 6px;">작가 편집</span>';
    if (type === 'hybrid') return '<span class="badge badge-secondary" style="font-size: 0.7rem; padding: 1px 6px;">혼합 수정</span>';
    return '<span class="badge badge-secondary" style="font-size: 0.7rem; padding: 1px 6px;">혼합</span>';
  }

  function createVersionItem(content, depth = 0) {
    const item = document.createElement('div');
    item.className = 'glass-card animate-fade-in';
    item.style.padding = '14px';
    if (depth > 0) {
      item.style.marginLeft = `${Math.min(depth, 6) * 16}px`;
      item.style.borderLeft = '3px solid var(--primary)';
    }
    
    // Distinct border for approved final version
    if (content.is_approved) {
      item.style.border = '2px solid var(--secondary, #0d9488)';
      item.style.backgroundColor = 'hsl(var(--s-h), var(--s-s), 98%)';
      if (depth > 0) item.style.borderLeft = '3px solid var(--secondary)';
    } else if (depth === 0) {
      item.style.border = '1px solid var(--border-color)';
    }

    const dateStr = new Date(content.created_at).toLocaleString('ko-KR', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });

    const preview = escapeHtml(
      (content.text || '원고 내용이 비어 있습니다.').slice(0, 280)
    );
    const hasParent = !!content.parent_id;

    item.innerHTML = `
      <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
        <div style="display: flex; align-items: center; gap: 8px; flex-wrap: wrap;">
          ${depth > 0 ? `<span style="font-size:0.7rem;color:var(--primary);">└</span>` : ''}
          <strong style="font-size: 0.9rem; color: var(--text-primary);">${escapeHtml(content.version_tag)}</strong>
          ${getAuthorBadge(content.author_type)}
          ${content.is_approved ? '<span class="badge badge-success" style="font-size: 0.7rem; padding: 1px 6px;">최종 승인본</span>' : ''}
          ${hasParent ? `<span style="font-size: 0.7rem; color: var(--text-muted);">↩ #${content.parent_id}</span>` : ''}
          <span style="font-size: 0.7rem; color: var(--text-muted);">#${content.id}</span>
        </div>
        <span style="font-size: 0.75rem; color: var(--text-muted);">${dateStr}</span>
      </div>
      
      <p style="color: var(--text-secondary); font-size: 0.8rem; overflow: hidden; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; line-height: 1.4; margin-bottom: 12px; background: var(--bg-app); padding: 8px; border-radius: var(--radius-sm);">
        ${preview}
      </p>
      
      <div style="display: flex; justify-content: flex-end; gap: 8px; flex-wrap: wrap;">
        <button class="btn btn-secondary btn-view-full-text" style="padding: 4px 10px; font-size: 0.75rem;">👀 원문 보기</button>
        <button class="btn btn-secondary btn-edit-version" style="padding: 4px 10px; font-size: 0.75rem;">✏️ 편집·저장</button>
        ${hasParent ? `<button class="btn btn-secondary btn-diff-parent" style="padding: 4px 10px; font-size: 0.75rem;">📊 부모와 Diff</button>` : ''}
        ${hasParent ? `<button class="btn btn-secondary btn-rollback" style="padding: 4px 10px; font-size: 0.75rem;">↩️ 롤백</button>` : ''}
        ${!content.is_approved ? `
          <button class="btn btn-primary btn-approve-version" style="padding: 4px 10px; font-size: 0.75rem; background-color: var(--secondary); border-color: var(--secondary);">📥 최종본 승인</button>
        ` : ''}
      </div>
    `;

    // View full text modal
    item.querySelector('.btn-view-full-text').addEventListener('click', () => {
      const textViewer = document.createElement('div');
      textViewer.style.fontFamily = 'var(--font-sans)';
      textViewer.style.lineHeight = '1.8';
      textViewer.style.fontSize = '1.05rem';
      textViewer.style.color = 'var(--text-primary)';
      textViewer.style.whiteSpace = 'pre-wrap';
      textViewer.style.maxHeight = '50vh';
      textViewer.style.overflowY = 'auto';
      textViewer.style.padding = '12px';
      textViewer.style.background = 'var(--bg-app)';
      textViewer.style.borderRadius = 'var(--radius-sm)';
      textViewer.textContent = content.text;

      const wrap = document.createElement('div');
      wrap.appendChild(textViewer);
      const actions = document.createElement('div');
      actions.style.cssText = 'display:flex;justify-content:flex-end;gap:8px;margin-top:16px;';
      actions.innerHTML = `
        <button type="button" class="btn btn-secondary" id="view-edit-btn">✏️ 이 버전 편집</button>
      `;
      wrap.appendChild(actions);

      const modal = createModal({
        title: `원고 상세 (${content.version_tag})`,
        content: wrap,
        showFooter: false
      });
      actions.querySelector('#view-edit-btn').addEventListener('click', () => {
        modal.close();
        openContentEditor(content);
      });
    });

    item.querySelector('.btn-edit-version').addEventListener('click', () => {
      openContentEditor(content);
    });

    item.querySelector('.btn-diff-parent')?.addEventListener('click', () => {
      const parent = allContents.find(c => c.id === content.parent_id);
      if (!parent) {
        showToast('부모 버전을 찾을 수 없습니다.', 'error');
        return;
      }
      openDiffModal(parent, content);
    });

    item.querySelector('.btn-rollback')?.addEventListener('click', () => {
      rollbackToParent(content);
    });

    // Approve version event
    if (!content.is_approved) {
      item.querySelector('.btn-approve-version').addEventListener('click', async () => {
        showSpinner('최종본으로 승인 중...');
        try {
          await api.put(`/projects/${projectId}/episodes/${selectedEpisodeId}/contents/${content.id}/approve`);
          hideSpinner();
          showToast(`"${content.version_tag}" 원고를 챕터 최종본으로 설정했습니다.`, 'success');
          loadContents(selectedEpisodeId);
        } catch (err) {
          hideSpinner();
          showToast(`승인 실패: ${err.message}`, 'error');
        }
      });
    }

    return item;
  }

  function confirmDeleteEp(ep, element) {
    createModal({
      title: '회차 삭제',
      content: `정말로 <strong>"제 ${ep.episode_number}화. ${ep.title}"</strong> 회차를 삭제하시겠습니까?<br><span style="color: var(--accent); font-size: 0.85rem; display: block; margin-top: 8px;">⚠️ 이 회차 아래 작성된 모든 본문 버전 및 AI 평가 리포트가 영구적으로 함께 삭제됩니다.</span>`,
      confirmText: '삭제',
      cancelText: '취소',
      isDangerous: true,
      onConfirm: async () => {
        showSpinner('회차 삭제 중...');
        try {
          await api.delete(`/projects/${projectId}/episodes/${ep.id}`);
          hideSpinner();
          showToast(`제 ${ep.episode_number}화 회차를 성공적으로 삭제했습니다.`, 'success');
          
          element.style.transform = 'scale(0.9)';
          element.style.opacity = '0';
          setTimeout(() => {
            element.remove();
            allEpisodes = allEpisodes.filter(e => e.id !== ep.id);
            if (selectedEpisodeId === ep.id) {
              selectedEpisodeId = null;
              showEmptyContents();
            }
            if (allEpisodes.length === 0) {
              epListDiv.innerHTML = '<p style="color: var(--text-muted); font-size: 0.9rem; text-align: center; padding: 40px 0;">등록된 회차가 없습니다. 새 회차를 추가해 주세요.</p>';
            }
          }, 250);
        } catch (err) {
          hideSpinner();
          showToast(`삭제 실패: ${err.message}`, 'error');
        }
      }
    });
  }

  function openEpModal(ep = null) {
    const isEdit = !!ep;
    const formContainer = document.createElement('div');
    formContainer.innerHTML = `
      <div class="form-group">
        <label class="form-label" for="ep-number">회차 번호 (숫자)</label>
        <input class="form-control" type="number" id="ep-number" placeholder="예: 1, 2" required min="1" value="${isEdit ? ep.episode_number : allEpisodes.length + 1}">
      </div>
      
      <div class="form-group">
        <label class="form-label" for="ep-title">회차 제목</label>
        <input class="form-control" type="text" id="ep-title" placeholder="예: 첫 번째 만남, 운명의 서막" required maxlength="100" value="${isEdit ? ep.title : ''}">
      </div>
      
      <div class="form-group">
        <label class="form-label" for="ep-outline">회차 아웃라인 / 씬 집필 가이드</label>
        <textarea class="form-control" id="ep-outline" placeholder="이 챕터에서 일어날 주요 사건, 기승전결 구조, 배치할 씬 목록을 개략적으로 서술해 주세요. AI 플로터가 이를 기반으로 씬 기획을 시작합니다." style="height: 140px; resize: none;" required>${isEdit ? ep.outline : ''}</textarea>
      </div>
    `;

    createModal({
      title: isEdit ? '회차 정보 수정' : '새 회차 추가',
      content: formContainer,
      confirmText: isEdit ? '수정' : '추가',
      cancelText: '취소',
      onConfirm: async (dismiss) => {
        const episode_number = parseInt(formContainer.querySelector('#ep-number').value);
        const title = formContainer.querySelector('#ep-title').value.trim();
        const outline = formContainer.querySelector('#ep-outline').value.trim();

        if (isNaN(episode_number) || episode_number <= 0 || !title || !outline) {
          showToast('올바른 회차 정보와 아웃라인을 입력해 주세요.', 'error');
          return false;
        }

        showSpinner(isEdit ? '회차 수정 중...' : '신규 회차 추가 중...');
        try {
          if (isEdit) {
            await api.put(`/projects/${projectId}/episodes/${ep.id}`, {
              episode_number,
              title,
              outline
            });
            showToast(`제 ${episode_number}화 정보를 수정했습니다.`, 'success');
          } else {
            await api.post(`/projects/${projectId}/episodes`, {
              episode_number,
              title,
              outline
            });
            showToast(`제 ${episode_number}화 회차를 새로 추가했습니다.`, 'success');
          }
          
          hideSpinner();
          dismiss();
          await loadEpisodes();
        } catch (err) {
          hideSpinner();
          showToast(`저장 실패: ${err.message}`, 'error');
          return false;
        }
      }
    });
  }

  addEpBtn.addEventListener('click', () => openEpModal());
  loadEpisodes();

  return container;
}
