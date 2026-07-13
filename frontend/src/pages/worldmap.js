// World Settings (Lorebook) Page
import { api } from '../api/client.js';
import { showToast } from '../components/toast.js';
import { showSpinner, hideSpinner } from '../components/loading.js';
import { createModal } from '../components/modal.js';

export async function renderWorldMap(projectId) {
  const container = document.createElement('div');
  container.className = 'animate-fade-in';
  
  let currentCategory = 'all';
  let allSettings = [];

  container.innerHTML = `
    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 24px;" class="flex-row-responsive">
      <div>
        <h3 style="font-family: var(--font-heading); font-size: 1.3rem; margin: 0; display: flex; align-items: center; gap: 8px;">
          <span>🌍</span> 세계관 설정집 (Lorebook)
        </h3>
        <p style="color: var(--text-secondary); font-size: 0.9rem; margin-top: 4px;">소설의 고유 명사, 지명, 마법 법칙, 설정 데이터베이스를 구축하세요</p>
      </div>
      <button class="btn btn-primary" id="btn-add-lore" style="height: 40px;">
        <span>➕</span> 설정 추가
      </button>
    </div>

    <!-- Category filter tabs -->
    <div style="display: flex; gap: 8px; margin-bottom: 24px; border-bottom: 1px solid var(--border-color); padding-bottom: 12px; overflow-x: auto;">
      <button class="btn btn-secondary category-tab active" data-category="all" style="padding: 6px 14px; font-size: 0.85rem; border-radius: var(--radius-full);">전체</button>
      <button class="btn btn-secondary category-tab" data-category="lore" style="padding: 6px 14px; font-size: 0.85rem; border-radius: var(--radius-full);">📜 일반 설정</button>
      <button class="btn btn-secondary category-tab" data-category="location" style="padding: 6px 14px; font-size: 0.85rem; border-radius: var(--radius-full);">📍 지명 / 위치</button>
      <button class="btn btn-secondary category-tab" data-category="item" style="padding: 6px 14px; font-size: 0.85rem; border-radius: var(--radius-full);">⚔️ 아이템 / 아티팩트</button>
      <button class="btn btn-secondary category-tab" data-category="concept" style="padding: 6px 14px; font-size: 0.85rem; border-radius: var(--radius-full);">💡 마법 / 개념</button>
    </div>

    <div id="lores-grid" style="display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 20px;">
      <!-- Lore cards will render here -->
    </div>
  `;

  const grid = container.querySelector('#lores-grid');
  const addBtn = container.querySelector('#btn-add-lore');
  const categoryTabs = container.querySelectorAll('.category-tab');

  async function loadSettings() {
    showSpinner('세계관 설정을 조회하는 중...');
    try {
      allSettings = await api.get(`/projects/${projectId}/world-settings`);
      hideSpinner();
      renderSettings();
    } catch (err) {
      hideSpinner();
      showToast(`설정 로딩 실패: ${err.message}`, 'error');
    }
  }

  function renderSettings() {
    grid.innerHTML = '';
    
    const filtered = currentCategory === 'all' 
      ? allSettings 
      : allSettings.filter(s => s.category === currentCategory);

    if (filtered.length === 0) {
      grid.innerHTML = `
        <div style="grid-column: 1/-1; padding: 48px; text-align: center;" class="glass-card">
          <span style="font-size: 2.5rem; display: block; margin-bottom: 12px;">🗺️</span>
          <p style="color: var(--text-secondary); font-size: 0.95rem; font-weight: 500;">
            ${currentCategory === 'all' ? '아직 등록된 설정이 없습니다.' : '이 카테고리에 해당하는 설정이 없습니다.'}
          </p>
        </div>
      `;
      return;
    }

    filtered.forEach(setting => {
      const card = createSettingCard(setting);
      grid.appendChild(card);
    });
  }

  function getCategoryBadge(category) {
    if (category === 'lore') return '<span class="badge badge-primary">📜 일반 설정</span>';
    if (category === 'location') return '<span class="badge badge-success">📍 위치</span>';
    if (category === 'item') return '<span class="badge badge-secondary" style="background-color: #fef3c7; color: #b45309;">⚔️ 아이템</span>';
    if (category === 'concept') return '<span class="badge badge-secondary" style="background-color: #e0f2fe; color: #0369a1;">💡 개념</span>';
    return `<span class="badge badge-secondary">${category}</span>`;
  }

  function createSettingCard(setting) {
    const card = document.createElement('div');
    card.className = 'glass-card animate-fade-in';
    card.style.padding = '20px';
    card.style.position = 'relative';
    card.style.display = 'flex';
    card.style.flexDirection = 'column';
    card.style.justifyContent = 'space-between';
    card.style.minHeight = '140px';
    
    card.innerHTML = `
      <div>
        <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 8px; padding-right: 56px;">
          <h4 style="font-family: var(--font-heading); font-size: 1.1rem; font-weight: 600; color: var(--text-primary); margin: 0;">
            ${setting.keyword}
          </h4>
        </div>
        <p style="color: var(--text-secondary); font-size: 0.85rem; line-height: 1.5; margin-bottom: 12px;">
          ${setting.description}
        </p>
      </div>
      <div style="display: flex; justify-content: space-between; align-items: center; border-top: 1px solid var(--border-color); padding-top: 12px; margin-top: auto;">
        ${getCategoryBadge(setting.category)}
        <div style="display: flex; gap: 8px;">
          <button class="btn-edit-lore" title="수정" style="background: none; border: none; font-size: 0.95rem; cursor: pointer;">✏️</button>
          <button class="btn-delete-lore" title="삭제" style="background: none; border: none; font-size: 0.95rem; cursor: pointer;">🗑️</button>
        </div>
      </div>
    `;

    card.querySelector('.btn-edit-lore').addEventListener('click', () => openFormModal(setting));
    card.querySelector('.btn-delete-lore').addEventListener('click', () => confirmDelete(setting, card));

    return card;
  }

  function confirmDelete(setting, cardElement) {
    createModal({
      title: '설정 삭제',
      content: `세계관 키워드 <strong>"${setting.keyword}"</strong>을 정말로 삭제하시겠습니까?<br><span style="color: var(--text-muted); font-size: 0.8rem; display: block; margin-top: 4px;">지식베이스에서 제거되며 AI 집필 컨텍스트에 더 이상 인젝션되지 않습니다.</span>`,
      confirmText: '삭제',
      cancelText: '취소',
      isDangerous: true,
      onConfirm: async () => {
        showSpinner('설정 삭제 중...');
        try {
          await api.delete(`/projects/${projectId}/world-settings/${setting.id}`);
          hideSpinner();
          showToast(`"${setting.keyword}" 설정을 성공적으로 삭제했습니다.`, 'success');
          
          cardElement.style.transform = 'scale(0.9)';
          cardElement.style.opacity = '0';
          setTimeout(() => {
            cardElement.remove();
            allSettings = allSettings.filter(s => s.id !== setting.id);
            if (grid.children.length === 0) {
              renderSettings();
            }
          }, 250);
        } catch (err) {
          hideSpinner();
          showToast(`삭제 실패: ${err.message}`, 'error');
        }
      }
    });
  }

  function openFormModal(setting = null) {
    const isEdit = !!setting;
    const formContainer = document.createElement('div');
    formContainer.innerHTML = `
      <div class="form-group">
        <label class="form-label" for="ws-keyword">세계관 키워드 / 고유명사</label>
        <input class="form-control" type="text" id="ws-keyword" placeholder="예: 아발론 제국, 테트라 마법진" required maxlength="100" value="${isEdit ? setting.keyword : ''}">
      </div>
      
      <div class="form-group">
        <label class="form-label" for="ws-category">카테고리</label>
        <select class="form-control" id="ws-category">
          <option value="lore" ${isEdit && setting.category === 'lore' ? 'selected' : ''}>📜 일반 설정</option>
          <option value="location" ${isEdit && setting.category === 'location' ? 'selected' : ''}>📍 지명 / 위치</option>
          <option value="item" ${isEdit && setting.category === 'item' ? 'selected' : ''}>⚔️ 아이템 / 아티팩트</option>
          <option value="concept" ${isEdit && setting.category === 'concept' ? 'selected' : ''}>💡 마법 / 개념</option>
        </select>
      </div>
      
      <div class="form-group">
        <label class="form-label" for="ws-desc">상세 설명 / 설정 내용</label>
        <textarea class="form-control" id="ws-desc" placeholder="설정의 상세 내용을 명확하게 기술해 주세요. RAG를 통해 관련 씬 작성 시 AI 작가에게 주입됩니다." style="height: 140px; resize: none;" required>${isEdit ? setting.description : ''}</textarea>
      </div>
    `;

    createModal({
      title: isEdit ? '세계관 설정 수정' : '새 세계관 설정 추가',
      content: formContainer,
      confirmText: isEdit ? '수정' : '추가',
      cancelText: '취소',
      onConfirm: async (dismiss) => {
        const keyword = formContainer.querySelector('#ws-keyword').value.trim();
        const category = formContainer.querySelector('#ws-category').value;
        const description = formContainer.querySelector('#ws-desc').value.trim();

        if (!keyword || !description) {
          showToast('키워드와 상세 설명을 모두 입력해 주세요.', 'error');
          return false;
        }

        showSpinner(isEdit ? '설정 수정 중...' : '신규 설정 등록 중...');
        try {
          if (isEdit) {
            const updated = await api.put(`/projects/${projectId}/world-settings/${setting.id}`, {
              keyword,
              category,
              description
            });
            showToast(`"${keyword}" 설정을 수정했습니다.`, 'success');
            allSettings = allSettings.map(s => s.id === setting.id ? updated : s);
          } else {
            const created = await api.post(`/projects/${projectId}/world-settings`, {
              keyword,
              category,
              description
            });
            showToast(`"${keyword}" 설정을 추가했습니다.`, 'success');
            allSettings.push(created);
          }
          
          hideSpinner();
          dismiss();
          renderSettings();
        } catch (err) {
          hideSpinner();
          showToast(`저장 실패: ${err.message}`, 'error');
          return false;
        }
      }
    });
  }

  // Category tab filter event
  categoryTabs.forEach(tab => {
    tab.addEventListener('click', () => {
      categoryTabs.forEach(t => t.classList.remove('active'));
      tab.classList.add('active');
      currentCategory = tab.getAttribute('data-category');
      renderSettings();
    });
  });

  addBtn.addEventListener('click', () => openFormModal());
  
  // Load data initially
  loadSettings();

  return container;
}
