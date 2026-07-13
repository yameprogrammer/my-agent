// Global client-side state management

const STATE_KEY = 'novel_agent_app_state';

// Default initial state
const defaultState = {
  theme: 'light',
  currentProject: null,
  currentEpisode: null
};

let appState = { ...defaultState };

// Load state from localStorage on init
function init() {
  try {
    const saved = localStorage.getItem(STATE_KEY);
    if (saved) {
      appState = { ...defaultState, ...JSON.parse(saved) };
    }
  } catch (e) {
    console.error('Failed to load state from localStorage:', e);
  }
  
  // Apply initial theme
  applyTheme(appState.theme);
}

function save() {
  try {
    localStorage.setItem(STATE_KEY, JSON.stringify(appState));
  } catch (e) {
    console.error('Failed to save state to localStorage:', e);
  }
}

function applyTheme(theme) {
  if (theme === 'dark') {
    document.documentElement.setAttribute('data-theme', 'dark');
  } else {
    document.documentElement.removeAttribute('data-theme');
  }
}

export function getTheme() {
  return appState.theme;
}

export function setTheme(theme) {
  appState.theme = theme;
  applyTheme(theme);
  save();
  
  // Dispatch custom event for reactive UI updates
  window.dispatchEvent(new CustomEvent('theme-changed', { detail: { theme } }));
}

export function getState() {
  return appState;
}

export function updateState(updates) {
  appState = { ...appState, ...updates };
  save();
  window.dispatchEvent(new CustomEvent('state-updated', { detail: appState }));
}

// Run initialization
init();
