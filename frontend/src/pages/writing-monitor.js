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

    <!-- Main 2-Column Workspace layout -->
    <div style="display: grid; grid-template-columns: 1.2fr 0.8fr; gap: 24px;" class="grid-cols-2">
      
      <!-- Left Column: Draft Content viewer -->
      <div class="glass-card" style="padding: 24px; display: flex; flex-direction: column; min-height: 600px;">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; border-bottom: 1px solid var(--border-color); padding-bottom: 12px;">
          <h3 style="font-family: var(--font-heading); font-size: 1.2rem; margin: 0; display: flex; align-items: center; gap: 8px;">
            <span>📝</span> 소설 초안 뷰어
          </h3>
          <span style="font-size: 0.8rem; color: var(--text-muted);" id="word-count-badge">글자 수: 0자</span>
        </div>
        
        <!-- Document Page styling -->
        <div id="draft-text-area" style="flex: 1; overflow-y: auto; max-height: 520px; padding: 24px; background: var(--bg-app); border-radius: var(--radius-md); border: 1px dashed var(--border-color); font-family: var(--font-sans); line-height: 1.9; font-size: 1.05rem; color: var(--text-primary); white-space: pre-wrap; word-break: break-all; transition: background-color var(--transition-normal);">
          집필이 시작되면 실시간으로 글이 작성되는 과정을 보실 수 있습니다.
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
              작성된 아웃라인을 바탕으로 에이전트 집필 루프를 시작할 수 있습니다.
            </p>
            <button class="btn btn-primary" id="btn-start-writing" style="width: 100%; font-weight: 600;">⚡ 집필 프로세스 기동</button>
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
              <label class="form-label" style="font-size: 0.85rem;" for="feedback-text">에이전트에게 보낼 작가 피드백</label>
              <textarea class="form-control" id="feedback-text" placeholder="예: '주인공들의 대화를 조금 더 코믹하게 수정해줘.', '3씬의 묘사를 좀 더 늘려줘.'" style="height: 70px; resize: none; font-size: 0.85rem;"></textarea>
            </div>
            
            <div style="display: flex; gap: 12px; margin-top: 8px;">
              <button class="btn btn-secondary" id="btn-feedback" style="flex: 1; font-size: 0.85rem; border-color: var(--accent); color: var(--accent);">
                🔄 피드백 반영 재작성
              </button>
              <button class="btn btn-primary" id="btn-approve" style="flex: 1; font-size: 0.85rem; background-color: var(--secondary); border-color: var(--secondary);">
                📥 최종본 승인 완료
              </button>
            </div>
          </div>
          
        </div>
      </div>
      
    </div>
  `;

  // Bind references
  const wsBadge = container.querySelector('#ws-status-badge');
  const draftArea = container.querySelector('#draft-text-area');
  const wordCountBadge = container.querySelector('#word-count-badge');
  
  const idlePanel = container.querySelector('#idle-controls');
  const runningPanel = container.querySelector('#running-controls');
  const reviewPanel = container.querySelector('#review-controls');
  
  const startBtn = container.querySelector('#btn-start-writing');
  const feedbackBtn = container.querySelector('#btn-feedback');
  const approveBtn = container.querySelector('#btn-approve');
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

  // Handle agent steps indicators coloring
  function highlightActiveStep(stepName) {
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

  // Start WebSocket connection
  wsManager.connect(projectId, episodeId);
  updateWsBadge(wsManager.status);

  // Subscribe to WS manager status change
  const offStatus = wsManager.on('status-change', (status) => {
    updateWsBadge(status);
  });

  // Subscribe to state change
  const offState = wsManager.on('status_changed', (msg) => {
    const status = msg.status; // idle, writing, judging, editing, reviewing, waiting_user, done
    console.log(`WS State transition: ${status}`);

    if (status === 'writing' || status === 'editing') {
      highlightActiveStep(status === 'writing' ? 'writer' : 'editor');
      showPanel('running', { activeStep: status === 'writing' ? 'writer' : 'editor' });
    } else if (status === 'judging') {
      highlightActiveStep('judge');
      showPanel('running', { activeStep: 'judge' });
    } else if (status === 'reviewing') {
      highlightActiveStep('reviewer');
      showPanel('running', { activeStep: 'reviewer' });
    } else if (status === 'done') {
      highlightActiveStep(null);
      showPanel('idle');
      showToast('소설 집필이 성공적으로 완료 및 영구 저장되었습니다!', 'success');
      window.location.hash = `#/projects/${projectId}`;
    }
  });

  // Subscribe to text stream
  const offText = wsManager.on('text_stream', (msg) => {
    // Append or initialize text
    if (msg.is_new_scene || draftArea.textContent.includes('집필이 시작되면')) {
      currentDraftText = msg.chunk;
    } else {
      currentDraftText += msg.chunk;
    }
    
    draftArea.textContent = currentDraftText;
    wordCountBadge.textContent = `글자 수: ${currentDraftText.length}자`;
    
    // Auto scroll bottom
    draftArea.scrollTop = draftArea.scrollHeight;
  });

  // Subscribe to HITL request
  const offReview = wsManager.on('requires_user_review', (msg) => {
    highlightActiveStep(null);
    showPanel('review');
    showToast('소설 1차 초고 작성이 끝나 작가 검토를 기다리고 있습니다.', 'info');
    
    currentDraftText = msg.draft_text || '';
    draftArea.textContent = currentDraftText;
    wordCountBadge.textContent = `글자 수: ${currentDraftText.length}자`;
    draftArea.scrollTop = 0; // Let user read from top

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
    currentState = msg.state;
    
    if (currentState === 'waiting_user') {
      // Re-trigger review view
      wsManager.trigger('requires_user_review', {
        draft_text: msg.draft,
        evaluation_report: msg.evaluation_report
      });
    } else if (currentState === 'idle') {
      highlightActiveStep(null);
      showPanel('idle');
      if (msg.draft) {
        draftArea.textContent = msg.draft;
        wordCountBadge.textContent = `글자 수: ${msg.draft.length}자`;
      }
    } else {
      // Is running (writing/judging/editing/reviewing)
      let activeStep = 'writer';
      if (currentState === 'editing') activeStep = 'editor';
      else if (currentState === 'judging') activeStep = 'judge';
      else if (currentState === 'reviewing') activeStep = 'reviewer';
      
      highlightActiveStep(activeStep);
      showPanel('running', { activeStep });
      if (msg.draft) {
        draftArea.textContent = msg.draft;
        wordCountBadge.textContent = `글자 수: ${msg.draft.length}자`;
        draftArea.scrollTop = draftArea.scrollHeight;
      }
    }
  });

  // Action listeners
  startBtn.addEventListener('click', () => {
    const sent = wsManager.send('start_writing');
    if (sent) {
      showPanel('running', { activeStep: 'plotter' });
      highlightActiveStep('plotter');
      draftArea.textContent = 'AI 플로터가 회차 줄거리를 분석하여 소설 씬(Scene)들을 구성하는 중입니다. 곧 집필이 시작됩니다...';
    } else {
      showToast('서버에 집필 명령을 보내지 못했습니다. 소켓 연결 상태를 확인하세요.', 'error');
    }
  });

  feedbackBtn.addEventListener('click', () => {
    const feedback = feedbackInput.value.trim();
    if (!feedback) {
      showToast('피드백 내용을 입력해 주세요.', 'error');
      return;
    }
    
    const sent = wsManager.send('submit_feedback', { feedback });
    if (sent) {
      feedbackInput.value = '';
      showPanel('running', { activeStep: 'editor' });
      highlightActiveStep('editor');
      showToast('피드백이 전송되어 교정 집필을 시작합니다.', 'success');
    } else {
      showToast('피드백 전송 실패', 'error');
    }
  });

  approveBtn.addEventListener('click', () => {
    createModal({
      title: '원고 승인 완료',
      content: '이 본문 버전을 본 에피소드의 최종 원고로 승인하고 DB에 영구 저장하시겠습니까?',
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

  // Clean up WebSockets subscriptions on navigation away
  container.addEventListener('destroyed', () => {
    console.log('Cleaning up Writing Monitor Page WebSocket subscriptions');
    offStatus();
    offState();
    offText();
    offReview();
    offSync();
    wsManager.disconnect();
  });

  return container;
}
