// API Service для взаимодействия с бэкендом

class APIService {
  constructor(baseUrl) {
    this.baseUrl = baseUrl;
  }

  async chat(question, chatType = CHAT_TYPES.QUESTION, topK = 5) {
    try {
      const response = await fetch(`${this.baseUrl}${API_CONFIG.endpoints.chat}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          question: question,
          chat_type: chatType,
          top_k: topK,
          use_query_refinement: true
        })
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Ошибка при обращении к API');
      }

      return await response.json();
    } catch (error) {
      console.error('API Error:', error);
      throw error;
    }
  }

  async search(query, topK = 5) {
    try {
      const response = await fetch(`${this.baseUrl}${API_CONFIG.endpoints.search}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          query: query,
          top_k: topK
        })
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Ошибка при поиске');
      }

      return await response.json();
    } catch (error) {
      console.error('Search Error:', error);
      throw error;
    }
  }

  async checkHealth() {
    try {
      const response = await fetch(`${this.baseUrl}${API_CONFIG.endpoints.health}`);
      if (!response.ok) {
        throw new Error('Health check failed');
      }
      return await response.json();
    } catch (error) {
      console.error('Health Check Error:', error);
      return null;
    }
  }
}

// Создаем экземпляр сервиса
const apiService = new APIService(API_CONFIG.baseUrl);
