/**
 * История открытых карточек уроков (sessionStorage — только текущая вкладка, без сохранения между визитами).
 */
(function (w) {
  var STORAGE_KEY = 'lessonsWidgetOpenedHistory';
  var MAX_ITEMS = 25;

  function canonicalId(raw) {
    var s = String(raw || '').trim().replace(/\u00a0/g, ' ');
    var m = s.match(/^LL(\d+)$/i);
    return m ? 'LL' + m[1] : '';
  }

  /** Удаляет следы старого формата в localStorage (раньше история жила там). */
  function dropLegacyLocalStorage() {
    try {
      w.localStorage.removeItem(STORAGE_KEY);
    } catch (e) {
      /* ignore */
    }
  }

  function load() {
    dropLegacyLocalStorage();
    try {
      var raw = w.sessionStorage.getItem(STORAGE_KEY);
      if (!raw) return [];
      var arr = JSON.parse(raw);
      return Array.isArray(arr) ? arr : [];
    } catch (e) {
      return [];
    }
  }

  function save(items) {
    try {
      w.sessionStorage.setItem(STORAGE_KEY, JSON.stringify(items));
    } catch (e) {
      /* quota / private mode */
    }
  }

  function record(lessonId, title) {
    var id = canonicalId(lessonId);
    if (!id) return;
    var label = title && String(title).trim() ? String(title).trim() : id;
    var now = new Date().toISOString();
    var items = load().filter(function (x) {
      return x && x.id !== id;
    });
    items.unshift({ id: id, title: label, openedAt: now });
    items = items.slice(0, MAX_ITEMS);
    save(items);
    try {
      w.dispatchEvent(new CustomEvent('lessonsOpenedHistoryUpdated'));
    } catch (e) {
      /* ignore */
    }
  }

  function clear() {
    save([]);
    try {
      w.dispatchEvent(new CustomEvent('lessonsOpenedHistoryUpdated'));
    } catch (e) {
      /* ignore */
    }
  }

  function getList() {
    return load();
  }

  w.LessonsOpenedHistory = {
    record: record,
    clear: clear,
    getList: getList,
    canonicalId: canonicalId,
    STORAGE_KEY: STORAGE_KEY,
    MAX_ITEMS: MAX_ITEMS,
  };
})(typeof window !== 'undefined' ? window : this);
