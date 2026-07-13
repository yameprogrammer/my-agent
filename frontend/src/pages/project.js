// Project Detail Page Container with tab navigation
import { api } from '../api/client.js';
import { showSpinner, hideSpinner } from '../components/loading.js';
import { renderBrainstorm } from './brainstorm.js';
import { renderWorldMap } from './worldmap.js';
import { renderCharacters } from './characters.js';
import { renderEpisodes } from './episodes.js';
import { renderSettings } from './settings.js';

export async function renderProject(params) {
  const projectId = params.id;
  const container = document.createElement('div');
  container.className = 'animate-fade-in';
  container.style.width = '100%';
  
  let activeTab = 'episodes'; // default tab

  container.innerHTML = `
    <!-- Project Info Header -->
    <div class="glass-card" style="padding: 24px; margin-bottom: 24px; display: flex; justify-content: space-between; align-items: center;" class="flex-row-responsive">
      <div>
        <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 6px;">
          <a href="#/" style="font-size: 0.9rem; font-weight: 600; display: flex; align-items: center; gap: 4px;">
            <span>⬅️</span> 대시보드로 돌아가기
          </a>
        </div>
        <h2 id="project-header-title" style="font-family: var(--font-heading); font-size: 1.8rem; color: var(--text-primary); margin: 0;"></h2>
        <p id="project-header-synopsis" style="color: var(--text-secondary); font-size: 0.9rem; margin-top: 6px; max-width: 800px; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; line-height: 1.4;"></p>
      </div>
      <div style="text-align: right;" id="project-header-model-info">
        <!-- Model info badges -->
      </div>
    </div>

    <!-- Tabs Navigation Bar -->
    <div class="glass-card" style="padding: 0 12px; margin-bottom: 24px; border-bottom: none;">
      <div style="display: flex; overflow-x: auto; scrollbar-width: none;">
        <button class="project-tab-btn" data-tab="episodes" style="padding: 16px 20px; font-weight: 600; font-size: 0.95rem; border: none; background: none; color: var(--text-secondary); cursor: pointer; border-bottom: 3px solid transparent; transition: all var(--transition-fast);">
          📚 회차 관리
        </button>
        <button class="project-tab-btn" data-tab="brainstorm" style="padding: 16px 20px; font-weight: 600; font-size: 0.95rem; border: none; background: none; color: var(--text-secondary); cursor: pointer; border-bottom: 3px solid transparent; transition: all var(--transition-fast);">
          💡 AI 기획 파트너
        </button>
        <button class="project-tab-btn" data-tab="worldmap" style="padding: 16px 20px; font-weight: 600; font-size: 0.95rem; border: none; background: none; color: var(--text-secondary); cursor: pointer; border-bottom: 3px solid transparent; transition: all var(--transition-fast);">
          🌍 세계관 설정집
        </button>
        <button class="project-tab-btn" data-tab="characters" style="padding: 16px 20px; font-weight: 600; font-size: 0.95rem; border: none; background: none; color: var(--text-secondary); cursor: pointer; border-bottom: 3px solid transparent; transition: all var(--transition-fast);">
          👥 캐릭터 시트
        </button>
        <button class="project-tab-btn" data-tab="settings" style="padding: 16px 20px; font-weight: 600; font-size: 0.95rem; border: none; background: none; color: var(--text-secondary); cursor: pointer; border-bottom: 3px solid transparent; transition: all var(--transition-fast);">
          ⚙️ 프로젝트 설정
        </button>
      </div>
    </div>

    <!-- Active Tab Content Container -->
    <div id="project-tab-content" style="width: 100%;" class="animate-fade-in"></div>
  `;

  const tabContent = container.querySelector('#project-tab-content');
  const tabBtns = container.querySelectorAll('.project-tab-btn');

  async function loadProjectHeader() {
    try {
      const project = await api.get(`/projects/${projectId}`);
      container.querySelector('#project-header-title').textContent = project.title;
      container.querySelector('#project-header-synopsis').textContent = project.synopsis || '등록된 소설 시놉시스가 없습니다.';
      
      const modelInfo = container.querySelector('#project-header-model-info');
      let provBadge = '';
      if (project.llm_provider === 'openai') provBadge = '<span class="badge badge-primary">OpenAI</span>';
      else if (project.llm_provider === 'google') provBadge = '<span class="badge badge-success">Gemini</span>';
      else provBadge = `<span class="badge badge-secondary">${project.llm_provider}</span>`;
      
      modelInfo.innerHTML = `
        <span style="font-size: 0.75rem; color: var(--text-muted); display: block; margin-bottom: 4px;">지정된 기본 AI 모델</span>
        <div style="font-weight: 600; font-size: 0.9rem; display: flex; align-items: center; gap: 8px;">
          ${provBadge} ${project.llm_model}
        </div>
      `;
    } catch (err) {
      console.error('Failed to load project header:', err);
    }
  }

  async function switchTab(tabId) {
    activeTab = tabId;
    
    // Update active tab buttons visual style
    tabBtns.forEach(btn => {
      const isSelected = btn.getAttribute('data-tab') === tabId;
      btn.style.color = isSelected ? 'var(--primary)' : 'var(--text-secondary)';
      btn.style.borderBottomColor = isSelected ? 'var(--primary)' : 'transparent';
    });

    // Clear contents
    tabContent.innerHTML = '';
    
    // Load and render tab module
    let subElement = null;
    showSpinner('탭 내용을 로딩 중...');
    
    try {
      if (tabId === 'brainstorm') {
        subElement = await renderBrainstorm(projectId);
      } else if (tabId === 'worldmap') {
        subElement = await renderWorldMap(projectId);
      } else if (tabId === 'characters') {
        subElement = await renderCharacters(projectId);
      } else if (tabId === 'episodes') {
        subElement = await renderEpisodes(projectId);
      } else if (tabId === 'settings') {
        subElement = await renderSettings(projectId);
      }
      
      hideSpinner();
      if (subElement) {
        tabContent.appendChild(subElement);
      }
    } catch (err) {
      hideSpinner();
      tabContent.innerHTML = `
        <div style="padding: 40px; text-align: center; color: var(--accent);">
          <h4>⚠️ 탭 콘텐츠 로딩 실패</h4>
          <p>${err.message}</p>
        </div>
      `;
    }
  }

  // Bind tab buttons events
  tabBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      const tabId = btn.getAttribute('data-tab');
      switchTab(tabId);
    });
  });

  // Initial load
  loadProjectHeader();
  switchTab(activeTab);

  return container;
}
