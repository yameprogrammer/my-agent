// Episode and Version Management Page
import { api } from '../api/client.js';
import { showToast } from '../components/toast.js';
import { showSpinner, hideSpinner } from '../components/loading.js';
import { createModal } from '../components/modal.js';

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
            <div style="display: flex; gap: 8px; flex-shrink: 0;" class="flex-row-responsive">
              <button class="btn btn-secondary" id="btn-audit-plot-tab" style="border-color: var(--primary); color: var(--primary); font-weight: 600; padding: 8px 16px; font-size: 0.9rem;">
                🔍 기획 & 인물 검수
              </button>
              <button class="btn btn-danger" id="btn-enter-monitor" style="background-color: var(--primary); border-color: var(--primary); font-weight: 600; padding: 8px 16px; font-size: 0.9rem; flex-shrink: 0;">
                ⚡ 실시간 집필실 입장
              </button>
            </div>
          </div>
          
          <h5 style="font-size: 0.95rem; font-weight: 600; margin-bottom: 12px;">원고 히스토리 및 버전 트리</h5>
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
        versionsList.innerHTML = '<p style="color: var(--text-muted); font-size: 0.85rem; text-align: center; padding: 20px 0;">작성된 본문 초안이 없습니다. 상단 집필실에 입장하여 첫 집필을 시작하세요!</p>';
        return;
      }

      // Sort content by date desc for user friendly viewing
      const sorted = [...allContents].reverse();
      
      sorted.forEach(content => {
        const item = createVersionItem(content);
        versionsList.appendChild(item);
      });
    } catch (err) {
      versionsList.innerHTML = `<p style="color: var(--accent); font-size: 0.85rem; text-align: center; padding: 20px 0;">원고 로딩 실패: ${err.message}</p>`;
    }
  }

  function getAuthorBadge(type) {
    if (type === 'ai') return '<span class="badge badge-primary" style="font-size: 0.7rem; padding: 1px 6px;">AI 집필</span>';
    if (type === 'user') return '<span class="badge badge-success" style="font-size: 0.7rem; padding: 1px 6px;">작가 편집</span>';
    return '<span class="badge badge-secondary" style="font-size: 0.7rem; padding: 1px 6px;">혼합</span>';
  }

  function createVersionItem(content) {
    const item = document.createElement('div');
    item.className = 'glass-card animate-fade-in';
    item.style.padding = '14px';
    
    // Distinct border for approved final version
    if (content.is_approved) {
      item.style.border = '2px solid var(--secondary, #0d9488)';
      item.style.backgroundColor = 'hsl(var(--s-h), var(--s-s), 98%)';
    } else {
      item.style.border = '1px solid var(--border-color)';
    }

    const dateStr = new Date(content.created_at).toLocaleString('ko-KR', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });

    item.innerHTML = `
      <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
        <div style="display: flex; align-items: center; gap: 8px;">
          <strong style="font-size: 0.9rem; color: var(--text-primary);">${content.version_tag}</strong>
          ${getAuthorBadge(content.author_type)}
          ${content.is_approved ? '<span class="badge badge-success" style="font-size: 0.7rem; padding: 1px 6px;">최종 승인본</span>' : ''}
        </div>
        <span style="font-size: 0.75rem; color: var(--text-muted);">${dateStr}</span>
      </div>
      
      <!-- Content body preview -->
      <p style="color: var(--text-secondary); font-size: 0.8rem; overflow: hidden; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; line-height: 1.4; margin-bottom: 12px; background: var(--bg-app); padding: 8px; border-radius: var(--radius-sm);">
        ${content.text || '원고 내용이 비어 있습니다.'}
      </p>
      
      <div style="display: flex; justify-content: flex-end; gap: 8px;">
        <button class="btn btn-secondary btn-view-full-text" style="padding: 4px 10px; font-size: 0.75rem;">👀 원문 전체 보기</button>
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

      createModal({
        title: `원고 상세 정보 (${content.version_tag})`,
        content: textViewer,
        showFooter: false
      });
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
