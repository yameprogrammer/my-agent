// Authentication utility for managing JWT tokens and user session state
import { api } from '../api/client.js';
import { renderSidebar } from '../components/sidebar.js';

export function getToken() {
  return localStorage.getItem('access_token');
}

export function getCurrentUser() {
  const userJson = localStorage.getItem('user_info');
  if (!userJson) return null;
  try {
    return JSON.parse(userJson);
  } catch (e) {
    return null;
  }
}

export function isAuthenticated() {
  const token = getToken();
  if (!token) return false;
  
  // Quick JWT expiry check
  try {
    const payload = JSON.parse(atob(token.split('.')[1]));
    const exp = payload.exp * 1000;
    return Date.now() < exp;
  } catch (e) {
    return false;
  }
}

export async function login(username, password) {
  // OAuth2PasswordRequestForm expects URLSearchParams body
  const body = new URLSearchParams();
  body.append('username', username);
  body.append('password', password);
  
  try {
    const data = await api.post('/auth/login', body, {
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded'
      }
    });
    
    if (data && data.access_token) {
      localStorage.setItem('access_token', data.access_token);
      
      // Fetch user profile info
      const user = await api.get('/users/me');
      localStorage.setItem('user_info', JSON.stringify(user));
      
      // Update sidebar
      renderSidebar();
      return user;
    } else {
      throw new Error('토큰 발급에 실패했습니다.');
    }
  } catch (error) {
    console.error('Login failed:', error);
    throw error;
  }
}

export async function register(username, password, email) {
  return await api.post('/auth/register', { username, password, email });
}

export function logout() {
  localStorage.removeItem('access_token');
  localStorage.removeItem('user_info');
  
  // Clear sidebar
  const sidebar = document.getElementById('app-sidebar');
  if (sidebar) sidebar.remove();
  const mobileHeader = document.getElementById('app-mobile-header');
  if (mobileHeader) mobileHeader.remove();
  
  window.location.hash = '#/login';
}
