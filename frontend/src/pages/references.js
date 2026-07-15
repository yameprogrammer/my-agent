// References and Research Agent Management Page
import { api } from '../api/client.js';
import { showToast } from '../components/toast.js';
import { showSpinner, hideSpinner } from '../components/loading.js';
import { createModal } from '../components/modal.js';

// Markdown Parsing helper for beautiful layout rendering in modal
function parseMarkdownToHtml(markdown) {
  if (!markdown) return '';
  
  let html = markdown
    // Remove mock JSON tags if present
    .replace(/\\n/g, '\n')
    // Render H1/H2 Headers elegantly
    .replace(/^#\s+(.+)$/gm, '<h3 style="font-size: 1.3rem; font-weight: 800; color: var(--primary); border-bottom: 2px solid var(--border-color); padding-bottom: 8px; margin-top: 24px; margin-bottom: 14px; font-family: var(--font-heading);">$1</h3>')
    .replace(/^##\s+(.+)$/gm, '<h4 style="font-size: 1.12rem; font-weight: 700; color: var(--secondary); border-left: 4px solid var(--secondary); padding-left: 8px; margin-top: 20px; margin-bottom: 10px; font-family: var(--font-heading);">$1</h4>')
    .replace(/^###\s+(.+)$/gm, '<h5 style="font-size: 1rem; font-weight: 700; color: var(--text-primary); margin-top: 14px; margin-bottom: 8px;">$1</h5>')
    // Bullet lists styling
    .replace(/^\*\s+(.+)$/gm, '<li style="margin-left: 16px; margin-bottom: 8px; list-style-type: square; color: var(--text-secondary);">$1</li>')
    .replace(/^-\s+(.+)$/gm, '<li style="margin-left: 16px; margin-bottom: 8px; list-style-type: circle; color: var(--text-secondary);">$1</li>')
    // Bold tags to premium primary color text
    .replace(/\*\*([^*]+)\*\*/g, '<strong style="color: var(--primary); font-weight: 700;">$1</strong>')
    // Italics
    .replace(/\*([^*]+)\*/g, '<em style="color: var(--text-muted);">$1</em>')
    // Line breaks handling
    .replace(/\n/g, '<br>');
    
  // Wrap list items nicely
  html = html.replace(/(<li[^>]*>.*?<\/li>)/gs, '<ul style="margin: 12px 0; padding-left: 12px; display: flex; flex-direction: column; gap: 4px;">$1</ul>');
  
  return html;
}

export async function renderReferences(projectId) {
  const container = document.createElement('div');
  container.className = 'animate-fade-in';
  
  // Local state
  let references = [];
  let currentPage = 1;
  let totalCount = 0;
  const pageSize = 12;

  container.innerHTML = `
    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 24px;" class="flex-row-responsive">
      <div>
        <h3 style="font-family: var(--font-heading); font-size: 1.3rem; margin: 0; display: flex; align-items: center; gap: 8px;">
          <span>🔍</span> 고증 참고 자료 및 AI 리서치
        </h3>
        <p style="color: var(--text-secondary); font-size: 0.9rem; margin-top: 4px;">
          소설 창작에 필요한 사실 검증 자료와 AI 리서치 담당관의 고증 보고서를 수집하고 관리하세요
        </p>
      </div>
      <div style="display: flex; gap: 12px;">
        <button class="btn btn-secondary" id="btn-trigger-ai-research" style="height: 40px; border-radius: var(--radius-sm); font-weight: 600; display: flex; align-items: center; gap: 6px;">
          <span>🤖</span> AI 리서치 요청
        </button>
        <button class="btn btn-primary" id="btn-add-reference" style="height: 40px; border-radius: var(--radius-sm); font-weight: 600; display: flex; align-items: center; gap: 6px;">
          <span>➕</span> 자료 직접 추가
        </button>
      </div>
    </div>

    <!-- Search & Filter Controls -->
    <div class="glass-card" style="padding: 16px; margin-bottom: 24px; display: flex; gap: 16px; align-items: center; flex-wrap: wrap; background: rgba(255,255,255,0.02); border-color: var(--border-color);">
      <div style="flex: 1; min-width: 200px;">
        <input type="text" id="ref-search-input" class="search-input" placeholder="자료 제목 또는 내용 검색..." style="width: 100%; height: 40px; padding: 0 16px; border: 1px solid var(--border-color); border-radius: var(--radius-sm); background: transparent; color: var(--text-primary); outline: none; transition: border-color 0.2s;">
      </div>
      <div>
        <select id="ref-category-select" style="height: 40px; padding: 0 16px; border: 1px solid var(--border-color); border-radius: var(--radius-sm); background: var(--bg-card); color: var(--text-primary); outline: none; cursor: pointer; font-weight: 500;">
          <option value="">모든 카테고리</option>
          <option value="history">📜 역사 고증</option>
          <option value="science">🧪 과학 법칙</option>
          <option value="medical">🧬 의학/생명과학</option>
          <option value="law">⚖️ 법률/제도</option>
          <option value="etc">🔮 기타/커스텀</option>
        </select>
      </div>
    </div>

    <!-- References Grid -->
    <div id="references-grid" style="display: grid; grid-template-columns: repeat(auto-fill, minmax(340px, 1fr)); gap: 24px; margin-bottom: 24px;">
      <!-- References will be loaded here -->
    </div>

    <!-- Pagination controls -->
    <div id="ref-pagination" style="display: flex; justify-content: space-between; align-items: center; padding: 12px 0; border-top: 1px solid var(--border-color);">
      <span style="font-size: 0.88rem; color: var(--text-secondary);" id="ref-pagination-info"></span>
      <div style="display: flex; gap: 8px;">
        <button class="btn btn-secondary" id="ref-prev-btn" style="height: 38px; padding: 0 16px; font-weight: 600;" disabled>이전</button>
        <button class="btn btn-secondary" id="ref-next-btn" style="height: 38px; padding: 0 16px; font-weight: 600;" disabled>다음</button>
      </div>
    </div>
  `;

  // Select DOM Elements
  const grid = container.querySelector('#references-grid');
  const searchInput = container.querySelector('#ref-search-input');
  const categorySelect = container.querySelector('#ref-category-select');
  const paginationInfo = container.querySelector('#ref-pagination-info');
  const prevBtn = container.querySelector('#ref-prev-btn');
  const nextBtn = container.querySelector('#ref-next-btn');

  // Load References from Backend
  async function loadReferences() {
    showSpinner('참고 자료 목록을 불러오는 중...');
    const searchVal = searchInput.value;
    const catVal = categorySelect.value;
    
    let path = `/projects/${projectId}/references?page=${currentPage}&size=${pageSize}`;
    if (searchVal) path += `&search=${encodeURIComponent(searchVal)}`;
    if (catVal) path += `&category=${catVal}`;

    try {
      const res = await api.get(path);
      hideSpinner();
      references = res.items;
      totalCount = res.total;
      renderGrid();
      updatePagination();
    } catch (err) {
      hideSpinner();
      showToast(`참고 자료 로드 실패: ${err.message}`, 'error');
    }
  }

  // Render references grid
  function renderGrid() {
    grid.innerHTML = '';
    
    if (references.length === 0) {
      grid.innerHTML = `
        <div style="grid-column: 1/-1; padding: 80px; text-align: center; border-radius: var(--radius-md);" class="glass-card">
          <span style="font-size: 3rem; display: block; margin-bottom: 16px;">📚</span>
          <p style="color: var(--text-secondary); font-size: 1rem; font-weight: 600; margin: 0;">아직 등록된 고증 자료가 없습니다.</p>
          <p style="color: var(--text-muted); font-size: 0.85rem; margin-top: 6px;">직접 추가하거나 AI 리서치 담당관에게 조사를 의뢰해 보세요.</p>
        </div>
      `;
      return;
    }

    references.forEach(ref => {
      const card = document.createElement('div');
      card.className = 'glass-card';
      card.style.padding = '24px';
      card.style.display = 'flex';
      card.style.flexDirection = 'column';
      card.style.justifyContent = 'space-between';
      card.style.gap = '16px';
      card.style.cursor = 'pointer';
      card.style.borderRadius = 'var(--radius-md)';
      card.style.transition = 'transform 0.2s cubic-bezier(0.16, 1, 0.3, 1), box-shadow 0.2s, border-color 0.2s';
      card.style.border = '1px solid var(--border-color)';
      
      // Hover animations
      card.addEventListener('mouseenter', () => {
        card.style.transform = 'translateY(-4px) scale(1.005)';
        card.style.boxShadow = '0 12px 24px -10px rgba(0, 0, 0, 0.15)';
        card.style.borderColor = 'var(--primary)';
      });
      card.addEventListener('mouseleave', () => {
        card.style.transform = 'translateY(0) scale(1)';
        card.style.boxShadow = 'var(--shadow-sm)';
        card.style.borderColor = 'var(--border-color)';
      });

      // Badges
      let catLabel = '🔮 기타';
      let catColor = '#868e96';
      if (ref.category === 'history') { catLabel = '📜 역사 고증'; catColor = '#e8590c'; }
      else if (ref.category === 'science') { catLabel = '🧪 과학 법칙'; catColor = '#1098ad'; }
      else if (ref.category === 'medical') { catLabel = '🧬 의학/약학'; catColor = '#0ca678'; }
      else if (ref.category === 'law') { catLabel = '⚖️ 법률/제도'; catColor = '#7048e8'; }

      // Source type badges
      const sources = ref.source_type ? ref.source_type.split(',') : ['manual'];
      const sourceBadges = sources.map(src => {
        let label = src.toUpperCase();
        let bg = 'rgba(0,0,0,0.05)';
        if (src === 'academic') bg = 'rgba(28, 126, 214, 0.1); color: #1c7ed6;';
        if (src === 'sns') bg = 'rgba(214, 51, 108, 0.1); color: #d6336c;';
        if (src === 'community') bg = 'rgba(240, 140, 0, 0.1); color: #f08c00;';
        if (src === 'web') bg = 'rgba(116, 184, 22, 0.1); color: #74b816;';
        return `<span style="font-size: 0.72rem; padding: 2px 8px; border-radius: 4px; font-weight: 700; background: ${bg}">${label}</span>`;
      }).join(' ');

      const formattedDate = new Date(ref.created_at).toLocaleDateString();
      const rawContent = ref.content
        .replace(/[#*`\\n]/g, ' ') // formatting symbols clean
        .trim();

      card.innerHTML = `
        <div>
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
            <span style="font-size: 0.75rem; padding: 3px 10px; border-radius: 12px; font-weight: 700; background: ${catColor}15; color: ${catColor};">${catLabel}</span>
            <div style="display: flex; gap: 4px;">${sourceBadges}</div>
          </div>
          <h4 style="margin: 0 0 10px 0; font-size: 1.05rem; font-weight: 700; color: var(--text-primary); line-height: 1.35; font-family: var(--font-heading);">${ref.title}</h4>
          <p style="color: var(--text-secondary); font-size: 0.88rem; line-height: 1.5; margin: 0; display: -webkit-box; -webkit-line-clamp: 4; -webkit-box-orient: vertical; overflow: hidden;">
            ${rawContent}
          </p>
        </div>
        <div style="display: flex; justify-content: space-between; align-items: center; border-top: 1px solid var(--border-color); padding-top: 14px; margin-top: auto;">
          <span style="font-size: 0.75rem; color: var(--text-muted); font-weight: 500;">📅 수집일: ${formattedDate}</span>
          <div style="display: flex; gap: 8px;">
            ${ref.source_url ? `<a href="${ref.source_url}" target="_blank" class="btn-icon" title="출처 링크" style="font-size: 0.9rem;" onclick="event.stopPropagation()">🔗</a>` : ''}
            <button class="btn-icon btn-delete-ref" data-id="${ref.id}" title="삭제" style="color: var(--accent); font-size: 0.9rem;">🗑️</button>
          </div>
        </div>
      `;

      // Open detail modal on click
      card.addEventListener('click', () => showDetailModal(ref));

      // Delete button listener
      card.querySelector('.btn-delete-ref').addEventListener('click', async (e) => {
        e.stopPropagation();
        if (confirm(`'${ref.title}' 자료를 정말 삭제하시겠습니까?`)) {
          showSpinner('참고 자료를 삭제하는 중...');
          try {
            await api.delete(`/projects/${projectId}/references/${ref.id}`);
            hideSpinner();
            showToast('참고 자료가 정상 삭제되었습니다.', 'success');
            loadReferences();
          } catch (err) {
            hideSpinner();
            showToast(`삭제 실패: ${err.message}`, 'error');
          }
        }
      });

      grid.appendChild(card);
    });
  }

  // Update Pagination Controls
  function updatePagination() {
    const totalPages = Math.ceil(totalCount / pageSize) || 1;
    paginationInfo.textContent = `페이지 ${currentPage} / ${totalPages} (총 ${totalCount}개 자료)`;
    prevBtn.disabled = currentPage <= 1;
    nextBtn.disabled = currentPage >= totalPages;
  }

  // Show detailed document modal
  function showDetailModal(ref) {
    // Beautiful markdown parsing for reports
    const parsedBody = parseMarkdownToHtml(ref.content);
    
    let catLabel = '기타';
    let catColor = '#868e96';
    if (ref.category === 'history') { catLabel = '📜 역사 고증'; catColor = '#e8590c'; }
    else if (ref.category === 'science') { catLabel = '🧪 과학 법칙'; catColor = '#1098ad'; }
    else if (ref.category === 'medical') { catLabel = '🧬 의학/약학'; catColor = '#0ca678'; }
    else if (ref.category === 'law') { catLabel = '⚖️ 법률/제도'; catColor = '#7048e8'; }

    const contentHtml = `
      <div style="padding: 4px 0; max-height: 72vh; overflow-y: auto; display: flex; flex-direction: column; gap: 18px;">
        <div style="display: flex; gap: 8px; align-items: center; border-bottom: 1px solid var(--border-color); padding-bottom: 12px;">
          <span style="font-size: 0.78rem; font-weight: 700; background: ${catColor}15; color: ${catColor}; padding: 4px 12px; border-radius: 20px;">
            ${catLabel}
          </span>
          <span style="font-size: 0.78rem; font-weight: 700; background: rgba(0,0,0,0.05); padding: 4px 12px; border-radius: 20px; color: var(--text-secondary);">
            📡 출처: ${ref.source_type ? ref.source_type.toUpperCase().replace(/,/g, ' + ') : '직접 수동 입력'}
          </span>
        </div>
        
        <div class="markdown-body" style="font-size: 0.96rem; line-height: 1.65; color: var(--text-primary); padding: 24px; border-radius: var(--radius-md); background: rgba(255,255,255,0.01); border: 1px solid var(--border-color); box-shadow: inset 0 2px 4px rgba(0,0,0,0.02);">
          ${parsedBody}
        </div>
        
        ${ref.source_url ? `
          <div style="text-align: right; margin-top: 6px;">
            <a href="${ref.source_url}" target="_blank" class="btn btn-secondary" style="display: inline-flex; align-items: center; gap: 6px; font-size: 0.88rem; height: 38px; border-radius: var(--radius-sm);">
              <span>🔗</span> 원본 출처 사이트 이동
            </a>
          </div>
        ` : ''}
      </div>
    `;

    createModal({
      title: ref.title,
      content: contentHtml,
      showFooter: false
    });
  }

  // Show Manual reference insertion modal
  container.querySelector('#btn-add-reference').addEventListener('click', () => {
    const formEl = document.createElement('div');
    formEl.innerHTML = `
      <form id="form-add-ref" style="display: flex; flex-direction: column; gap: 16px; padding: 8px 0;">
        <div style="display: flex; flex-direction: column; gap: 6px;">
          <label style="font-size: 0.88rem; font-weight: 600;">자료 제목 *</label>
          <input type="text" id="add-ref-title" style="height: 40px; padding: 0 12px; border: 1px solid var(--border-color); border-radius: var(--radius-sm); outline: none;" placeholder="예: 중세시대 흑사병의 사망율 통계" required>
        </div>
        
        <div style="display: flex; gap: 16px;" class="flex-row-responsive">
          <div style="flex: 1; display: flex; flex-direction: column; gap: 6px;">
            <label style="font-size: 0.88rem; font-weight: 600;">카테고리 분류</label>
            <select id="add-ref-category" style="height: 40px; padding: 0 12px; border: 1px solid var(--border-color); border-radius: var(--radius-sm); background: var(--bg-card); cursor: pointer;">
              <option value="etc">🔮 기타/커스텀</option>
              <option value="history">📜 역사 고증</option>
              <option value="science">🧪 과학 법칙</option>
              <option value="medical">🧬 의학/생명과학</option>
              <option value="law">⚖️ 법률/제도</option>
            </select>
          </div>
          <div style="flex: 1; display: flex; flex-direction: column; gap: 6px;">
            <label style="font-size: 0.88rem; font-weight: 600;">자료 출처 URL</label>
            <input type="url" id="add-ref-url" style="height: 40px; padding: 0 12px; border: 1px solid var(--border-color); border-radius: var(--radius-sm); outline: none;" placeholder="https://example.com/source">
          </div>
        </div>
        
        <div style="display: flex; flex-direction: column; gap: 6px;">
          <label style="font-size: 0.88rem; font-weight: 600;">자료 본문 내용 *</label>
          <textarea id="add-ref-content" style="height: 200px; padding: 12px; border: 1px solid var(--border-color); border-radius: var(--radius-sm); outline: none; resize: vertical;" placeholder="고증에 참고할 상세 정보나 기록문을 작성해 주세요..." required></textarea>
        </div>
      </form>
    `;

    createModal({
      title: '참고 자료 직접 수동 등록',
      content: formEl,
      confirmText: '등록하기',
      cancelText: '취소',
      onConfirm: async (dismiss) => {
        const form = formEl.querySelector('#form-add-ref');
        if (!form.reportValidity()) return false;

        const title = formEl.querySelector('#add-ref-title').value;
        const category = formEl.querySelector('#add-ref-category').value;
        const source_url = formEl.querySelector('#add-ref-url').value || null;
        const content = formEl.querySelector('#add-ref-content').value;

        showSpinner('참고 자료 등록 중...');
        try {
          await api.post(`/projects/${projectId}/references`, {
            title,
            content,
            category,
            source_type: 'manual',
            source_url
          });
          hideSpinner();
          showToast('새 참고 자료가 수동 등록되었습니다.', 'success');
          dismiss();
          currentPage = 1;
          loadReferences();
        } catch (err) {
          hideSpinner();
          showToast(`등록 실패: ${err.message}`, 'error');
          return false;
        }
      }
    });
  });

  // Show AI Researcher Trigger Modal
  container.querySelector('#btn-trigger-ai-research').addEventListener('click', () => {
    const formEl = document.createElement('div');
    formEl.innerHTML = `
      <form id="form-ai-research" style="display: flex; flex-direction: column; gap: 16px; padding: 8px 0;">
        <div style="display: flex; flex-direction: column; gap: 6px;">
          <label style="font-size: 0.88rem; font-weight: 600;">🔍 리서치 연구 주제 *</label>
          <input type="text" id="research-topic" style="height: 40px; padding: 0 12px; border: 1px solid var(--border-color); border-radius: var(--radius-sm); outline: none;" placeholder="예: 인간을 포함한 포유류의 과 수면이 미치는 영향" required>
          <span style="font-size: 0.78rem; color: var(--text-muted);">에이전트가 웹/학술DB 등에서 팩트체크할 주제 키워드를 작성해 주세요.</span>
        </div>

        <div style="display: flex; flex-direction: column; gap: 6px;">
          <label style="font-size: 0.88rem; font-weight: 600;">📁 저장할 카테고리</label>
          <select id="research-category" style="height: 40px; padding: 0 12px; border: 1px solid var(--border-color); border-radius: var(--radius-sm); background: var(--bg-card); cursor: pointer; width: 200px;">
            <option value="medical">🧬 의학/생명과학</option>
            <option value="history">📜 역사 고증</option>
            <option value="science">🧪 과학 법칙</option>
            <option value="law">⚖️ 법률/제도</option>
            <option value="etc">🔮 기타/커스텀</option>
          </select>
        </div>

        <div style="display: flex; flex-direction: column; gap: 8px;">
          <label style="font-size: 0.88rem; font-weight: 600;">📡 대상 데이터 풀 타겟팅 (복수 선택 가능)</label>
          <div style="display: flex; flex-wrap: wrap; gap: 18px; margin-top: 4px;">
            <label style="display: flex; align-items: center; gap: 8px; font-size: 0.88rem; cursor: pointer;">
              <input type="checkbox" name="research-source" value="web" checked style="width: 16px; height: 16px; cursor: pointer;">
              <span>🌐 일반 웹 포털</span>
            </label>
            <label style="display: flex; align-items: center; gap: 8px; font-size: 0.88rem; cursor: pointer;">
              <input type="checkbox" name="research-source" value="academic" checked style="width: 16px; height: 16px; cursor: pointer;">
              <span>🎓 학술 논문/지식지</span>
            </label>
            <label style="display: flex; align-items: center; gap: 8px; font-size: 0.88rem; cursor: pointer;">
              <input type="checkbox" name="research-source" value="sns" style="width: 16px; height: 16px; cursor: pointer;">
              <span>💬 SNS (트렌드/여론)</span>
            </label>
            <label style="display: flex; align-items: center; gap: 8px; font-size: 0.88rem; cursor: pointer;">
              <input type="checkbox" name="research-source" value="community" style="width: 16px; height: 16px; cursor: pointer;">
              <span>👥 커뮤니티/포럼</span>
            </label>
          </div>
        </div>
      </form>
    `;

    createModal({
      title: 'AI 리서치 담당관 호출',
      content: formEl,
      confirmText: '리서치 의뢰 시작',
      cancelText: '취소',
      onConfirm: async (dismiss) => {
        const form = formEl.querySelector('#form-ai-research');
        if (!form.reportValidity()) return false;

        const topic = formEl.querySelector('#research-topic').value;
        const category = formEl.querySelector('#research-category').value;
        
        const checkboxes = formEl.querySelectorAll('input[name="research-source"]:checked');
        const target_sources = Array.from(checkboxes).map(cb => cb.value);

        if (target_sources.length === 0) {
          showToast('최소 한 개 이상의 대상 데이터 풀을 선택해야 합니다.', 'warning');
          return false;
        }

        showSpinner('AI 리서치 태스크를 전달하는 중...');
        try {
          await api.post(`/projects/${projectId}/references/research`, {
            topic,
            category,
            target_sources
          });
          hideSpinner();
          showToast('🤖 리서치 의뢰 접수 완료! 백그라운드 조사가 개시되었습니다.', 'info');
          dismiss();
          
          setTimeout(() => {
            loadReferences();
          }, 2500);
        } catch (err) {
          hideSpinner();
          showToast(`리서치 기동 실패: ${err.message}`, 'error');
          return false;
        }
      }
    });
  });

  // Bind controls event listeners
  let searchTimeout;
  searchInput.addEventListener('input', () => {
    clearTimeout(searchTimeout);
    searchTimeout = setTimeout(() => {
      currentPage = 1;
      loadReferences();
    }, 400);
  });

  categorySelect.addEventListener('change', () => {
    currentPage = 1;
    loadReferences();
  });

  prevBtn.addEventListener('click', () => {
    if (currentPage > 1) {
      currentPage--;
      loadReferences();
    }
  });

  nextBtn.addEventListener('click', () => {
    const totalPages = Math.ceil(totalCount / pageSize);
    if (currentPage < totalPages) {
      currentPage++;
      loadReferences();
    }
  });

  // Connect to WebSocket for real-time alerts if not connected (Phase 3)
  let wsCleanup = null;
  async function initWebSocketAlerts() {
    try {
      const episodes = await api.get(`/projects/${projectId}/episodes`);
      if (episodes && episodes.length > 0) {
        const epId = episodes[0].id;
        const { wsManager } = await import('../api/websocket.js');
        wsManager.connect(projectId, epId);
        
        wsCleanup = wsManager.on('research_completed', (data) => {
          if (data.project_id === parseInt(projectId)) {
            showToast(data.message || '리서치가 성공적으로 완료되었습니다!', 'success');
            loadReferences();
          }
        });
      }
    } catch (e) {
      console.warn('Failed to initialize WebSocket real-time alerts for references page:', e);
    }
  }

  // Bind container destruction to cleanup listeners
  container.addEventListener('destroy', () => {
    if (wsCleanup) {
      wsCleanup();
    }
  });

  // First Load
  loadReferences();
  initWebSocketAlerts();

  return container;
}
