const launcher = document.getElementById('chatLauncher');
const chatWrapper = document.getElementById('chatWrapper');
const closeBtn = document.getElementById('closeChat');
const expandBtn = document.getElementById('expandChat');
const messages = document.getElementById('messages');
const sendBtn = document.getElementById('sendBtn');
const input = document.getElementById('messageInput');
const assistantOverlay = document.getElementById('assistantOverlay');
const assistantBack = document.getElementById('assistantBack');
const assistantMessages = document.getElementById('assistantMessages');
const assistantSend = document.getElementById('assistantSend');
const assistantInput = document.getElementById('assistantInput');
const sessionBadge = document.getElementById('sessionBadge');

let sessionId = null;
let currentMode = 'chat';
let loading = false;

function now() {
  return new Date().toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' });
}

function escapeHtml(value) {
  return (value || '').replaceAll('&', '&amp;').replaceAll('<', '&lt;').replaceAll('>', '&gt;');
}

function bubble(container, text, role = 'assistant') {
  const el = document.createElement('div');
  el.className = `bubble ${role}`;
  el.innerHTML = `${escapeHtml(text).replaceAll('\n', '<br>')}<span class="meta">${role} • ${now()}</span>`;
  container.appendChild(el);
  container.scrollTop = container.scrollHeight;
}

function loadingBubble(container) {
  const el = document.createElement('div');
  el.className = 'bubble assistant';
  el.innerHTML = `Идет обработка запроса...<span class="meta">${now()}</span>`;
  container.appendChild(el);
  container.scrollTop = container.scrollHeight;
  return el;
}

function syncSmallToLarge() {
  assistantMessages.innerHTML = messages.innerHTML;
  assistantInput.value = input.value;
}

function syncLargeToSmall() {
  messages.innerHTML = assistantMessages.innerHTML;
  input.value = assistantInput.value;
}

function setMode(mode) {
  currentMode = mode;
  document.querySelectorAll('.mode-btn').forEach((btn) => {
    btn.classList.toggle('active', btn.dataset.mode === mode);
  });
}

async function ensureSession() {
  if (sessionId) return sessionId;
  const session = await apiService.createSession();
  sessionId = session.session_id;
  if (sessionBadge) {
    sessionBadge.textContent = `session ${sessionId.slice(0, 8)}`;
  }
  return sessionId;
}

async function sendMessage(sourceInput, targetContainer) {
  if (loading) return;
  const message = sourceInput.value.trim();
  if (!message) return;

  await ensureSession();
  bubble(targetContainer, message, 'user');
  sourceInput.value = '';
  loading = true;
  const loader = loadingBubble(targetContainer);

  try {
    const response = await apiService.respond(sessionId, message, currentMode);
    loader.remove();
    bubble(targetContainer, response.answer, 'assistant');
    if (targetContainer === assistantMessages) {
      syncLargeToSmall();
    } else {
      syncSmallToLarge();
    }
  } catch (error) {
    loader.remove();
    bubble(targetContainer, `Ошибка: ${error.message}`, 'assistant');
  } finally {
    loading = false;
  }
}

launcher?.addEventListener('click', () => chatWrapper.classList.add('open'));
closeBtn?.addEventListener('click', () => chatWrapper.classList.remove('open'));
expandBtn?.addEventListener('click', () => {
  syncSmallToLarge();
  assistantOverlay.classList.add('open');
  document.body.classList.add('overlay-open');
});
assistantBack?.addEventListener('click', () => {
  syncLargeToSmall();
  assistantOverlay.classList.remove('open');
  document.body.classList.remove('overlay-open');
});
sendBtn?.addEventListener('click', () => sendMessage(input, messages));
assistantSend?.addEventListener('click', () => sendMessage(assistantInput, assistantMessages));
input?.addEventListener('keydown', (event) => {
  if (event.key === 'Enter') sendMessage(input, messages);
});
assistantInput?.addEventListener('keydown', (event) => {
  if (event.key === 'Enter') sendMessage(assistantInput, assistantMessages);
});
document.querySelectorAll('.mode-bar').forEach((bar) => {
  bar.addEventListener('click', (event) => {
    const btn = event.target.closest('.mode-btn');
    if (!btn) return;
    setMode(btn.dataset.mode);
  });
});
window.addEventListener('beforeunload', () => {
  if (sessionId) apiService.closeSession(sessionId);
});

bubble(messages, 'Ассистент работает только по разделу "Извлеченные уроки". Выберите режим и задайте запрос.', 'assistant');
ensureSession().catch(() => bubble(messages, 'Не удалось инициализировать диалоговую сессию.', 'assistant'));
