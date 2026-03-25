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
let sessionBootstrapped = false;

const STORAGE_SESSION_ID = 'lessonsWidgetSessionId';
const STORAGE_REOPEN_CHAT = 'lessonsWidgetReopenChat';
const STORAGE_RETURNING_FROM_LESSON = 'lessonsWidgetReturningFromLesson';

function lessonsCachePrefix(session) {
  return `lessonsWidgetLessons:${session}:`;
}

function persistAssistantLessons(session, turnIndex, lessons) {
  if (!session || typeof turnIndex !== 'number' || turnIndex < 0) return;
  try {
    sessionStorage.setItem(lessonsCachePrefix(session) + String(turnIndex), JSON.stringify(lessons || []));
  } catch (e) {
    /* quota */
  }
}

function loadAssistantLessons(session, turnIndex) {
  if (!session || typeof turnIndex !== 'number' || turnIndex < 0) return [];
  try {
    const raw = sessionStorage.getItem(lessonsCachePrefix(session) + String(turnIndex));
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed : [];
  } catch (e) {
    return [];
  }
}

function clearAllWidgetStorage() {
  try {
    sessionStorage.removeItem(STORAGE_RETURNING_FROM_LESSON);
    sessionStorage.removeItem(STORAGE_SESSION_ID);
    sessionStorage.removeItem(STORAGE_REOPEN_CHAT);
    for (let i = sessionStorage.length - 1; i >= 0; i -= 1) {
      const k = sessionStorage.key(i);
      if (k && k.startsWith('lessonsWidgetLessons:')) sessionStorage.removeItem(k);
    }
  } catch (e) {
    /* ignore */
  }
}

function persistStateBeforeOpeningLesson() {
  if (!sessionId) return;
  try {
    sessionStorage.setItem(STORAGE_RETURNING_FROM_LESSON, '1');
    sessionStorage.setItem(STORAGE_SESSION_ID, sessionId);
    sessionStorage.setItem(STORAGE_REOPEN_CHAT, '1');
  } catch (e) {
    /* quota / private mode */
  }
}

function now() {
  return new Date().toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' });
}

function roleLabel(role) {
  return role === 'user' ? 'user_id' : 'assistant';
}

function escapeHtml(value) {
  return (value || '').replaceAll('&', '&amp;').replaceAll('<', '&lt;').replaceAll('>', '&gt;');
}

function lessonPageHref(lessonCode) {
  const q = new URLSearchParams();
  q.set('lessonId', lessonCode);
  q.set('backendUrl', API_CONFIG.baseUrl);
  return `lesson.html?${q.toString()}`;
}

function stripMarkdownAsterisks(text) {
  let s = text || '';
  for (let i = 0; i < 20 && s.includes('**'); i += 1) {
    const next = s.replace(/\*\*([^*]+?)\*\*/, '$1');
    if (next === s) break;
    s = next;
  }
  s = s.replace(/(?<!\*)\*([^*]+)\*(?!\*)/g, '$1');
  return s.replaceAll('*', '');
}

function lessonKeyFromSnippet(L) {
  if (L.lesson_id != null && String(L.lesson_id).trim() !== '') {
    return String(L.lesson_id).trim();
  }
  const id = L.id != null ? String(L.id) : '';
  const base = id.split('::')[0];
  return base.trim() || '';
}

function buildKnownLessonCodes(lessons) {
  const codes = new Set();
  if (!Array.isArray(lessons)) return codes;
  for (const L of lessons) {
    const lid = lessonKeyFromSnippet(L);
    if (lid) codes.add(lid);
  }
  return codes;
}

function formatAssistantBodyHtml(text, lessons) {
  const cleaned = stripMarkdownAsterisks(text);
  const known = buildKnownLessonCodes(lessons);
  const re = /\[([A-Za-zА-Яа-яЁё0-9][A-Za-zА-Яа-яЁё0-9._-]*)\]/g;
  let result = '';
  let last = 0;
  let m = re.exec(cleaned);
  while (m !== null) {
    result += escapeHtml(cleaned.slice(last, m.index));
    const id = m[1];
    if (known.has(id)) {
      const href = lessonPageHref(id);
      result += `[<a class="lesson-inline-link" href="${href}">${escapeHtml(id)}</a>]`;
    } else {
      result += escapeHtml(m[0]);
    }
    last = re.lastIndex;
    m = re.exec(cleaned);
  }
  result += escapeHtml(cleaned.slice(last));
  return result.replaceAll('\n', '<br>');
}

function assistantBubbleHtml(text, lessons, mode) {
  const body = formatAssistantBodyHtml(text, lessons);
  return `${body}<span class="meta">${roleLabel('assistant')} • ${now()} • ${mode}</span>`;
}

function bubble(container, text, role = 'assistant', mode = currentMode) {
  const el = document.createElement('div');
  el.className = `bubble ${role}`;
  el.innerHTML = `${escapeHtml(text).replaceAll('\n', '<br>')}<span class="meta">${roleLabel(role)} • ${now()} • ${mode}</span>`;
  container.appendChild(el);
  container.scrollTop = container.scrollHeight;
}

function assistantBubble(container, text, lessons, mode = currentMode) {
  const el = document.createElement('div');
  el.className = 'bubble assistant assistant-turn';
  el.innerHTML = assistantBubbleHtml(text, lessons, mode);
  container.appendChild(el);
  container.scrollTop = container.scrollHeight;
}

function loadingBubble(container, mode = currentMode) {
  const el = document.createElement('div');
  el.className = 'bubble assistant';
  el.innerHTML = `Идет обработка запроса...<span class="meta">assistant • ${now()} • ${mode}</span>`;
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
  sessionBootstrapped = true;
  if (sessionBadge) {
    sessionBadge.textContent = `session ${sessionId.slice(0, 8)}`;
  }
  return sessionId;
}

async function tryRestoreSessionById(saved) {
  if (!saved) return false;
  try {
    const data = await apiService.getSession(saved);
    if (data.status !== 'active') return false;
    sessionId = data.session_id;
    sessionBootstrapped = true;
    if (sessionBadge) {
      sessionBadge.textContent = `session ${sessionId.slice(0, 8)}`;
    }
    messages.innerHTML = '';
    assistantMessages.innerHTML = '';
    const msgs = data.messages || [];
    let lastMode = currentMode;
    let assistantTurn = 0;
    for (let i = 0; i < msgs.length; i += 1) {
      const m = msgs[i];
      const mode = m.mode || 'chat';
      lastMode = mode;
      if (m.role === 'user') {
        bubble(messages, m.content, 'user', mode);
      } else {
        const cachedLessons = loadAssistantLessons(sessionId, assistantTurn);
        assistantBubble(messages, m.content, cachedLessons, mode);
        assistantTurn += 1;
      }
    }
    setMode(lastMode);
    if (msgs.length === 0) {
      seedConversation(messages);
    }
    syncSmallToLarge();
    try {
      if (sessionStorage.getItem(STORAGE_REOPEN_CHAT) === '1') {
        chatWrapper?.classList.add('open');
        sessionStorage.removeItem(STORAGE_REOPEN_CHAT);
      }
    } catch (e) {
      /* ignore */
    }
    return true;
  } catch (e) {
    return false;
  }
}

function seedConversation(container = messages) {
  if (container.children.length > 0) return;
  const el = document.createElement('div');
  el.className = 'bubble assistant chat-welcome-seed';
  el.innerHTML = `${escapeHtml('Ассистент работает только по разделу "Извлеченные уроки". Выберите режим и задайте запрос.').replaceAll('\n', '<br>')}<span class="meta">${roleLabel('assistant')} • ${now()} • ${currentMode}</span>`;
  container.appendChild(el);
  container.scrollTop = container.scrollHeight;
}

async function sendMessage(sourceInput, targetContainer) {
  if (loading) return;
  const message = sourceInput.value.trim();
  if (!message) return;

  document.querySelectorAll('.chat-welcome-seed').forEach((el) => el.remove());

  await ensureSession();
  const activeMode = currentMode;
  bubble(targetContainer, message, 'user', activeMode);
  sourceInput.value = '';
  loading = true;
  const loader = loadingBubble(targetContainer, activeMode);

  try {
    const response = await apiService.respond(sessionId, message, activeMode);
    loader.remove();
    const answerText = response.text || response.answer || '';
    const lessons = response.lessons || [];
    assistantBubble(targetContainer, answerText, lessons, activeMode);
    if (targetContainer === assistantMessages) {
      syncLargeToSmall();
    } else {
      syncSmallToLarge();
    }
    const turnIndex = messages.querySelectorAll('.assistant-turn').length - 1;
    persistAssistantLessons(sessionId, turnIndex, lessons);
  } catch (error) {
    loader.remove();
    bubble(targetContainer, `Ошибка: ${error.message}`, 'assistant', activeMode);
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
messages?.addEventListener('click', (event) => {
  if (event.target.closest('a.lesson-inline-link')) persistStateBeforeOpeningLesson();
});
assistantMessages?.addEventListener('click', (event) => {
  if (event.target.closest('a.lesson-inline-link')) persistStateBeforeOpeningLesson();
});

async function bootstrapWidget() {
  let returningFromLesson = false;
  try {
    returningFromLesson = sessionStorage.getItem(STORAGE_RETURNING_FROM_LESSON) === '1';
  } catch (e) {
    /* ignore */
  }

  if (returningFromLesson) {
    try {
      sessionStorage.removeItem(STORAGE_RETURNING_FROM_LESSON);
    } catch (e) {
      /* ignore */
    }
    let savedSid = null;
    try {
      savedSid = sessionStorage.getItem(STORAGE_SESSION_ID);
    } catch (e) {
      /* ignore */
    }
    if (savedSid && (await tryRestoreSessionById(savedSid))) {
      try {
        sessionStorage.removeItem(STORAGE_SESSION_ID);
      } catch (e) {
        /* ignore */
      }
      return;
    }
  }

  clearAllWidgetStorage();
  sessionId = null;
  sessionBootstrapped = false;

  seedConversation(messages);
  try {
    await ensureSession();
  } catch (e) {
    if (!sessionBootstrapped) {
      bubble(messages, 'Не удалось инициализировать диалоговую сессию.', 'assistant');
    }
  }
}

bootstrapWidget();
