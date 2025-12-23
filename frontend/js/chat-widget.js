const chatWrapper = document.getElementById('chatWrapper');
const launcher = document.getElementById('chatLauncher');
const closeBtn = document.getElementById('closeChat');
const expandBtn = document.getElementById('expandChat');
const messages = document.getElementById('messages');
const sendBtn = document.getElementById('sendBtn');
const input = document.getElementById('messageInput');
const chipsBar = document.getElementById('chipsBar');

const assistantOverlay = document.getElementById('assistantOverlay');
const assistantBack = document.getElementById('assistantBack');
const assistantMessages = document.getElementById('assistantMessages');
const assistantSend = document.getElementById('assistantSend');
const assistantInput = document.getElementById('assistantInput');
const assistantChips = document.getElementById('assistantChips');
const lessonHistoryContainer = document.getElementById('lessonHistory');

const contextButtons = document.getElementById('contextButtons');
const assistantContextButtons = document.getElementById('assistantContextButtons');

let lessonHistory = [];
let currentChatType = CHAT_TYPES.QUESTION; // Текущий тип чата по умолчанию
let isLoading = false;

function scrollToBottom(container) {
  container.scrollTop = container.scrollHeight;
}

function timeNow() {
  const now = new Date();
  return now.toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' });
}

function renderMessage({ text, sender = 'assistant', time }, container = messages) {
  const bubble = document.createElement('div');
  bubble.className = `bubble ${sender}`;
  bubble.innerHTML = `${text}<span class="meta">${time || timeNow()}</span>`;
  container.appendChild(bubble);
  scrollToBottom(container);
}

function renderLoadingMessage(container = messages) {
  const bubble = document.createElement('div');
  bubble.className = 'bubble assistant loading';
  bubble.innerHTML = `<span class="loading-dots">Думаю</span><span class="meta">${timeNow()}</span>`;
  container.appendChild(bubble);
  scrollToBottom(container);
  return bubble;
}

function removeLoadingMessage(bubble) {
  if (bubble && bubble.parentNode) {
    bubble.parentNode.removeChild(bubble);
  }
}

function renderHistory() {
  if (!lessonHistoryContainer) return;
  lessonHistoryContainer.innerHTML = '';

  lessonHistory.forEach((lesson) => {
    const item = document.createElement('div');
    item.className = 'history-item';
    item.dataset.code = lesson.code;
    item.textContent = lesson.title;
    lessonHistoryContainer.appendChild(item);
  });
}

function addLessonToHistory(code, title) {
  if (!code) return;
  const exists = lessonHistory.some((item) => item.code === code);
  if (exists) return;

  lessonHistory = [...lessonHistory, { code, title }];
  renderHistory();
}

function openLessonPage(code, title = `Урок ${code}`) {
  if (!code) return;

  const pageTitle = title || `Урок ${code}`;
  const lessonWindow = window.open('', '_blank');

  if (lessonWindow) {
    lessonWindow.document.write(`<!DOCTYPE html><html lang="ru"><head><meta charset="UTF-8"><title>${pageTitle}</title></head><body><h1>${pageTitle}</h1><p>Текст: ${pageTitle}</p></body></html>`);
    lessonWindow.document.close();
  }

  addLessonToHistory(code, pageTitle);
}

function renderDate(dateText) {
  const badge = document.createElement('div');
  badge.className = 'date-divider';
  badge.textContent = dateText;
  messages.appendChild(badge);
}

function formatContextChunks(chunks) {
  if (!chunks || chunks.length === 0) return '';
  
  let html = '<div class="context-sources"><strong>Найденные источники:</strong><ol>';
  chunks.forEach((chunk, index) => {
    const metadata = chunk.metadata || {};
    const title = metadata.name || metadata.title || `Урок ${index + 1}`;
    const description = chunk.document ? chunk.document.substring(0, 150) + '...' : 'Нет описания';
    const code = metadata.lesson_id || metadata.id || `L${index + 1}`;
    
    html += `<li><strong>${title}</strong><br />${description}<br /><a href="#" class="lesson-link" data-code="${code}">Урок ${code}</a></li>`;
  });
  html += '</ol></div>';
  return html;
}

function formatLessonParagraphs(text) {
  if (!text) return '';

  const parts = text.split(/(?=---\s*Урок\s+\d+\s*---)/g);
  if (parts.length === 1) {
    return text;
  }

  return parts
    .map((part, index) => {
      const trimmed = part.trim();
      if (!trimmed) return '';

      const normalized = trimmed.replace(/\n/g, '<br>');
      if (index === 0 && !trimmed.startsWith('--- Урок')) {
        return normalized;
      }

      return `<p>${normalized}</p>`;
    })
    .join('');
}

function seedSmallConversation() {
  renderDate(new Date().toLocaleDateString('ru-RU'));
  renderMessage({
    sender: 'assistant',
    time: timeNow(),
    text: `Привет, я Ассистент-помощник для быстрого поиска извлечённых уроков по твоим запросам.<br>Напиши мне на какую тему ты хочешь найти, а я предложу тебе несколько вариантов.`,
  });
}

function syncMessagesToLarge() {
  // Копируем все сообщения из малого чата в большой
  assistantMessages.innerHTML = messages.innerHTML;
  // Копируем текст из поля ввода
  assistantInput.value = input.value;
  // Прокручиваем вниз после копирования
  scrollToBottom(assistantMessages);
}

function syncMessagesToSmall() {
  // Копируем все сообщения из большого чата в малый
  messages.innerHTML = assistantMessages.innerHTML;
  // Копируем текст из поля ввода
  input.value = assistantInput.value;
  // Прокручиваем вниз после копирования
  scrollToBottom(messages);
}

function syncContextButtons() {
  // Синхронизируем активную кнопку типа контекста
  const activeSmall = contextButtons?.querySelector('.context-btn.active');
  const activeLarge = assistantContextButtons?.querySelector('.context-btn.active');
  
  if (activeSmall) {
    const type = activeSmall.dataset.type;
    assistantContextButtons?.querySelectorAll('.context-btn').forEach(btn => {
      btn.classList.toggle('active', btn.dataset.type === type);
    });
  } else if (activeLarge) {
    const type = activeLarge.dataset.type;
    contextButtons?.querySelectorAll('.context-btn').forEach(btn => {
      btn.classList.toggle('active', btn.dataset.type === type);
    });
  }
}

function openChat() {
  chatWrapper.classList.add('open');
}

function closeChat() {
  chatWrapper.classList.remove('open');
}

function showAssistant() {
  syncMessagesToLarge();
  syncContextButtons();
  assistantOverlay.classList.add('open');
  document.body.classList.add('overlay-open');
  closeChat();
}

function hideAssistant() {
  syncMessagesToSmall();
  syncContextButtons();
  assistantOverlay.classList.remove('open');
  document.body.classList.remove('overlay-open');
  openChat();
}

async function handleSendSmall() {
  if (isLoading) return;
  
  const value = input.value.trim();
  if (!value) return;

  // Отображаем сообщение пользователя
  renderMessage({ sender: 'user', text: value });
  input.value = '';
  
  // Показываем индикатор загрузки
  isLoading = true;
  const loadingBubble = renderLoadingMessage();
  
  try {
    // Отправляем запрос к API
    const response = await apiService.chat(value, currentChatType);
    
    // Удаляем индикатор загрузки
    removeLoadingMessage(loadingBubble);
    
    // Отображаем ответ
    let answerText = formatLessonParagraphs(response.answer);
    if (response.context_chunks && response.context_chunks.length > 0) {
      answerText += '<br><br>' + formatContextChunks(response.context_chunks);
    }
    
    renderMessage({
      sender: 'assistant',
      text: answerText,
    });
  } catch (error) {
    removeLoadingMessage(loadingBubble);
    renderMessage({
      sender: 'assistant',
      text: `Извините, произошла ошибка: ${error.message}. Проверьте, что бэкенд запущен.`,
    });
  } finally {
    isLoading = false;
    input.focus();
  }
}

async function handleSendLarge() {
  if (isLoading) return;
  
  const value = assistantInput.value.trim();
  if (!value) return;

  // Отображаем сообщение пользователя
  renderMessage({ sender: 'user', text: value }, assistantMessages);
  assistantInput.value = '';
  
  // Показываем индикатор загрузки
  isLoading = true;
  const loadingBubble = renderLoadingMessage(assistantMessages);
  
  try {
    // Отправляем запрос к API
    const response = await apiService.chat(value, currentChatType);
    
    // Удаляем индикатор загрузки
    removeLoadingMessage(loadingBubble);
    
    // Отображаем ответ
    let answerText = formatLessonParagraphs(response.answer);
    if (response.context_chunks && response.context_chunks.length > 0) {
      answerText += '<br><br>' + formatContextChunks(response.context_chunks);
    }
    
    renderMessage({
      sender: 'assistant',
      text: answerText,
    }, assistantMessages);
  } catch (error) {
    removeLoadingMessage(loadingBubble);
    renderMessage({
      sender: 'assistant',
      text: `Извините, произошла ошибка: ${error.message}. Проверьте, что бэкенд запущен.`,
    }, assistantMessages);
  } finally {
    isLoading = false;
    assistantInput.focus();
  }
}

function handleChipClick(event, targetInput) {
  if (!event.target.classList.contains('chip')) return;
  targetInput.value = event.target.textContent;
  targetInput.focus();
}

function handleContextButtonClick(event) {
  const btn = event.target.closest('.context-btn');
  if (!btn) return;

  // Убираем активный класс со всех кнопок в текущей группе
  const container = btn.parentElement;
  container.querySelectorAll('.context-btn').forEach(b => b.classList.remove('active'));
  
  // Добавляем активный класс к нажатой кнопке
  btn.classList.add('active');
  
  // Обновляем текущий тип чата
  currentChatType = btn.dataset.type;
  
  console.log('Chat type changed to:', currentChatType);
}

// Event listeners
launcher.addEventListener('click', openChat);
closeBtn.addEventListener('click', closeChat);
expandBtn.addEventListener('click', showAssistant);
assistantBack.addEventListener('click', hideAssistant);

sendBtn.addEventListener('click', handleSendSmall);
assistantSend.addEventListener('click', handleSendLarge);

input.addEventListener('keydown', (e) => {
  if (e.key === 'Enter') {
    e.preventDefault();
    handleSendSmall();
  }
});

assistantInput.addEventListener('keydown', (e) => {
  if (e.key === 'Enter') {
    e.preventDefault();
    handleSendLarge();
  }
});

chipsBar.addEventListener('click', (e) => handleChipClick(e, input));
assistantChips.addEventListener('click', (e) => handleChipClick(e, assistantInput));

// Обработчики для кнопок типа контекста
contextButtons?.addEventListener('click', handleContextButtonClick);
assistantContextButtons?.addEventListener('click', handleContextButtonClick);

function handleLessonLink(event) {
  const link = event.target.closest('.lesson-link');
  if (!link) return;
  event.preventDefault();
  const code = link.dataset.code;
  if (!code) return;
  const title = `Урок ${code}`;
  const win = window.open('', '_blank');
  if (win) {
    win.document.write(`<!DOCTYPE html><html lang="ru"><head><meta charset="UTF-8"><title>${title}</title></head><body><h1>${title}</h1><p>Информация об уроке ${code}</p></body></html>`);
    win.document.close();
  }
  addLessonToHistory(code, title);
}

assistantMessages?.addEventListener('click', handleLessonLink);
messages?.addEventListener('click', handleLessonLink);

lessonHistoryContainer?.addEventListener('click', (event) => {
  const item = event.target.closest('.history-item');
  if (!item) return;
  const code = item.dataset.code;
  if (!code) return;
  const title = `Урок ${code}`;
  const win = window.open('', '_blank');
  if (win) {
    win.document.write(`<!DOCTYPE html><html lang="ru"><head><meta charset="UTF-8"><title>${title}</title></head><body><h1>${title}</h1><p>Информация об уроке ${code}</p></body></html>`);
    win.document.close();
  }
});

// Проверка здоровья API при загрузке
async function checkAPIHealth() {
  const health = await apiService.checkHealth();
  if (health) {
    console.log('API Health:', health);
    if (health.status !== 'healthy') {
      console.warn('API is not fully healthy:', health);
    }
  } else {
    console.error('Cannot connect to backend API. Make sure it is running on', API_CONFIG.baseUrl);
  }
}

// Инициализация
seedSmallConversation();
checkAPIHealth();
