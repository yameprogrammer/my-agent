/**
 * H6: 서버 diff 행을 HTML 로 렌더링
 * rows: [{ op, left, right }]
 */
export function renderDiffRowsHtml(rows) {
  if (!rows || !rows.length) {
    return '<p style="color:var(--text-muted);font-size:0.85rem;">변경 사항이 없습니다 (동일 본문).</p>';
  }
  const rowHtml = rows.map(r => {
    const op = r.op || 'equal';
    let bg = 'transparent';
    if (op === 'delete') bg = 'rgba(239,68,68,0.12)';
    else if (op === 'insert') bg = 'rgba(34,197,94,0.12)';
    else if (op === 'replace') bg = 'rgba(234,179,8,0.14)';
    const left = r.left == null ? '<span style="color:var(--text-muted);">∅</span>' : escapeHtml(r.left);
    const right = r.right == null ? '<span style="color:var(--text-muted);">∅</span>' : escapeHtml(r.right);
    const tag =
      op === 'equal' ? '' :
      op === 'delete' ? '<span style="color:#ef4444;font-size:0.7rem;">−</span>' :
      op === 'insert' ? '<span style="color:#22c55e;font-size:0.7rem;">+</span>' :
      '<span style="color:#ca8a04;font-size:0.7rem;">~</span>';
    return `
      <div style="display:grid;grid-template-columns:18px 1fr 1fr;gap:6px;padding:4px 6px;background:${bg};border-bottom:1px solid var(--border-color);font-family:var(--font-mono);font-size:0.75rem;line-height:1.45;">
        <div>${tag}</div>
        <div style="white-space:pre-wrap;word-break:break-word;color:var(--text-secondary);">${left}</div>
        <div style="white-space:pre-wrap;word-break:break-word;color:var(--text-primary);">${right}</div>
      </div>`;
  }).join('');

  return `
    <div style="border:1px solid var(--border-color);border-radius:var(--radius-sm);overflow:hidden;">
      <div style="display:grid;grid-template-columns:18px 1fr 1fr;gap:6px;padding:8px 6px;background:var(--bg-app);font-size:0.75rem;font-weight:600;color:var(--text-muted);">
        <div></div><div>이전 (left)</div><div>이후 (right)</div>
      </div>
      <div style="max-height:50vh;overflow-y:auto;">${rowHtml}</div>
    </div>`;
}

function escapeHtml(str) {
  return String(str ?? '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

/**
 * textarea 선택 구간 추출
 */
export function getTextareaSelection(ta) {
  if (!ta) return null;
  const start = ta.selectionStart;
  const end = ta.selectionEnd;
  if (start == null || end == null || start === end) return null;
  return {
    start,
    end,
    text: ta.value.slice(start, end),
  };
}
