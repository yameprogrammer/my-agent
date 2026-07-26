// Project Detail Page Container with tab navigation
import { api, downloadBlob } from '../api/client.js';
import { showSpinner, hideSpinner } from '../components/loading.js';
import { showToast } from '../components/toast.js';
import { createModal } from '../components/modal.js';
import { openProjectExportModal } from '../utils/migration.js';
import { renderBrainstorm } from './brainstorm.js';
import { renderWorldMap } from './worldmap.js';
import { renderReferences } from './references.js';
import { renderCharacters } from './characters.js';
import { renderEpisodes } from './episodes.js';
import { renderSettings } from './settings.js';

const DOWNLOAD_FORMATS = [
  { id: 'txt', label: 'TXT', desc: '투고용 평문', icon: '📄' },
  { id: 'epub', label: 'EPUB', desc: '전자책', icon: '📘' },
  { id: 'pdf', label: 'PDF', desc: '인쇄·공유', icon: '📕' },
  { id: 'docx', label: 'DOCX', desc: '워드 문서', icon: '📝' },
];

const EXPORT_PRESETS = [
  { id: 'default', label: '기본' },
  { id: 'kakao', label: '카카오페이지 관례' },
  { id: 'series', label: '연재 시리즈' },
];

/**
 * 소설 원고 포맷 선택 모달 후 JWT blob 다운로드 (IMP-01)
 */
export function openNovelDownloadModal(projectId, projectTitle = '소설') {
  const body = document.createElement('div');
  body.innerHTML = `
    <p style="color: var(--text-secondary); font-size: 0.9rem; margin: 0 0 16px; line-height: 1.5;">
      승인된 회차 본문(없으면 최신 버전)을 선택한 형식으로 컴파일해 다운로드합니다.
      회차가 없으면 서버에서 오류가 반환됩니다.
    </p>
    <div class="form-group" style="margin-bottom: 12px;">
      <label class="form-label" style="font-size: 0.85rem;">투고 포맷 프리셋 (IDEA-14)</label>
      <select class="form-control" id="export-preset-select">
        ${EXPORT_PRESETS.map(p => `<option value="${p.id}">${p.label}</option>`).join('')}
      </select>
    </div>
    <div class="form-group" style="margin-bottom: 12px;">
      <label class="form-label" style="font-size: 0.85rem;">회차 번호 필터 (선택, 콤마 구분 — IDEA-15)</label>
      <input class="form-control" id="export-episode-numbers" placeholder="예: 1,2,3 (비우면 전체)" />
    </div>
    <div id="download-format-grid" style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px;">
      ${DOWNLOAD_FORMATS.map(f => `
        <button type="button" class="btn btn-secondary download-format-btn" data-format="${f.id}"
          style="display: flex; flex-direction: column; align-items: flex-start; gap: 4px; padding: 14px 16px; text-align: left; height: auto; min-height: 72px;">
          <span style="font-size: 1.1rem;">${f.icon} <strong>${f.label}</strong></span>
          <span style="font-size: 0.78rem; color: var(--text-muted); font-weight: 400;">${f.desc}</span>
        </button>
      `).join('')}
    </div>
  `;

  const modal = createModal({
    title: '📥 원고 내보내기',
    content: body,
    showFooter: false,
  });

  body.querySelectorAll('.download-format-btn').forEach(btn => {
    btn.addEventListener('click', async () => {
      const format = btn.getAttribute('data-format');
      const preset = body.querySelector('#export-preset-select')?.value || 'default';
      const nums = (body.querySelector('#export-episode-numbers')?.value || '').trim();
      showSpinner(`${format.toUpperCase()} 원고를 생성하는 중...`);
      try {
        const safeTitle = (projectTitle || 'novel').replace(/[\\/:*?"<>|]/g, '_');
        let q = `format=${encodeURIComponent(format)}&export_preset=${encodeURIComponent(preset)}`;
        if (nums) q += `&episode_numbers=${encodeURIComponent(nums)}`;
        const { filename } = await downloadBlob(
          `/projects/${projectId}/download?${q}`,
          { defaultFilename: `${safeTitle}.${format}` }
        );
        hideSpinner();
        showToast(`다운로드 완료: ${filename}`, 'success');
        modal.close();
      } catch (err) {
        hideSpinner();
        showToast(err.message || '다운로드에 실패했습니다.', 'error');
      }
    });
  });
}

export async function renderProject(params) {
  const projectId = params.id;
  const container = document.createElement('div');
  container.className = 'animate-fade-in';
  container.style.width = '100%';
  
  let activeTab = 'episodes'; // default tab
  let projectTitle = '';

  container.innerHTML = `
    <!-- Project Info Header -->
    <div class="glass-card" style="padding: 24px; margin-bottom: 24px; display: flex; justify-content: space-between; align-items: flex-start; gap: 16px; flex-wrap: wrap;" class="flex-row-responsive">
      <div style="flex: 1; min-width: 200px;">
        <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 6px;">
          <a href="#/" style="font-size: 0.9rem; font-weight: 600; display: flex; align-items: center; gap: 4px;">
            <span>⬅️</span> 대시보드로 돌아가기
          </a>
        </div>
        <h2 id="project-header-title" style="font-family: var(--font-heading); font-size: 1.8rem; color: var(--text-primary); margin: 0;"></h2>
        <p id="project-header-synopsis" style="color: var(--text-secondary); font-size: 0.9rem; margin-top: 6px; max-width: 800px; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; line-height: 1.4;"></p>
      </div>
      <div style="display: flex; flex-direction: column; align-items: flex-end; gap: 12px;">
        <div style="text-align: right;" id="project-header-model-info">
          <!-- Model info badges -->
        </div>
        <div style="display: flex; gap: 8px; flex-wrap: wrap; justify-content: flex-end;">
          <button type="button" class="btn btn-secondary" id="btn-backup-project" style="white-space: nowrap;" title="JSON 마이그레이션 백업">
            📦 프로젝트 백업
          </button>
          <button type="button" class="btn btn-primary" id="btn-export-novel" style="white-space: nowrap;">
            📥 원고 내보내기
          </button>
        </div>
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
        <button class="project-tab-btn" data-tab="references" style="padding: 16px 20px; font-weight: 600; font-size: 0.95rem; border: none; background: none; color: var(--text-secondary); cursor: pointer; border-bottom: 3px solid transparent; transition: all var(--transition-fast);">
          🔍 고증 참고 자료
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
      projectTitle = project.title || '';
      container.querySelector('#project-header-title').textContent = project.title;
      container.querySelector('#project-header-synopsis').textContent = project.synopsis || '등록된 소설 시놉시스가 없습니다.';
      
      const modelInfo = container.querySelector('#project-header-model-info');
      let provBadge = '';
      if (project.llm_provider === 'openai') provBadge = '<span class="badge badge-primary">OpenAI</span>';
      else if (project.llm_provider === 'google') provBadge = '<span class="badge badge-success">Gemini</span>';
      else if (project.llm_provider === 'nvidia') provBadge = '<span class="badge badge-secondary" style="background-color: #e8f5e9; color: #1b5e20;">NVIDIA NIM</span>';
      else if (project.llm_provider === 'anthropic') provBadge = '<span class="badge badge-secondary" style="background-color: #ffeedd; color: #cc6600;">Anthropic</span>';
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

  container.querySelector('#btn-export-novel').addEventListener('click', () => {
    openNovelDownloadModal(projectId, projectTitle);
  });

  container.querySelector('#btn-backup-project').addEventListener('click', () => {
    openProjectExportModal(projectId, projectTitle);
  });

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
      } else if (tabId === 'references') {
        subElement = await renderReferences(projectId);
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
