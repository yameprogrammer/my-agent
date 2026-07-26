// Fetch-based HTTP REST API Client

const BASE_URL = '/api';

function authHeaders(extra = {}) {
  const token = localStorage.getItem('access_token');
  const headers = { ...extra };
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }
  return headers;
}

function handleUnauthorized() {
  localStorage.removeItem('access_token');
  localStorage.removeItem('user_info');
  window.location.hash = '#/login';
  throw new Error('인증 세션이 만료되었습니다. 다시 로그인해주세요.');
}

async function parseErrorMessage(response) {
  let errorMsg = `HTTP error! status: ${response.status}`;
  try {
    const errorData = await response.json();
    if (errorData.detail) {
      if (Array.isArray(errorData.detail)) {
        errorMsg = errorData.detail.map(err => {
          const field = err.loc ? err.loc.join('.') : '데이터';
          return `${field} 필드 오류: ${err.msg}`;
        }).join(', ');
      } else {
        errorMsg = typeof errorData.detail === 'string'
          ? errorData.detail
          : JSON.stringify(errorData.detail);
      }
    }
  } catch (e) {
    // No JSON body
  }
  return errorMsg;
}

/**
 * Content-Disposition 에서 파일명 추출 (filename*=UTF-8''... 및 filename= 지원)
 */
export function parseFilenameFromDisposition(disposition, fallback = 'download') {
  if (!disposition) return fallback;
  const utf8Match = /filename\*\s*=\s*UTF-8''([^;]+)/i.exec(disposition);
  if (utf8Match && utf8Match[1]) {
    try {
      return decodeURIComponent(utf8Match[1].trim().replace(/['"]/g, ''));
    } catch (e) {
      return utf8Match[1].trim().replace(/['"]/g, '');
    }
  }
  const plainMatch = /filename\s*=\s*((['"]).*?\2|[^;\n]*)/i.exec(disposition);
  if (plainMatch && plainMatch[1]) {
    return plainMatch[1].replace(/['"]/g, '').trim() || fallback;
  }
  return fallback;
}

export async function request(path, options = {}) {
  const headers = authHeaders({
    'Content-Type': 'application/json',
    ...options.headers
  });
  
  const config = {
    ...options,
    headers
  };
  
  // Convert body to JSON string if it's an object and not FormData/URLSearchParams
  if (config.body && typeof config.body === 'object' && !(config.body instanceof FormData) && !(config.body instanceof URLSearchParams)) {
    config.body = JSON.stringify(config.body);
  }
  
  try {
    const response = await fetch(`${BASE_URL}${path}`, config);
    
    if (response.status === 401) {
      handleUnauthorized();
    }
    
    if (!response.ok) {
      throw new Error(await parseErrorMessage(response));
    }
    
    // Check if empty response (e.g. 204 No Content)
    if (response.status === 204) {
      return null;
    }
    
    return await response.json();
  } catch (error) {
    console.error(`API Request failed on ${path}:`, error);
    throw error;
  }
}

/**
 * JWT 포함 바이너리 다운로드 (소설 원고 TXT/EPUB/PDF/DOCX 등).
 * @param {string} path - /api 이후 경로 (예: /projects/1/download?format=txt)
 * @param {{ defaultFilename?: string }} options
 * @returns {Promise<{ filename: string }>}
 */
export async function downloadBlob(path, options = {}) {
  const { defaultFilename = 'download' } = options;
  const response = await fetch(`${BASE_URL}${path}`, {
    method: 'GET',
    headers: authHeaders()
  });

  if (response.status === 401) {
    handleUnauthorized();
  }

  if (!response.ok) {
    throw new Error(await parseErrorMessage(response));
  }

  const blob = await response.blob();
  const disposition = response.headers.get('Content-Disposition') || response.headers.get('content-disposition');
  const filename = parseFilenameFromDisposition(disposition, defaultFilename);

  const url = window.URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  window.URL.revokeObjectURL(url);

  return { filename };
}

/**
 * JSON 응답을 파일로 저장 (프로젝트 마이그레이션 export 등).
 */
export async function downloadJson(path, defaultFilename = 'export.json') {
  const response = await fetch(`${BASE_URL}${path}`, {
    method: 'GET',
    headers: authHeaders({ Accept: 'application/json' }),
  });

  if (response.status === 401) {
    handleUnauthorized();
  }
  if (!response.ok) {
    throw new Error(await parseErrorMessage(response));
  }

  const data = await response.json();
  const blob = new Blob([JSON.stringify(data, null, 2)], {
    type: 'application/json;charset=utf-8',
  });
  const url = window.URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = defaultFilename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  window.URL.revokeObjectURL(url);
  return { filename: defaultFilename, data };
}

/**
 * multipart 파일 업로드 (Content-Type 은 브라우저가 boundary 와 함께 설정).
 */
export async function uploadFile(path, file, fieldName = 'file') {
  const form = new FormData();
  form.append(fieldName, file);

  const response = await fetch(`${BASE_URL}${path}`, {
    method: 'POST',
    headers: authHeaders(),
    body: form,
  });

  if (response.status === 401) {
    handleUnauthorized();
  }
  if (!response.ok) {
    throw new Error(await parseErrorMessage(response));
  }
  if (response.status === 204) {
    return null;
  }
  return await response.json();
}

export const api = {
  get: (path, options) => request(path, { ...options, method: 'GET' }),
  post: (path, body, options) => request(path, { ...options, method: 'POST', body }),
  put: (path, body, options) => request(path, { ...options, method: 'PUT', body }),
  patch: (path, body, options) => request(path, { ...options, method: 'PATCH', body }),
  delete: (path, options) => request(path, { ...options, method: 'DELETE' }),
  download: downloadBlob,
  downloadJson,
  uploadFile,
};
