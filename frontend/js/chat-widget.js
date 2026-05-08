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

let sessionId = null;
let currentMode = 'chat';
let loading = false;
let sessionBootstrapped = false;

const STORAGE_SESSION_ID = 'lessonsWidgetSessionId';
const STORAGE_UI_LAYOUT = 'lessonsWidgetUiLayout';
const STORAGE_RETURNING_FROM_LESSON = 'lessonsWidgetReturningFromLesson';
const TRANSCRIPT_PREFIX = 'lessonsWidgetTranscript:';

function transcriptKey(session) {
  return TRANSCRIPT_PREFIX + session;
}

function loadTranscriptSnapshot(sid) {
  if (!sid) return [];
  try {
    const raw = sessionStorage.getItem(transcriptKey(sid));
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed : [];
  } catch (e) {
    return [];
  }
}

function saveTranscriptSnapshot(sid, entries) {
  if (!sid || !Array.isArray(entries)) return;
  try {
    sessionStorage.setItem(transcriptKey(sid), JSON.stringify(entries));
  } catch (e) {
    /* quota */
  }
}

function appendTranscriptTurn(sid, userText, assistantText, mode) {
  const prev = loadTranscriptSnapshot(sid);
  prev.push(
    { role: 'user', content: userText, mode },
    { role: 'assistant', content: assistantText, mode },
  );
  saveTranscriptSnapshot(sid, prev);
}

function mergeServerAndTranscript(serverMsgs, sid) {
  const server = Array.isArray(serverMsgs) ? serverMsgs : [];
  const local = loadTranscriptSnapshot(sid);
  if (local.length > server.length) {
    return local;
  }
  return server;
}

function normalizeMessageRow(m) {
  const role = String(m.role || '')
    .toLowerCase()
    .trim();
  return {
    role,
    content: m.content != null ? String(m.content) : '',
    mode: m.mode || 'chat',
  };
}

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
    sessionStorage.removeItem(STORAGE_UI_LAYOUT);
    if (typeof LessonsOpenedHistory !== 'undefined') {
      LessonsOpenedHistory.clear();
    }
  } catch (e) {
    /* ignore */
  }
  try {
    for (let i = sessionStorage.length - 1; i >= 0; i -= 1) {
      const k = sessionStorage.key(i);
      if (
        k &&
        (k.startsWith('lessonsWidgetLessons:') || k.startsWith(TRANSCRIPT_PREFIX))
      ) {
        sessionStorage.removeItem(k);
      }
    }
  } catch (e) {
    /* ignore */
  }
}

function captureChatUiLayout() {
  const expanded = assistantOverlay?.classList.contains('open');
  const compactOpen = chatWrapper?.classList.contains('open');
  if (expanded) return 'expanded';
  if (compactOpen) return 'compact';
  return 'closed';
}

function applyChatUiLayout(layout) {
  const l = layout || 'compact';
  if (l === 'expanded') {
    chatWrapper?.classList.add('open');
    assistantOverlay?.classList.add('open');
    document.body.classList.add('overlay-open');
  } else if (l === 'compact') {
    chatWrapper?.classList.add('open');
    assistantOverlay?.classList.remove('open');
    document.body.classList.remove('overlay-open');
  } else {
    chatWrapper?.classList.remove('open');
    assistantOverlay?.classList.remove('open');
    document.body.classList.remove('overlay-open');
  }
  /* Встроенный виджет на demo.html всегда остаётся развёрнутым в колонке. */
  if (chatWrapper?.classList.contains('chat-wrapper--embedded')) {
    chatWrapper.classList.add('open');
  }
}

function persistStateBeforeOpeningLesson() {
  if (!sessionId) return;
  try {
    sessionStorage.setItem(STORAGE_RETURNING_FROM_LESSON, '1');
    sessionStorage.setItem(STORAGE_SESSION_ID, sessionId);
    sessionStorage.setItem(STORAGE_UI_LAYOUT, captureChatUiLayout());
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

function isAssistantExpanded() {
  return Boolean(assistantOverlay?.classList.contains('open'));
}

/** Панель чата, которую сейчас видит пользователь: полноэкранная или компактная. */
function activeMessagesPanel() {
  return isAssistantExpanded() ? assistantMessages : messages;
}

/** Дублирует разметку чата во вторую панель (компакт ↔ полноэкранный). */
function mirrorChatPanelsFrom(sourcePanel) {
  if (!messages || !assistantMessages || !sourcePanel) return;
  const dest = sourcePanel === messages ? assistantMessages : messages;
  dest.innerHTML = sourcePanel.innerHTML;
}

function lessonPageHref(lessonCode) {
  const q = new URLSearchParams();
  q.set('lessonId', lessonCode);
  q.set('backendUrl', API_CONFIG.baseUrl);
  return `lesson.html?${q.toString()}`;
}

function renderOpenedLessonsPanels() {
  const hist =
    typeof LessonsOpenedHistory !== 'undefined' ? LessonsOpenedHistory.getList() : [];
  const ul = document.getElementById('openedLessonsSidebarList');
  if (!ul) return;
  ul.innerHTML = '';
  if (!hist.length) {
    const li = document.createElement('li');
    li.className = 'opened-lessons-empty';
    li.textContent =
      'Уроки появятся здесь после перехода по ссылке LL… из ответа ассистента.';
    ul.appendChild(li);
    return;
  }
  hist.forEach((entry) => {
    if (!entry || !entry.id) return;
    const id = entry.id;
    const title =
      entry.title && String(entry.title).trim() ? String(entry.title).trim() : id;
    let timeStr = '';
    try {
      timeStr = entry.openedAt
        ? new Date(entry.openedAt).toLocaleString('ru-RU', {
            day: 'numeric',
            month: 'short',
            hour: '2-digit',
            minute: '2-digit',
          })
        : '';
    } catch (e) {
      timeStr = '';
    }
    const li = document.createElement('li');
    li.className = 'opened-lessons-item';
    const a = document.createElement('a');
    a.className = 'opened-lessons-row lesson-inline-link';
    a.href = lessonPageHref(id);
    a.addEventListener('click', () => persistStateBeforeOpeningLesson());
    const titleEl = document.createElement('span');
    titleEl.className = 'opened-lessons-row-title';
    const primary = title.length > 120 ? `${title.slice(0, 117)}…` : title;
    titleEl.textContent = primary;
    titleEl.title = title;
    const meta = document.createElement('span');
    meta.className = 'opened-lessons-row-meta';
    if (title !== id) {
      meta.textContent = timeStr ? `${id} · ${timeStr}` : id;
    } else {
      meta.textContent = timeStr || '';
    }
    a.appendChild(titleEl);
    a.appendChild(meta);
    li.appendChild(a);
    ul.appendChild(li);
  });
}

function initOpenedLessonsUi() {
  document.body.addEventListener('click', (event) => {
    const btn = event.target.closest('.opened-lessons-clear-btn');
    if (!btn) return;
    if (typeof LessonsOpenedHistory !== 'undefined') LessonsOpenedHistory.clear();
  });
  window.addEventListener('lessonsOpenedHistoryUpdated', renderOpenedLessonsPanels);
  window.addEventListener('pageshow', () => {
    renderOpenedLessonsPanels();
  });
  window.addEventListener('storage', (event) => {
    if (
      typeof LessonsOpenedHistory !== 'undefined' &&
      event.key === LessonsOpenedHistory.STORAGE_KEY
    ) {
      renderOpenedLessonsPanels();
    }
  });
  renderOpenedLessonsPanels();
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

function looksLikeLessonCode(id) {
  return /^LL\d+$/i.test(id);
}

function normalizeBracketLessonId(raw) {
  return String(raw || '')
    .replace(/\u00a0/g, ' ')
    .replace(/[\u200b-\u200d\ufeff]/g, '')
    .trim();
}

function canonicalLlLessonId(raw) {
  const n = normalizeBracketLessonId(raw);
  const m = String(n).match(/^LL(\d+)$/i);
  return m ? `LL${m[1]}` : n;
}

function shouldLinkLessonBracketId(id, knownCodes) {
  if (knownCodes.has(id)) return true;
  return looksLikeLessonCode(id);
}

/** Текст между ссылками в скобках: голые LL1234 (как в ответах модели без [ ]) тоже делаем ссылками. */
function formatPlainSegmentWithBareLessonLinks(segment, known) {
  const re = /\b(LL\d+)\b/gi;
  let out = '';
  let last = 0;
  let m = re.exec(segment);
  while (m !== null) {
    out += escapeHtml(segment.slice(last, m.index));
    const id = canonicalLlLessonId(m[1]);
    if (id && shouldLinkLessonBracketId(id, known)) {
      const href = lessonPageHref(id);
      out += `<a class="lesson-inline-link" href="${href}">${escapeHtml(id)}</a>`;
    } else {
      out += escapeHtml(m[0]);
    }
    last = re.lastIndex;
    m = re.exec(segment);
  }
  out += escapeHtml(segment.slice(last));
  return out;
}

function formatAssistantBodyHtml(text, lessons) {
  const cleaned = stripMarkdownAsterisks(text)
    .replace(/\uff3b/g, '[')
    .replace(/\uff3d/g, ']');
  const known = buildKnownLessonCodes(lessons);
  const re = /\[([A-Za-zА-Яа-яЁё0-9][A-Za-zА-Яа-яЁё0-9._-]*)\]/g;
  let result = '';
  let last = 0;
  let m = re.exec(cleaned);
  while (m !== null) {
    result += formatPlainSegmentWithBareLessonLinks(cleaned.slice(last, m.index), known);
    const id = normalizeBracketLessonId(m[1]);
    if (!id) {
      result += escapeHtml(m[0]);
    } else if (shouldLinkLessonBracketId(id, known)) {
      const href = lessonPageHref(id);
      result += `[<a class="lesson-inline-link" href="${href}">${escapeHtml(id)}</a>]`;
    } else {
      result += escapeHtml(m[0]);
    }
    last = re.lastIndex;
    m = re.exec(cleaned);
  }
  result += formatPlainSegmentWithBareLessonLinks(cleaned.slice(last), known);
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
  el.className = 'bubble assistant bubble-loading';
  el.innerHTML = `Идёт обработка запроса…<span class="meta">assistant • ${now()} • ${mode}</span>`;
  container.appendChild(el);
  container.scrollTop = container.scrollHeight;
  return el;
}

function scrollChatPanelsToBottom() {
  [messages, assistantMessages].forEach((el) => {
    if (!el) return;
    el.scrollTo({ top: el.scrollHeight, behavior: 'auto' });
  });
}

/** После смены layout (компакт ↔ полноэкранный) высоты считаются заново — прокрутка дважды в rAF. */
function scrollChatPanelsToBottomSoon() {
  scrollChatPanelsToBottom();
  requestAnimationFrame(() => {
    scrollChatPanelsToBottom();
    requestAnimationFrame(scrollChatPanelsToBottom);
  });
}

function syncSmallToLarge() {
  mirrorChatPanelsFrom(messages);
  assistantInput.value = input.value;
  scrollChatPanelsToBottom();
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
  return sessionId;
}

async function tryRestoreSessionById(saved) {
  if (!saved) return false;
  try {
    const data = await apiService.getSession(saved);
    if (data.status !== 'active') return false;
    sessionId = data.session_id;
    sessionBootstrapped = true;
    messages.innerHTML = '';
    assistantMessages.innerHTML = '';
    const rawMsgs = mergeServerAndTranscript(data.messages, sessionId);
    const msgs = rawMsgs.map(normalizeMessageRow);
    saveTranscriptSnapshot(sessionId, msgs);
    let lastMode = currentMode;
    let assistantTurn = 0;
    for (let i = 0; i < msgs.length; i += 1) {
      const m = msgs[i];
      const mode = m.mode || 'chat';
      lastMode = mode;
      if (m.role === 'user') {
        bubble(messages, m.content, 'user', mode);
      } else if (m.role === 'assistant' || m.role === 'system') {
        const cachedLessons = loadAssistantLessons(sessionId, assistantTurn);
        assistantBubble(messages, m.content, cachedLessons, mode);
        assistantTurn += 1;
      } else {
        bubble(messages, m.content, 'assistant', mode);
        assistantTurn += 1;
      }
    }
    setMode(lastMode);
    if (msgs.length === 0) {
      seedConversation(messages);
    }
    syncSmallToLarge();
    try {
      const layout = sessionStorage.getItem(STORAGE_UI_LAYOUT) || 'compact';
      sessionStorage.removeItem(STORAGE_UI_LAYOUT);
      applyChatUiLayout(layout);
    } catch (e) {
      chatWrapper?.classList.add('open');
    }
    scrollChatPanelsToBottomSoon();
    renderOpenedLessonsPanels();
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

async function sendMessage(sourceInput) {
  if (loading) return;
  const message = sourceInput.value.trim();
  if (!message) return;

  document.querySelectorAll('.chat-welcome-seed').forEach((el) => el.remove());

  await ensureSession();
  const activeMode = currentMode;
  input.value = '';
  assistantInput.value = '';

  const panel = activeMessagesPanel();
  bubble(panel, message, 'user', activeMode);
  loading = true;
  const loader = loadingBubble(panel, activeMode);
  mirrorChatPanelsFrom(panel);

  try {
    const response = await apiService.respond(sessionId, message, activeMode);
    loader.remove();
    const answerText = response.text || response.answer || '';
    const lessons = response.lessons || [];
    assistantBubble(panel, answerText, lessons, activeMode);
    mirrorChatPanelsFrom(panel);
    const turnIndex = panel.querySelectorAll('.assistant-turn').length - 1;
    persistAssistantLessons(sessionId, turnIndex, lessons);
    appendTranscriptTurn(sessionId, message, answerText, activeMode);
  } catch (error) {
    loader.remove();
    bubble(panel, `Ошибка: ${error.message}`, 'assistant', activeMode);
    mirrorChatPanelsFrom(panel);
  } finally {
    loading = false;
    scrollChatPanelsToBottomSoon();
  }
}

launcher?.addEventListener('click', () => {
  chatWrapper.classList.add('open');
  scrollChatPanelsToBottomSoon();
});
closeBtn?.addEventListener('click', () => chatWrapper.classList.remove('open'));
expandBtn?.addEventListener('click', () => {
  syncSmallToLarge();
  assistantOverlay.classList.add('open');
  document.body.classList.add('overlay-open');
  scrollChatPanelsToBottomSoon();
  renderOpenedLessonsPanels();
});
assistantBack?.addEventListener('click', () => {
  if (input && assistantInput) {
    input.value = assistantInput.value;
  }
  mirrorChatPanelsFrom(assistantMessages);
  assistantOverlay.classList.remove('open');
  document.body.classList.remove('overlay-open');
  scrollChatPanelsToBottomSoon();
});
sendBtn?.addEventListener('click', () => sendMessage(input));
assistantSend?.addEventListener('click', () => sendMessage(assistantInput));
input?.addEventListener('keydown', (event) => {
  if (event.key === 'Enter') sendMessage(input);
});
assistantInput?.addEventListener('keydown', (event) => {
  if (event.key === 'Enter') sendMessage(assistantInput);
});
document.querySelectorAll('.mode-bar').forEach((bar) => {
  bar.addEventListener('click', (event) => {
    const btn = event.target.closest('.mode-btn');
    if (!btn) return;
    setMode(btn.dataset.mode);
  });
});
function onLessonLinkActivate(event) {
  const a = event.target.closest('a.lesson-inline-link');
  if (!a) return;
  persistStateBeforeOpeningLesson();
  if (typeof LessonsOpenedHistory !== 'undefined') {
    try {
      const href = a.getAttribute('href') || '';
      const u = new URL(href, window.location.href);
      const lid = u.searchParams.get('lessonId');
      if (lid) {
        LessonsOpenedHistory.record(lid, null);
      } else {
        const t = (a.textContent || '').trim();
        if (/^LL\d+$/i.test(t)) LessonsOpenedHistory.record(t, null);
      }
    } catch (e) {
      const t = (a.textContent || '').trim();
      if (/^LL\d+$/i.test(t)) LessonsOpenedHistory.record(t, null);
    }
  }
}
messages?.addEventListener('click', onLessonLinkActivate);
assistantMessages?.addEventListener('click', onLessonLinkActivate);
messages?.addEventListener('auxclick', onLessonLinkActivate);
assistantMessages?.addEventListener('auxclick', onLessonLinkActivate);

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
  syncSmallToLarge();
  scrollChatPanelsToBottomSoon();
  renderOpenedLessonsPanels();
}

initOpenedLessonsUi();
bootstrapWidget();
