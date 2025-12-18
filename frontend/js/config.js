// API Configuration
const API_CONFIG = {
  baseUrl: 'http://localhost:8000',
  endpoints: {
    chat: '/api/v1/chat',
    search: '/api/v1/search',
    health: '/api/v1/health'
  }
};

// Chat types
const CHAT_TYPES = {
  QUESTION: 'question',
  LETTER: 'letter',
  DOCUMENT: 'document'
};
