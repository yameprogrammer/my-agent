// Character Sheets Page
import { api } from '../api/client.js';
import { showToast } from '../components/toast.js';
import { showSpinner, hideSpinner } from '../components/loading.js';
import { createModal } from '../components/modal.js';

export async function renderCharacters(projectId) {
  const container = document.createElement('div');
  container.className = 'animate-fade-in';
  
  let allCharacters = [];

  container.innerHTML = `
    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 24px;" class="flex-row-responsive">
      <div>
        <h3 style="font-family: var(--font-heading); font-size: 1.3rem; margin: 0; display: flex; align-items: center; gap: 8px;">
          <span>👥</span> 캐릭터 시트 (Character Sheets)
        </h3>
        <p style="color: var(--text-secondary); font-size: 0.9rem; margin-top: 4px;">등장인물의 이름, 역할 중요도, 인물 관계 설정을 등록하고 관리하세요</p>
      </div>
      <button class="btn btn-primary" id="btn-add-character" style="height: 40px;">
        <span>➕</span> 캐릭터 추가
      </button>
    </div>

    <div id="characters-sections" style="display: flex; flex-direction: column; gap: 32px;">
      <!-- Categorized characters lists -->
    </div>
  `;

  const sectionsDiv = container.querySelector('#characters-sections');
  const addBtn = container.querySelector('#btn-add-character');

  async function loadCharacters() {
    showSpinner('캐릭터 목록을 불러오는 중...');
    try {
      allCharacters = await api.get(`/projects/${projectId}/characters`);
      hideSpinner();
      renderCharactersList();
    } catch (err) {
      hideSpinner();
      showToast(`캐릭터 로드 실패: ${err.message}`, 'error');
    }
  }

  function renderCharactersList() {
    sectionsDiv.innerHTML = '';
    
    if (allCharacters.length === 0) {
      sectionsDiv.innerHTML = `
        <div style="padding: 48px; text-align: center;" class="glass-card">
          <span style="font-size: 2.5rem; display: block; margin-bottom: 12px;">👤</span>
          <p style="color: var(--text-secondary); font-size: 0.95rem; font-weight: 500;">아직 등록된 등장인물이 없습니다.</p>
        </div>
      `;
      return;
    }

    // Categorize characters
    const groups = {
      protagonist: { title: '👑 주인공 (Protagonist)', items: [] },
      deuteragonist: { title: '🥈 주연 / 라이벌 (Deuteragonist)', items: [] },
      major: { title: '👥 주요 조연 (Major)', items: [] },
      minor: { title: '🌱 기타 등장인물 (Minor)', items: [] }
    };

    allCharacters.forEach(c => {
      const importance = c.importance || 'minor';
      if (groups[importance]) {
        groups[importance].items.push(c);
      } else {
        groups.minor.items.push(c);
      }
    });

    // Render each category section
    Object.keys(groups).forEach(key => {
      const group = groups[key];
      if (group.items.length === 0) return; // Skip empty groups
      
      const section = document.createElement('section');
      section.innerHTML = `
        <h4 style="font-family: var(--font-heading); font-size: 1.05rem; font-weight: 600; color: var(--text-primary); margin-bottom: 16px; padding-bottom: 8px; border-bottom: 2px solid var(--border-color); display: flex; align-items: center; gap: 8px;">
          ${group.title}
          <span class="badge badge-primary" style="font-size: 0.75rem; padding: 2px 8px;">${group.items.length}</span>
        </h4>
        <div class="char-grid" style="display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 20px;">
          <!-- Cards -->
        </div>
      `;
      
      const grid = section.querySelector('.char-grid');
      group.items.forEach(char => {
        const card = createCharacterCard(char);
        grid.appendChild(card);
      });
      
      sectionsDiv.appendChild(section);
    });
  }

  function getImportanceBadge(importance) {
    if (importance === 'protagonist') return '<span class="badge badge-primary">주인공</span>';
    if (importance === 'deuteragonist') return '<span class="badge badge-success">조연</span>';
    if (importance === 'major') return '<span class="badge badge-secondary" style="background-color: #fef3c7; color: #b45309;">주요인물</span>';
    return '<span class="badge badge-secondary">기타</span>';
  }

  function createCharacterCard(char) {
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
          <h5 style="font-family: var(--font-heading); font-size: 1.1rem; font-weight: 600; color: var(--text-primary); margin: 0;">
            ${char.name}
          </h5>
        </div>
        <p style="color: var(--text-secondary); font-size: 0.85rem; line-height: 1.5; margin-bottom: 12px;">
          ${char.description}
        </p>
      </div>
      <div style="display: flex; justify-content: space-between; align-items: center; border-top: 1px solid var(--border-color); padding-top: 12px; margin-top: auto;">
        ${getImportanceBadge(char.importance)}
        <div style="display: flex; gap: 8px;">
          <button class="btn-edit-char" title="수정" style="background: none; border: none; font-size: 0.95rem; cursor: pointer;">✏️</button>
          <button class="btn-delete-char" title="삭제" style="background: none; border: none; font-size: 0.95rem; cursor: pointer;">🗑️</button>
        </div>
      </div>
    `;

    card.querySelector('.btn-edit-char').addEventListener('click', () => openFormModal(char));
    card.querySelector('.btn-delete-char').addEventListener('click', () => confirmDelete(char, card));

    return card;
  }

  function confirmDelete(char, cardElement) {
    createModal({
      title: '캐릭터 삭제',
      content: `캐릭터 <strong>"${char.name}"</strong>의 시트를 정말로 삭제하시겠습니까?<br><span style="color: var(--text-muted); font-size: 0.8rem; display: block; margin-top: 4px;">세계관 설정에서 제거되며 AI 집필 컨텍스트에 더 이상 주입되지 않습니다.</span>`,
      confirmText: '삭제',
      cancelText: '취소',
      isDangerous: true,
      onConfirm: async () => {
        showSpinner('캐릭터 삭제 중...');
        try {
          await api.delete(`/projects/${projectId}/characters/${char.id}`);
          hideSpinner();
          showToast(`"${char.name}" 캐릭터를 성공적으로 삭제했습니다.`, 'success');
          
          cardElement.style.transform = 'scale(0.9)';
          cardElement.style.opacity = '0';
          setTimeout(() => {
            cardElement.remove();
            allCharacters = allCharacters.filter(c => c.id !== char.id);
            renderCharactersList();
          }, 250);
        } catch (err) {
          hideSpinner();
          showToast(`삭제 실패: ${err.message}`, 'error');
        }
      }
    });
  }

  function openFormModal(char = null) {
    const isEdit = !!char;
    const formContainer = document.createElement('div');
    formContainer.innerHTML = `
      <div class="form-group">
        <label class="form-label" for="char-name">캐릭터 이름</label>
        <input class="form-control" type="text" id="char-name" placeholder="예: 레오나르도 에르반, 세라핀" required maxlength="50" value="${isEdit ? char.name : ''}">
      </div>
      
      <div class="form-group">
        <label class="form-label" for="char-importance">중요도 / 역할</label>
        <select class="form-control" id="char-importance">
          <option value="protagonist" ${isEdit && char.importance === 'protagonist' ? 'selected' : ''}>👑 주인공 (Protagonist)</option>
          <option value="deuteragonist" ${isEdit && char.importance === 'deuteragonist' ? 'selected' : ''}>🥈 주연 / 라이벌 (Deuteragonist)</option>
          <option value="major" ${isEdit && char.importance === 'major' ? 'selected' : ''}>👥 주요 조연 (Major)</option>
          <option value="minor" ${isEdit && char.importance === 'minor' ? 'selected' : ''}>🌱 기타 등장인물 (Minor)</option>
        </select>
      </div>
      
      <div class="form-group">
        <label class="form-label" for="char-desc">캐릭터 외양 / 내면 묘사 및 역할 설정</label>
        <textarea class="form-control" id="char-desc" placeholder="나이, 성격, 행동 양식, 갈등 요소 등을 상세하게 작성해 주세요. 인물 일관성을 판단하는 Judge 에이전트와 Writer 에이전트가 활용합니다." style="height: 140px; resize: none;" required>${isEdit ? char.description : ''}</textarea>
      </div>
    `;

    createModal({
      title: isEdit ? '캐릭터 시트 수정' : '새 캐릭터 추가',
      content: formContainer,
      confirmText: isEdit ? '수정' : '추가',
      cancelText: '취소',
      onConfirm: async (dismiss) => {
        const name = formContainer.querySelector('#char-name').value.trim();
        const importance = formContainer.querySelector('#char-importance').value;
        const description = formContainer.querySelector('#char-desc').value.trim();

        if (!name || !description) {
          showToast('이름과 인물 묘사를 모두 입력해 주세요.', 'error');
          return false;
        }

        showSpinner(isEdit ? '캐릭터 수정 중...' : '캐릭터 등록 중...');
        try {
          if (isEdit) {
            const updated = await api.put(`/projects/${projectId}/characters/${char.id}`, {
              name,
              importance,
              description
            });
            showToast(`"${name}" 캐릭터 정보를 수정했습니다.`, 'success');
            allCharacters = allCharacters.map(c => c.id === char.id ? updated : c);
          } else {
            const created = await api.post(`/projects/${projectId}/characters`, {
              name,
              importance,
              description
            });
            showToast(`"${name}" 캐릭터를 등록했습니다.`, 'success');
            allCharacters.push(created);
          }
          
          hideSpinner();
          dismiss();
          renderCharactersList();
        } catch (err) {
          hideSpinner();
          showToast(`저장 실패: ${err.message}`, 'error');
          return false;
        }
      }
    });
  }

  addBtn.addEventListener('click', () => openFormModal());
  
  // Load initially
  loadCharacters();

  return container;
}
