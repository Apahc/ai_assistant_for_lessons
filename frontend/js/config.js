const API_CONFIG = {
  baseUrl: window.location.hostname === 'localhost'
    ? 'http://localhost:8000'
    : `${window.location.protocol}//${window.location.hostname}:8000`,
  endpoints: {
    createSession: '/api/v1/sessions',
    closeSession: (sessionId) => `/api/v1/sessions/${sessionId}/close`,
    message: '/message',
    health: '/api/v1/health',
  },
};
