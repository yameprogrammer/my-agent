/**
 * IMP-02: 프로젝트 JSON 마이그레이션 (export / import) UX 헬퍼
 * - 기본: API 키 미포함 (include_secrets=false)
 * - 시크릿 포함은 옵트인 + 경고
 */
import { api, downloadJson, uploadFile } from '../api/client.js';
import { showToast } from '../components/toast.js';
import { showSpinner, hideSpinner } from '../components/loading.js';
import { createModal } from '../components/modal.js';

function safeFilename(title) {
  const base = (title || 'project')
    .replace(/[\\/:*?"<>|]/g, '_')
    .replace(/\s+/g, '_')
    .slice(0, 80);
  const d = new Date().toISOString().slice(0, 10);
  return `${base}_export_${d}.json`;
}

/**
 * 프로젝트 export 모달 → JSON 파일 다운로드
 */
export function openProjectExportModal(projectId, projectTitle = 'project') {
  const body = document.createElement('div');
  body.innerHTML = `
    <p style="font-size:0.9rem;color:var(--text-secondary);line-height:1.5;margin:0 0 14px;">
      세계관·캐릭터·회차·본문 버전을 JSON으로 내보냅니다.
      다른 계정/서버로 옮기거나 백업할 때 사용하세요.
    </p>
    <label style="display:flex;align-items:flex-start;gap:10px;font-size:0.85rem;color:var(--text-primary);cursor:pointer;padding:12px;background:var(--bg-app);border-radius:var(--radius-sm);border:1px solid var(--border-color);">
      <input type="checkbox" id="mig-include-secrets" style="margin-top:3px;">
      <span>
        <strong>API 키 포함 (비권장)</strong><br>
        <span style="font-size:0.78rem;color:var(--accent);line-height:1.4;">
          체크 시 프로젝트에 저장된 LLM API 키가 평문으로 JSON에 들어갑니다.
          공개 저장소·메신저에 올리지 마세요. 기본값은 키 제외입니다.
        </span>
      </span>
    </label>
  `;

  createModal({
    title: '📦 프로젝트 백업 (Export)',
    content: body,
    confirmText: 'JSON 다운로드',
    cancelText: '취소',
    onConfirm: async () => {
      const includeSecrets = !!body.querySelector('#mig-include-secrets')?.checked;
      const q = includeSecrets ? '?include_secrets=true' : '';
      const fname = safeFilename(projectTitle);
      showSpinner('프로젝트 데이터를 내보내는 중...');
      try {
        await downloadJson(`/migration/export/${projectId}${q}`, fname);
        hideSpinner();
        showToast(
          includeSecrets
            ? `다운로드 완료: ${fname} (API 키 포함 — 취급 주의)`
            : `다운로드 완료: ${fname}`,
          includeSecrets ? 'info' : 'success'
        );
      } catch (err) {
        hideSpinner();
        showToast(err.message || '내보내기 실패', 'error');
        return false;
      }
    },
  });
}

/**
 * 프로젝트 import — 파일 선택 후 업로드
 * @param {{ onSuccess?: (result: object) => void }} options
 */
export function openProjectImportPicker(options = {}) {
  const input = document.createElement('input');
  input.type = 'file';
  input.accept = 'application/json,.json';
  input.style.display = 'none';
  document.body.appendChild(input);

  input.addEventListener('change', async () => {
    const file = input.files?.[0];
    input.remove();
    if (!file) return;

    createModal({
      title: '📥 프로젝트 가져오기 (Import)',
      content: `
        <p style="font-size:0.9rem;color:var(--text-secondary);line-height:1.55;margin:0;">
          파일 <strong>${escapeHtml(file.name)}</strong> 을(를) 현재 계정에
          <strong>새 프로젝트</strong>로 복원합니다.<br><br>
          · 기존 프로젝트는 덮어쓰지 않습니다.<br>
          · export 시 키가 없었다면 LLM 키는 복원되지 않습니다 (설정에서 다시 입력).<br>
          · 손상된 JSON 이면 실패할 수 있습니다.
        </p>
      `,
      confirmText: '가져오기 실행',
      cancelText: '취소',
      onConfirm: async () => {
        showSpinner('프로젝트 복원 중...');
        try {
          const result = await uploadFile('/migration/import', file, 'file');
          hideSpinner();
          showToast(
            `가져오기 완료: 「${result.title || '새 프로젝트'}」(id ${result.new_project_id})`,
            'success'
          );
          if (typeof options.onSuccess === 'function') {
            options.onSuccess(result);
          } else if (result.new_project_id) {
            window.location.hash = `#/projects/${result.new_project_id}`;
          }
        } catch (err) {
          hideSpinner();
          showToast(err.message || '가져오기 실패', 'error');
          return false;
        }
      },
    });
  });

  input.click();
}

function escapeHtml(str) {
  return String(str ?? '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}
