// Fetch-based HTTP REST API Client

const BASE_URL = '/api';

export async function request(path, options = {}) {
  const token = localStorage.getItem('access_token');
  
  const headers = {
    'Content-Type': 'application/json',
    ...options.headers
  };
  
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }
  
  const config = {
    ...options,
    headers
  };
  
  // Convert body to JSON string if it's an object and not FormData
  if (config.body && typeof config.body === 'object' && !(config.body instanceof FormData)) {
    config.body = JSON.stringify(config.body);
  }
  
  try {
    const response = await fetch(`${BASE_URL}${path}`, config);
    
    if (response.status === 401) {
      // Token expired or invalid, handle logout
      localStorage.removeItem('access_token');
      localStorage.removeItem('user_info');
      window.location.hash = '#/login';
      throw new Error('인증 세션이 만료되었습니다. 다시 로그인해주세요.');
    }
    
    if (!response.ok) {
      let errorMsg = `HTTP error! status: ${response.status}`;
      try {
        const errorData = await response.json();
        errorMsg = errorData.detail || errorMsg;
      } catch (e) {
        // No JSON response or body
      }
      throw new Error(errorMsg);
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

export const api = {
  get: (path, options) => request(path, { ...options, method: 'GET' }),
  post: (path, body, options) => request(path, { ...options, method: 'POST', body }),
  put: (path, body, options) => request(path, { ...options, method: 'PUT', body }),
  patch: (path, body, options) => request(path, { ...options, method: 'PATCH', body }),
  delete: (path, options) => request(path, { ...options, method: 'DELETE' })
};
