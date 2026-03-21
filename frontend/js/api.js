class APIService {
  constructor(baseUrl) {
    this.baseUrl = baseUrl;
  }

  async createSession() {
    const response = await fetch(`${this.baseUrl}${API_CONFIG.endpoints.createSession}`, { method: 'POST' });
    if (!response.ok) throw new Error('Не удалось создать сессию');
    return response.json();
  }

  async respond(sessionId, message, mode) {
    const response = await fetch(`${this.baseUrl}${API_CONFIG.endpoints.respond}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ session_id: sessionId, message, mode }),
    });
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Ошибка ответа ассистента');
    }
    return response.json();
  }

  async closeSession(sessionId) {
    if (!sessionId) return;
    await fetch(`${this.baseUrl}${API_CONFIG.endpoints.closeSession(sessionId)}`, {
      method: 'POST',
      keepalive: true,
    });
  }
}

const apiService = new APIService(API_CONFIG.baseUrl);
