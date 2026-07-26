// Real-time Writing Monitor page (WebSocket + Human-in-the-loop)
import { wsManager } from '../api/websocket.js';
import { api } from '../api/client.js';
import { showToast } from '../components/toast.js';
import { showSpinner, hideSpinner } from '../components/loading.js';
import { createModal } from '../components/modal.js';

export async function renderWritingMonitor(params) {
  const projectId = params.id;
  const episodeId = params.eid;
  
  const container = document.createElement('div');
  container.className = 'animate-fade-in';
  container.style.width = '100%';
  
  // Scaffolding UI
  container.innerHTML = `
    <!-- Top Nav Back button and status bar -->
    <div class="glass-card" style="padding: 16px 24px; margin-bottom: 24px; display: flex; justify-content: space-between; align-items: center;" class="flex-row-responsive">
      <a href="#/projects/${projectId}" style="font-weight: 600; display: flex; align-items: center; gap: 4px; font-size: 0.9rem;">
        <span>⬅️</span> 회차 목록으로 돌아가기
      </a>
      <div style="display: flex; align-items: center; gap: 12px;">
        <span style="font-size: 0.85rem; font-weight: 500; color: var(--text-secondary);">서버 연결 상태:</span>
        <span id="ws-status-badge" class="badge badge-secondary">연결 대기 중</span>
      </div>
    </div>

    <!-- Horizontal Stepper for Workflow progress -->
    <div class="glass-card" style="padding: 20px; margin-bottom: 24px;">
      <div style="display: flex; justify-content: space-between; align-items: center; position: relative;" id="stepper-horizontal">
        <!-- Connecting Line background -->
        <div style="position: absolute; top: 16px; left: 10%; right: 10%; height: 4px; background: var(--border-color); z-index: 0;" id="stepper-line"></div>
        <div style="position: absolute; top: 16px; left: 10%; width: 0%; height: 4px; background: var(--primary); z-index: 0; transition: width 0.4s ease;" id="stepper-line-active"></div>
        
        <div class="horizontal-step" data-step-h="plotter" style="display: flex; flex-direction: column; align-items: center; gap: 8px; z-index: 1; flex: 1;">
          <div class="step-h-num" style="width: 36px; height: 36px; border-radius: 50%; background: var(--bg-input); border: 3px solid var(--border-color); display: flex; align-items: center; justify-content: center; font-size: 0.9rem; font-weight: 700; color: var(--text-muted); transition: all 0.3s; box-shadow: var(--shadow-sm);">1</div>
          <div style="font-size: 0.8rem; font-weight: 600; color: var(--text-secondary);">기획 (Plotter)</div>
        </div>
        
        <div class="horizontal-step" data-step-h="writer" style="display: flex; flex-direction: column; align-items: center; gap: 8px; z-index: 1; flex: 1;">
          <div class="step-h-num" style="width: 36px; height: 36px; border-radius: 50%; background: var(--bg-input); border: 3px solid var(--border-color); display: flex; align-items: center; justify-content: center; font-size: 0.9rem; font-weight: 700; color: var(--text-muted); transition: all 0.3s; box-shadow: var(--shadow-sm);">2</div>
          <div style="font-size: 0.8rem; font-weight: 600; color: var(--text-secondary);">집필 (Writer)</div>
        </div>
        
        <div class="horizontal-step" data-step-h="judge" style="display: flex; flex-direction: column; align-items: center; gap: 8px; z-index: 1; flex: 1;">
          <div class="step-h-num" style="width: 36px; height: 36px; border-radius: 50%; background: var(--bg-input); border: 3px solid var(--border-color); display: flex; align-items: center; justify-content: center; font-size: 0.9rem; font-weight: 700; color: var(--text-muted); transition: all 0.3s; box-shadow: var(--shadow-sm);">3</div>
          <div style="font-size: 0.8rem; font-weight: 600; color: var(--text-secondary);">검증 (Judge)</div>
        </div>
        
        <div class="horizontal-step" data-step-h="editor" style="display: flex; flex-direction: column; align-items: center; gap: 8px; z-index: 1; flex: 1;">
          <div class="step-h-num" style="width: 36px; height: 36px; border-radius: 50%; background: var(--bg-input); border: 3px solid var(--border-color); display: flex; align-items: center; justify-content: center; font-size: 0.9rem; font-weight: 700; color: var(--text-muted); transition: all 0.3s; box-shadow: var(--shadow-sm);">4</div>
          <div style="font-size: 0.8rem; font-weight: 600; color: var(--text-secondary);">퇴고 (Editor)</div>
        </div>
        
        <div class="horizontal-step" data-step-h="reviewer" style="display: flex; flex-direction: column; align-items: center; gap: 8px; z-index: 1; flex: 1;">
          <div class="step-h-num" style="width: 36px; height: 36px; border-radius: 50%; background: var(--bg-input); border: 3px solid var(--border-color); display: flex; align-items: center; justify-content: center; font-size: 0.9rem; font-weight: 700; color: var(--text-muted); transition: all 0.3s; box-shadow: var(--shadow-sm);">5</div>
          <div style="font-size: 0.8rem; font-weight: 600; color: var(--text-secondary);">평가 (Reviewer)</div>
        </div>
      </div>
    </div>

    <!-- Main 2-Column Workspace layout -->
    <div style="display: grid; grid-template-columns: 1.2fr 0.8fr; gap: 24px;" class="grid-cols-2">
      
      <!-- Left Column: Draft Content viewer & Thinking Console -->
      <div style="display: flex; flex-direction: column; gap: 24px;">
        
        <!-- Thinking console for Reasoning models -->
        <div class="glass-card" id="thinking-container" style="display: none; padding: 0; overflow: hidden; border: 1px solid var(--border-color); transition: all 0.3s ease;">
          <div id="thinking-header" style="display: flex; justify-content: space-between; align-items: center; padding: 12px 20px; background: rgba(var(--primary-rgb), 0.05); border-bottom: 1px solid var(--border-color); cursor: pointer; user-select: none;">
            <div style="display: flex; align-items: center; gap: 8px; font-weight: 600; font-size: 0.85rem; color: var(--primary);">
              <span id="thinking-icon">🧠</span>
              <span id="thinking-title">AI가 깊게 추론하는 중입니다...</span>
              <div class="spinner-ring" id="thinking-spinner" style="width: 12px; height: 12px; border-width: 2px; margin: 0; display: inline-block;"></div>
            </div>
            <button class="btn btn-secondary" id="btn-toggle-thinking" style="padding: 2px 8px; font-size: 0.75rem; min-height: auto; font-weight: 600;">접기 ⬆️</button>
          </div>
          <div id="thinking-content" style="padding: 16px 20px; max-height: 180px; overflow-y: auto; font-family: var(--font-mono); font-size: 0.82rem; line-height: 1.6; color: var(--text-secondary); background: rgba(0,0,0,0.02); white-space: pre-wrap; word-break: break-all; transition: max-height 0.3s ease;">
          </div>
        </div>

        <div class="glass-card" style="padding: 24px; display: flex; flex-direction: column; min-height: 600px;">
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; border-bottom: 1px solid var(--border-color); padding-bottom: 12px; gap: 12px; flex-wrap: wrap;">
            <h3 style="font-family: var(--font-heading); font-size: 1.2rem; margin: 0; display: flex; align-items: center; gap: 8px;">
              <span>📝</span> <span id="draft-panel-title">소설 초안 뷰어</span>
            </h3>
            <div style="display: flex; align-items: center; gap: 10px; flex-wrap: wrap;">
              <span style="font-size: 0.8rem; color: var(--text-muted);" id="word-count-badge">글자 수: 0자</span>
              <button type="button" class="btn btn-secondary" id="btn-toggle-draft-edit" style="padding: 4px 12px; font-size: 0.8rem; min-height: auto;" title="본문을 직접 수정합니다 (H2)">
                ✏️ 편집 모드
              </button>
            </div>
          </div>
          
          <!-- Document Page styling (read-only view) -->
          <div id="draft-text-area" style="flex: 1; overflow-y: auto; max-height: 520px; padding: 24px; background: var(--bg-app); border-radius: var(--radius-md); border: 1px dashed var(--border-color); font-family: var(--font-sans); line-height: 1.9; font-size: 1.05rem; color: var(--text-primary); white-space: pre-wrap; word-break: break-word; transition: background-color var(--transition-normal);">
            집필이 시작되면 실시간으로 글이 작성되는 과정을 보실 수 있습니다.
          </div>
          <!-- Human edit textarea (hidden until edit mode) -->
          <textarea id="draft-edit-area" class="form-control" style="display: none; flex: 1; min-height: 480px; max-height: 520px; padding: 24px; font-family: var(--font-sans); line-height: 1.9; font-size: 1.05rem; resize: vertical; white-space: pre-wrap;" placeholder="본문을 직접 수정하세요. 저장 시 새 버전으로 남습니다."></textarea>
          <p id="draft-edit-hint" style="display: none; margin: 10px 0 0; font-size: 0.78rem; color: var(--text-muted); line-height: 1.4;">
            편집 중에는 AI 스트림이 본문을 덮어쓰지 않습니다. 우측에서 「수정본 저장」또는 「수정본 승인」을 사용하세요.
          </p>
        </div>
      </div>
      
      <!-- Right Column: AI Agent Timeline & HITL Action control panel -->
      <div style="display: flex; flex-direction: column; gap: 24px;">
        
        <!-- Agent State Timeline Panel -->
        <div class="glass-card" style="padding: 24px;">
          <h4 style="font-family: var(--font-heading); font-size: 1.05rem; margin-bottom: 20px;">🤖 AI 집필 에이전트 단계</h4>
          
          <div style="display: flex; flex-direction: column; gap: 16px; position: relative;">
            <!-- Vertical Timeline connector line -->
            <div style="position: absolute; top: 12px; bottom: 12px; left: 15px; width: 2px; background: var(--border-color); z-index: 0;"></div>
            
            <div class="timeline-step" data-step="plotter" style="display: flex; align-items: center; gap: 16px; position: relative; z-index: 1;">
              <div class="step-indicator" style="width: 32px; height: 32px; border-radius: 50%; background: var(--bg-input); border: 2px solid var(--border-color); display: flex; align-items: center; justify-content: center; font-size: 0.95rem; font-weight: 700; color: var(--text-muted); transition: all 0.3s;">🎯</div>
              <div>
                <div class="step-title" style="font-size: 0.9rem; font-weight: 600; color: var(--text-secondary);">Plotter (씬 기획)</div>
                <div class="step-desc" style="font-size: 0.75rem; color: var(--text-muted);">에피소드 아웃라인을 씬 단위로 구성</div>
              </div>
            </div>
            
            <div class="timeline-step" data-step="writer" style="display: flex; align-items: center; gap: 16px; position: relative; z-index: 1;">
              <div class="step-indicator" style="width: 32px; height: 32px; border-radius: 50%; background: var(--bg-input); border: 2px solid var(--border-color); display: flex; align-items: center; justify-content: center; font-size: 0.95rem; font-weight: 700; color: var(--text-muted); transition: all 0.3s;">✍️</div>
              <div>
                <div class="step-title" style="font-size: 0.9rem; font-weight: 600; color: var(--text-secondary);">Writer (씬 본문 집필)</div>
                <div class="step-desc" style="font-size: 0.75rem; color: var(--text-muted);">실시간 본문 텍스트 스트리밍</div>
              </div>
            </div>
            
            <div class="timeline-step" data-step="judge" style="display: flex; align-items: center; gap: 16px; position: relative; z-index: 1;">
              <div class="step-indicator" style="width: 32px; height: 32px; border-radius: 50%; background: var(--bg-input); border: 2px solid var(--border-color); display: flex; align-items: center; justify-content: center; font-size: 0.95rem; font-weight: 700; color: var(--text-muted); transition: all 0.3s;">⚖️</div>
              <div>
                <div class="step-title" style="font-size: 0.9rem; font-weight: 600; color: var(--text-secondary);">Judge (일관성 검증)</div>
                <div class="step-desc" style="font-size: 0.75rem; color: var(--text-muted);">설정집과의 모순 발생 여부 심사</div>
              </div>
            </div>
            
            <div class="timeline-step" data-step="editor" style="display: flex; align-items: center; gap: 16px; position: relative; z-index: 1;">
              <div class="step-indicator" style="width: 32px; height: 32px; border-radius: 50%; background: var(--bg-input); border: 2px solid var(--border-color); display: flex; align-items: center; justify-content: center; font-size: 0.95rem; font-weight: 700; color: var(--text-muted); transition: all 0.3s;">📐</div>
              <div>
                <div class="step-title" style="font-size: 0.9rem; font-weight: 600; color: var(--text-secondary);">Editor (윤문 / 퇴고)</div>
                <div class="step-desc" style="font-size: 0.75rem; color: var(--text-muted);">피드백 및 일관성 모순 반영 수정</div>
              </div>
            </div>
            
            <div class="timeline-step" data-step="reviewer" style="display: flex; align-items: center; gap: 16px; position: relative; z-index: 1;">
              <div class="step-indicator" style="width: 32px; height: 32px; border-radius: 50%; background: var(--bg-input); border: 2px solid var(--border-color); display: flex; align-items: center; justify-content: center; font-size: 0.95rem; font-weight: 700; color: var(--text-muted); transition: all 0.3s;">📝</div>
              <div>
                <div class="step-title" style="font-size: 0.9rem; font-weight: 600; color: var(--text-secondary);">Reviewer (소설 평가)</div>
                <div class="step-desc" style="font-size: 0.75rem; color: var(--text-muted);">가독성, 묘사력, 긴장감 평가 리포트 생성</div>
              </div>
            </div>
          </div>
        </div>
        
        <!-- HITL Control and Review Report Panel -->
        <div class="glass-card" style="padding: 24px; min-height: 300px; display: flex; flex-direction: column; justify-content: center;" id="action-panel">
          <!-- Initial, writing, review, or feedback status UI will render dynamically -->
          <div style="text-align: center; padding: 20px;" id="idle-controls">
            <span style="font-size: 2.5rem; display: block; margin-bottom: 16px;">🚀</span>
            <h4 style="font-family: var(--font-heading); font-size: 1.1rem; margin-bottom: 8px;">준비 완료</h4>
            <p style="color: var(--text-secondary); font-size: 0.85rem; margin-bottom: 20px; line-height: 1.4;">
              작성된 아웃라인을 바탕으로 에이전트 집필 루프를 시작하거나, 기획/인물 설정을 미리 사전 정밀 검수할 수 있습니다.
            </p>
            <button class="btn btn-primary" id="btn-start-writing" style="width: 100%; font-weight: 600; margin-bottom: 10px;">⚡ 집필 프로세스 기동</button>
            <button class="btn btn-secondary" id="btn-audit-plot" style="width: 100%; font-weight: 600; border-color: var(--primary); color: var(--primary);">🔍 기획 & 인물 사전 검수</button>
          </div>
          
          <div style="display: none; text-align: center; padding: 20px;" id="running-controls">
            <div class="spinner-ring" style="margin: 0 auto 20px;"></div>
            <h4 style="font-family: var(--font-heading); font-size: 1.1rem; margin-bottom: 8px;" id="running-title">소설 집필 중</h4>
            <p style="color: var(--text-secondary); font-size: 0.85rem; line-height: 1.4;" id="running-desc">에이전트들이 씬 기획 및 소설 쓰기를 진행 중입니다. 페이지를 벗어나도 백그라운드에서 계속 진행됩니다.</p>
          </div>

          <!-- HITL Review panel -->
          <div style="display: none; flex-direction: column; gap: 16px;" id="review-controls">
            <h4 style="font-family: var(--font-heading); font-size: 1.1rem; border-bottom: 1px solid var(--border-color); padding-bottom: 10px; margin-bottom: 4px; display: flex; align-items: center; gap: 6px;">
              <span>⚖️</span> AI 소설 평가서
            </h4>
            
            <div style="display: flex; gap: 12px; justify-content: space-around; margin-bottom: 8px;">
              <div style="text-align: center; background: var(--bg-app); padding: 8px 12px; border-radius: var(--radius-sm); flex: 1;">
                <span style="font-size: 0.75rem; color: var(--text-muted); display: block;">종합 점수</span>
                <strong style="font-size: 1.3rem; color: var(--primary);" id="report-score">0 / 100</strong>
              </div>
              <div style="text-align: center; background: var(--bg-app); padding: 8px 12px; border-radius: var(--radius-sm); flex: 1;">
                <span style="font-size: 0.75rem; color: var(--text-muted); display: block;">가독성</span>
                <strong style="font-size: 1.1rem; color: var(--secondary);" id="report-readability">0 / 10</strong>
              </div>
              <div style="text-align: center; background: var(--bg-app); padding: 8px 12px; border-radius: var(--radius-sm); flex: 1;">
                <span style="font-size: 0.75rem; color: var(--text-muted); display: block;">긴장감</span>
                <strong style="font-size: 1.1rem; color: var(--accent);" id="report-tension">0 / 10</strong>
              </div>
            </div>
            
            <!-- Accordion analysis tabs -->
            <div style="max-height: 180px; overflow-y: auto; font-size: 0.8rem; line-height: 1.5; color: var(--text-secondary); background: var(--bg-app); padding: 12px; border-radius: var(--radius-sm);">
              <div style="margin-bottom: 8px;">
                <strong style="color: var(--secondary);">✨ 강점 (Strengths)</strong>
                <p id="report-strengths" style="margin-top: 2px;"></p>
              </div>
              <div style="margin-bottom: 8px;">
                <strong style="color: var(--accent);">⚠️ 개선점 (Weaknesses)</strong>
                <p id="report-weaknesses" style="margin-top: 2px;"></p>
              </div>
              <div>
                <strong style="color: var(--primary);">💡 제안사항 (Suggestions)</strong>
                <p id="report-suggestions" style="margin-top: 2px;"></p>
              </div>
            </div>
            
            <div class="form-group" style="margin-bottom: 0;">
              <label class="form-label" style="font-size: 0.85rem;" for="feedback-text">에이전트에게 보낼 작가 피드백 (선택)</label>
              <textarea class="form-control" id="feedback-text" placeholder="예: '주인공들의 대화를 조금 더 코믹하게 수정해줘.', '3씬의 묘사를 좀 더 늘려줘.'" style="height: 70px; resize: none; font-size: 0.85rem;"></textarea>
            </div>
            
            <div style="display: flex; flex-direction: column; gap: 8px; margin-top: 8px;">
              <div style="display: flex; gap: 8px; flex-wrap: wrap;">
                <button class="btn btn-secondary" id="btn-save-human-edit" style="flex: 1; font-size: 0.82rem; min-width: 120px;">
                  💾 수정본 저장
                </button>
                <button class="btn btn-primary" id="btn-save-approve-human" style="flex: 1; font-size: 0.82rem; min-width: 120px; background-color: var(--secondary); border-color: var(--secondary);">
                  ✅ 수정본 승인
                </button>
              </div>
              <div style="display: flex; gap: 8px; flex-wrap: wrap;">
                <button class="btn btn-secondary" id="btn-feedback" style="flex: 1; font-size: 0.82rem; border-color: var(--accent); color: var(--accent); min-width: 120px;">
                  🔄 피드백 후 AI 재작성
                </button>
                <button class="btn btn-primary" id="btn-approve" style="flex: 1; font-size: 0.82rem; min-width: 120px;">
                  📥 AI 초안 그대로 승인
                </button>
              </div>
              <p style="margin: 0; font-size: 0.72rem; color: var(--text-muted); line-height: 1.4;">
                직접 고친 뒤 승인하려면 좌측「편집 모드」→「수정본 승인」. AI 초안을 그대로 쓰려면「AI 초안 그대로 승인」.
              </p>
            </div>
          </div>
          
        </div>
      </div>
      
    </div>
  `;

  // Bind references
  const wsBadge = container.querySelector('#ws-status-badge');
  const draftArea = container.querySelector('#draft-text-area');
  const draftEditArea = container.querySelector('#draft-edit-area');
  const draftEditHint = container.querySelector('#draft-edit-hint');
  const draftPanelTitle = container.querySelector('#draft-panel-title');
  const wordCountBadge = container.querySelector('#word-count-badge');
  const toggleEditBtn = container.querySelector('#btn-toggle-draft-edit');
  
  const idlePanel = container.querySelector('#idle-controls');
  const runningPanel = container.querySelector('#running-controls');
  const reviewPanel = container.querySelector('#review-controls');
  
  const startBtn = container.querySelector('#btn-start-writing');
  const auditBtn = container.querySelector('#btn-audit-plot');
  const feedbackBtn = container.querySelector('#btn-feedback');
  const approveBtn = container.querySelector('#btn-approve');
  const saveHumanBtn = container.querySelector('#btn-save-human-edit');
  const saveApproveHumanBtn = container.querySelector('#btn-save-approve-human');
  const feedbackInput = container.querySelector('#feedback-text');

  // Load report references
  const repScore = container.querySelector('#report-score');
  const repRead = container.querySelector('#report-readability');
  const repTension = container.querySelector('#report-tension');
  const repStr = container.querySelector('#report-strengths');
  const repWeak = container.querySelector('#report-weaknesses');
  const repSug = container.querySelector('#report-suggestions');

  let currentDraftText = '';
  let currentState = 'disconnected';
  /** H2: 편집 모드 — true 이면 스트림이 본문을 덮어쓰지 않음 */
  let isEditMode = false;
  let streamBlockedToastShown = false;
  let editDirty = false;

  function updateWordCount(text) {
    wordCountBadge.textContent = `글자 수: ${(text || '').length.toLocaleString('ko-KR')}자`;
  }

  function getDisplayedDraftText() {
    if (isEditMode) return draftEditArea.value || '';
    return currentDraftText || '';
  }

  /**
   * 뷰어/에디터에 본문 반영. force=false 이고 편집 중이면 스트림 덮어쓰기 거부.
   * @returns {boolean} 반영 여부
   */
  function setDraftText(text, { force = false, scrollBottom = false, scrollTop = false } = {}) {
    const next = text ?? '';
    if (isEditMode && !force) {
      if (!streamBlockedToastShown) {
        showToast('편집 모드 중이라 AI 스트림이 본문을 덮어쓰지 않습니다. 편집을 종료하면 동기화됩니다.', 'info');
        streamBlockedToastShown = true;
      }
      return false;
    }
    currentDraftText = next;
    if (isEditMode) {
      draftEditArea.value = next;
    } else {
      draftArea.textContent = next || '집필이 시작되면 실시간으로 글이 작성되는 과정을 보실 수 있습니다.';
    }
    updateWordCount(next);
    if (scrollBottom) {
      const el = isEditMode ? draftEditArea : draftArea;
      el.scrollTop = el.scrollHeight;
    }
    if (scrollTop) {
      const el = isEditMode ? draftEditArea : draftArea;
      el.scrollTop = 0;
    }
    return true;
  }

  function setEditMode(on) {
    if (on && !getDisplayedDraftText().trim() && !currentDraftText.trim()) {
      // allow empty edit for rare cases — still ok
    }
    if (on) {
      const fromView = currentDraftText || draftArea.textContent || '';
      // placeholder 문구는 초안으로 쓰지 않음
      const seed = fromView.includes('집필이 시작되면') ? '' : fromView;
      draftEditArea.value = seed || currentDraftText;
      currentDraftText = draftEditArea.value;
      draftArea.style.display = 'none';
      draftEditArea.style.display = 'block';
      draftEditHint.style.display = 'block';
      draftPanelTitle.textContent = '소설 초안 편집';
      toggleEditBtn.textContent = '👁 보기 모드';
      toggleEditBtn.classList.add('btn-primary');
      toggleEditBtn.classList.remove('btn-secondary');
      isEditMode = true;
      streamBlockedToastShown = false;
      editDirty = false;
      updateWordCount(draftEditArea.value);
      draftEditArea.focus();
    } else {
      // 편집 내용을 뷰로 반영
      currentDraftText = draftEditArea.value;
      draftArea.textContent = currentDraftText || '집필이 시작되면 실시간으로 글이 작성되는 과정을 보실 수 있습니다.';
      draftEditArea.style.display = 'none';
      draftEditHint.style.display = 'none';
      draftArea.style.display = 'block';
      draftPanelTitle.textContent = '소설 초안 뷰어';
      toggleEditBtn.textContent = '✏️ 편집 모드';
      toggleEditBtn.classList.remove('btn-primary');
      toggleEditBtn.classList.add('btn-secondary');
      isEditMode = false;
      editDirty = false;
      streamBlockedToastShown = false;
      updateWordCount(currentDraftText);
    }
  }

  toggleEditBtn.addEventListener('click', () => {
    setEditMode(!isEditMode);
  });

  draftEditArea.addEventListener('input', () => {
    editDirty = true;
    currentDraftText = draftEditArea.value;
    updateWordCount(draftEditArea.value);
  });

  async function resolveParentContentId() {
    try {
      const list = await api.get(`/projects/${projectId}/episodes/${episodeId}/contents`);
      if (!list || !list.length) return null;
      const sorted = [...list].sort(
        (a, b) => new Date(b.created_at) - new Date(a.created_at)
      );
      return sorted[0].id;
    } catch (e) {
      console.warn('parent content resolve failed', e);
      return null;
    }
  }

  function suggestHumanVersionTag() {
    const n = Date.now().toString().slice(-4);
    return `v-human-${n}`;
  }

  /**
   * REST: 사람 수정본 Content 생성 (+ 선택 승인)
   */
  async function saveHumanEdit({ approveAfter = false } = {}) {
    const text = getDisplayedDraftText().trim();
    if (!text) {
      showToast('저장할 본문이 비어 있습니다. 편집 모드에서 내용을 입력해 주세요.', 'error');
      return null;
    }
    // 편집 모드가 아니어도 현재 표시 텍스트로 저장 가능 (AI 초안 소폭 수정 없이 복제 저장)
    showSpinner(approveAfter ? '수정본 저장 및 승인 중...' : '수정본 저장 중...');
    try {
      const parent_id = await resolveParentContentId();
      const author_type = parent_id ? 'hybrid' : 'user';
      const created = await api.post(
        `/projects/${projectId}/episodes/${episodeId}/contents`,
        {
          parent_id,
          version_tag: suggestHumanVersionTag(),
          text: getDisplayedDraftText(),
          author_type,
        }
      );
      if (approveAfter && created?.id) {
        await api.put(
          `/projects/${projectId}/episodes/${episodeId}/contents/${created.id}/approve`
        );
      }
      hideSpinner();
      editDirty = false;
      currentDraftText = getDisplayedDraftText();
      if (isEditMode) setEditMode(false);
      if (approveAfter) {
        showToast('수정본을 저장하고 최종본으로 승인했습니다.', 'success');
        // graph 가 waiting_user 에 남아 있을 수 있음 — REST 정본이 우선이므로 회차 목록으로
        window.location.hash = `#/projects/${projectId}`;
      } else {
        showToast(`수정본 저장 완료 (${created.version_tag || 'new'})`, 'success');
      }
      return created;
    } catch (err) {
      hideSpinner();
      showToast(err.message || '수정본 저장 실패', 'error');
      return null;
    }
  }

  const onBeforeUnload = (e) => {
    if (isEditMode && editDirty) {
      e.preventDefault();
      e.returnValue = '';
    }
  };
  window.addEventListener('beforeunload', onBeforeUnload);

  // Format badges helper
  function updateWsBadge(status) {
    wsBadge.textContent = {
      disconnected: '🔴 연결 해제됨',
      connecting: '🟡 연결 중...',
      connected: '🟢 연결 완료'
    }[status] || status;

    wsBadge.className = `badge badge-${
      status === 'connected' ? 'success' : status === 'connecting' ? 'secondary' : 'secondary'
    }`;
  }

  // Handle agent steps indicators coloring (vertical timeline + horizontal stepper)
  function highlightActiveStep(stepName) {
    // 1. 세로 타임라인 업데이트
    const steps = container.querySelectorAll('.timeline-step');
    steps.forEach(step => {
      const isCurrent = step.getAttribute('data-step') === stepName;
      const indicator = step.querySelector('.step-indicator');
      const title = step.querySelector('.step-title');
      
      if (isCurrent) {
        indicator.style.background = 'var(--primary-light)';
        indicator.style.borderColor = 'var(--primary)';
        indicator.style.color = 'var(--primary)';
        title.style.color = 'var(--primary)';
        title.style.fontWeight = '700';
      } else {
        indicator.style.background = 'var(--bg-input)';
        indicator.style.borderColor = 'var(--border-color)';
        indicator.style.color = 'var(--text-muted)';
        title.style.color = 'var(--text-secondary)';
        title.style.fontWeight = '600';
      }
    });

    // 2. 가로 Stepper 업데이트
    const hSteps = container.querySelectorAll('.horizontal-step');
    const stepOrder = ['plotter', 'writer', 'judge', 'editor', 'reviewer'];
    const activeIndex = stepOrder.indexOf(stepName);
    
    const activeLine = container.querySelector('#stepper-line-active');
    if (activeLine) {
      if (activeIndex === -1) {
        activeLine.style.width = '0%';
      } else {
        // 0단계 -> 0%, 4단계 -> 80% (마지막 단계까지 매끄럽게 연결)
        const percent = (activeIndex / (stepOrder.length - 1)) * 80;
        activeLine.style.width = `${percent}%`;
      }
    }

    hSteps.forEach((step, idx) => {
      const numDiv = step.querySelector('.step-h-num');
      const textDiv = step.querySelector('div:last-child');
      
      if (idx < activeIndex) {
        // 이미 지나간 완료 단계
        numDiv.textContent = '✓';
        numDiv.style.background = 'var(--secondary)';
        numDiv.style.borderColor = 'var(--secondary)';
        numDiv.style.color = '#fff';
        textDiv.style.color = 'var(--secondary)';
      } else if (idx === activeIndex) {
        // 현재 진행 중인 활성 단계
        numDiv.textContent = (idx + 1).toString();
        numDiv.style.background = 'var(--primary)';
        numDiv.style.borderColor = 'var(--primary)';
        numDiv.style.color = '#fff';
        textDiv.style.color = 'var(--primary)';
        textDiv.style.fontWeight = '700';
      } else {
        // 앞으로 진행해야 할 대기 단계
        numDiv.textContent = (idx + 1).toString();
        numDiv.style.background = 'var(--bg-input)';
        numDiv.style.borderColor = 'var(--border-color)';
        numDiv.style.color = 'var(--text-muted)';
        textDiv.style.color = 'var(--text-muted)';
        textDiv.style.fontWeight = '600';
      }
    });
  }

  // Handle panel rendering
  function showPanel(panelName, data = {}) {
    idlePanel.style.display = panelName === 'idle' ? 'block' : 'none';
    runningPanel.style.display = panelName === 'running' ? 'block' : 'none';
    reviewPanel.style.display = panelName === 'review' ? 'flex' : 'none';

    if (panelName === 'running') {
      const stepMsg = {
        plotter: 'AI 플로터가 소설 씬을 기획 중입니다...',
        writer: 'AI 작가가 소설 본문을 작성 중입니다...',
        judge: 'AI 심사위원이 세계관 설정과의 일관성을 심사 중입니다...',
        editor: 'AI 편집자가 퇴고 및 수정을 진행 중입니다...',
        reviewer: 'AI 평론가가 소설 종합 평가 리포트를 작성 중입니다...'
      }[data.activeStep] || '에이전트 워크플로우를 진행 중입니다...';
      
      container.querySelector('#running-title').textContent = data.activeStep 
        ? `${data.activeStep.charAt(0).toUpperCase() + data.activeStep.slice(1)} 작동 중` 
        : '집필 프로세스 가동 중';
      container.querySelector('#running-desc').textContent = stepMsg;
    }
  }

  // Thinking UI elements & interaction
  const thinkingContainer = container.querySelector('#thinking-container');
  const thinkingContent = container.querySelector('#thinking-content');
  const thinkingTitle = container.querySelector('#thinking-title');
  const thinkingSpinner = container.querySelector('#thinking-spinner');
  const thinkingIcon = container.querySelector('#thinking-icon');
  const toggleThinkingBtn = container.querySelector('#btn-toggle-thinking');

  let isThinkingFolded = false;
  let currentThinkingText = '';

  toggleThinkingBtn.addEventListener('click', (e) => {
    e.stopPropagation();
    isThinkingFolded = !isThinkingFolded;
    if (isThinkingFolded) {
      thinkingContent.style.maxHeight = '0px';
      thinkingContent.style.padding = '0px 20px';
      toggleThinkingBtn.textContent = '열기 ⬇️';
    } else {
      thinkingContent.style.maxHeight = '180px';
      thinkingContent.style.padding = '16px 20px';
      toggleThinkingBtn.textContent = '접기 ⬆️';
    }
  });

  function startThinkingView() {
    thinkingContainer.style.display = 'block';
    thinkingSpinner.style.display = 'inline-block';
    thinkingTitle.textContent = 'AI가 깊게 추론하는 중입니다...';
    thinkingIcon.textContent = '🧠';
  }

  function finishThinkingView() {
    thinkingSpinner.style.display = 'none';
    thinkingTitle.textContent = '추론 완료 (AI 생각 과정)';
    thinkingIcon.textContent = '✅';
  }

  // Start WebSocket connection
  wsManager.connect(projectId, episodeId);
  updateWsBadge(wsManager.status);

  // Subscribe to WS manager status change
  const offStatus = wsManager.on('status-change', (status) => {
    updateWsBadge(status);
  });

  // Subscribe to state change
  const offState = wsManager.on('status_changed', (msg) => {
    const status = msg.status; // idle, writing, judging, editing, reviewing, waiting_user, done, auditing
    console.log(`WS State transition: ${status}`);

    if (status === 'writing' || status === 'editing') {
      highlightActiveStep(status === 'writing' ? 'writer' : 'editor');
      showPanel('running', { activeStep: status === 'writing' ? 'writer' : 'editor' });
    } else if (status === 'judging') {
      finishThinkingView();
      highlightActiveStep('judge');
      showPanel('running', { activeStep: 'judge' });
    } else if (status === 'reviewing') {
      finishThinkingView();
      highlightActiveStep('reviewer');
      showPanel('running', { activeStep: 'reviewer' });
    } else if (status === 'auditing') {
      highlightActiveStep('plotter');
      showPanel('running', { activeStep: 'plotter' });
      container.querySelector('#running-title').textContent = '기획안 정밀 검수 중';
      container.querySelector('#running-desc').textContent = '에이전트가 씬 아웃라인 및 인물 디자인 개연성을 검토하고 있습니다...';
    } else if (status === 'idle') {
      finishThinkingView();
      highlightActiveStep(null);
      showPanel('idle');
    } else if (status === 'done') {
      finishThinkingView();
      highlightActiveStep(null);
      showPanel('idle');
      showToast('소설 집필이 성공적으로 완료 및 영구 저장되었습니다!', 'success');
      window.location.hash = `#/projects/${projectId}`;
    }
  });

  // Subscribe to reasoning stream (O1/R1 models thought path)
  const offReasoning = wsManager.on('reasoning_stream', (msg) => {
    if (thinkingContainer.style.display === 'none') {
      startThinkingView();
    }
    
    currentThinkingText += msg.chunk;
    thinkingContent.textContent = currentThinkingText;
    thinkingContent.scrollTop = thinkingContent.scrollHeight;
  });

  // Function to create beautiful Plot Audit Report Modal
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

  // Subscribe to plot audit results
  const offPlotAudited = wsManager.on('plot_audited', (msg) => {
    finishThinkingView();
    highlightActiveStep(null);
    showPanel('idle');
    showToast('스토리보드 및 인물 사전 검수가 완료되었습니다!', 'success');
    showPlotAuditModal(msg.report || {});
  });

  // 검수/집필 실패 시 running 패널에 고착되지 않도록 idle 복구
  const offError = wsManager.on('error', () => {
    finishThinkingView();
    highlightActiveStep(null);
    if (runningPanel.style.display !== 'none') {
      showPanel('idle');
    }
  });

  // Subscribe to text stream
  const offText = wsManager.on('text_stream', (msg) => {
    // 본문 출력이 시작되면 추론 과정은 끝났음을 인지
    finishThinkingView();

    if (isEditMode) {
      if (!streamBlockedToastShown) {
        showToast('편집 모드 중이라 AI 스트림이 본문을 덮어쓰지 않습니다.', 'info');
        streamBlockedToastShown = true;
      }
      return;
    }

    // Append or initialize text
    let next;
    if (msg.is_new_scene || currentDraftText === '' || draftArea.textContent.includes('집필이 시작되면')) {
      next = msg.chunk;
    } else {
      next = currentDraftText + msg.chunk;
    }
    setDraftText(next, { force: true, scrollBottom: true });
  });

  // Subscribe to HITL request
  const offReview = wsManager.on('requires_user_review', (msg) => {
    finishThinkingView();
    highlightActiveStep(null);
    showPanel('review');
    showToast('소설 1차 초고 작성이 끝나 작가 검토를 기다리고 있습니다. 편집 모드로 직접 고칠 수 있습니다.', 'info');
    
    setDraftText(msg.draft_text || '', { force: true, scrollTop: true });

    // Render Reviewer Report
    const report = msg.evaluation_report || {};
    repScore.textContent = `${report.score || 0} / 100`;
    repRead.textContent = `${report.readability || 0} / 10`;
    repTension.textContent = `${report.tension || 0} / 10`;
    
    repStr.textContent = report.strengths || '없음';
    repWeak.textContent = report.weaknesses || '없음';
    repSug.textContent = report.suggestions || '없음';
  });

  // Sync state on connect
  const offSync = wsManager.on('current_state', (msg) => {
    currentState = msg.status;
    
    if (currentState === 'waiting_user') {
      // Re-trigger review view
      wsManager.trigger('requires_user_review', {
        draft_text: msg.draft_text || msg.draft,
        evaluation_report: msg.evaluation_report
      });
    } else if (currentState === 'idle') {
      highlightActiveStep(null);
      showPanel('idle');
      const draftVal = msg.draft_text || msg.draft || '';
      if (draftVal) {
        setDraftText(draftVal, { force: !isEditMode });
      }
    } else {
      // Is running (writing/judging/editing/reviewing)
      let activeStep = 'writer';
      if (currentState === 'editing') activeStep = 'editor';
      else if (currentState === 'judging') activeStep = 'judge';
      else if (currentState === 'reviewing') activeStep = 'reviewer';
      
      highlightActiveStep(activeStep);
      showPanel('running', { activeStep });
      const draftVal = msg.draft_text || msg.draft || '';
      if (draftVal) {
        setDraftText(draftVal, { force: !isEditMode, scrollBottom: true });
      }
    }
  });

  // Action listeners
  startBtn.addEventListener('click', () => {
    if (isEditMode) setEditMode(false);
    const sent = wsManager.send('start_writing');
    if (sent) {
      currentThinkingText = '';
      thinkingContent.textContent = '';
      thinkingContainer.style.display = 'none';

      showPanel('running', { activeStep: 'plotter' });
      highlightActiveStep('plotter');
      setDraftText(
        'AI 플로터가 회차 줄거리를 분석하여 소설 씬(Scene)들을 구성하는 중입니다. 곧 집필이 시작됩니다...',
        { force: true }
      );
    } else {
      showToast('서버에 집필 명령을 보내지 못했습니다. 소켓 연결 상태를 확인하세요.', 'error');
    }
  });

  auditBtn.addEventListener('click', () => {
    const sent = wsManager.send('audit_plot');
    if (sent) {
      showPanel('running', { activeStep: 'plotter' });
      highlightActiveStep('plotter');
      container.querySelector('#running-title').textContent = '기획안 정밀 검수 중';
      container.querySelector('#running-desc').textContent = '에이전트가 씬 아웃라인 및 인물 디자인 개연성을 검토하고 있습니다...';
    } else {
      showToast('기획 검수 명령 전송 실패. 소켓 연결 상태를 확인하세요.', 'error');
    }
  });

  feedbackBtn.addEventListener('click', () => {
    const feedback = feedbackInput.value.trim();
    if (!feedback) {
      showToast('피드백 내용을 입력해 주세요.', 'error');
      return;
    }
    
    // 백엔드는 user_feedback 이라는 명시적 키를 원함 (버그 수정)
    const sent = wsManager.send('submit_feedback', { user_feedback: feedback });
    if (sent) {
      feedbackInput.value = '';
      currentThinkingText = '';
      thinkingContent.textContent = '';
      thinkingContainer.style.display = 'none';

      showPanel('running', { activeStep: 'editor' });
      highlightActiveStep('editor');
      showToast('피드백이 전송되어 교정 집필을 시작합니다.', 'success');
    } else {
      showToast('피드백 전송 실패', 'error');
    }
  });

  approveBtn.addEventListener('click', () => {
    createModal({
      title: 'AI 초안 그대로 승인',
      content: '현재 에이전트 초안(그래프 draft)을 본 에피소드 최종 원고로 승인하고 DB에 저장합니다. 직접 고친 내용이 있다면 「수정본 승인」을 사용하세요.',
      confirmText: '승인 및 저장',
      cancelText: '취소',
      onConfirm: () => {
        const sent = wsManager.send('approve');
        if (sent) {
          showSpinner('소설 원고를 최종 저장하는 중...');
        } else {
          showToast('승인 요청 실패', 'error');
        }
      }
    });
  });

  saveHumanBtn.addEventListener('click', async () => {
    if (!isEditMode) {
      setEditMode(true);
      showToast('편집 모드로 전환했습니다. 내용을 확인·수정한 뒤 다시 저장을 눌러 주세요.', 'info');
      return;
    }
    await saveHumanEdit({ approveAfter: false });
  });

  saveApproveHumanBtn.addEventListener('click', () => {
    if (!isEditMode) {
      setEditMode(true);
    }
    createModal({
      title: '수정본 승인',
      content: '현재 화면의 본문(편집본)을 새 버전으로 저장하고 최종본으로 승인합니다. AI 재실행 없이 작가 수정본이 정본이 됩니다.',
      confirmText: '저장 후 승인',
      cancelText: '취소',
      onConfirm: async () => {
        // preventDismiss: async confirm — createModal may dismiss before await; ok
        await saveHumanEdit({ approveAfter: true });
      }
    });
  });

  // Clean up WebSockets subscriptions on navigation away
  container.addEventListener('destroyed', () => {
    console.log('Cleaning up Writing Monitor Page WebSocket subscriptions');
    window.removeEventListener('beforeunload', onBeforeUnload);
    offStatus();
    offState();
    offReasoning();
    offPlotAudited();
    offError();
    offText();
    offReview();
    offSync();
    wsManager.disconnect();
  });

  return container;
}
