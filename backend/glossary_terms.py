"""
Подмешивание определений из glossary.json, если термин явно упомянут в сообщении.
Совпадение по целым терминам (границы «слова»), без привязки к формулировке вопроса.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

# Не буква/цифра: до и после термина не должно продолжаться «слово».
_BOUND = r"(?<![A-Za-zА-Яа-яЁё0-9])"
_BOUND_END = r"(?![A-Za-zА-Яа-яЁё0-9])"

_glossary_cache: tuple[str | None, float | None, list[dict[str, Any]]] = (None, None, [])


def _load_glossary(path: Path) -> list[dict[str, Any]]:
    global _glossary_cache
    if not path.is_file():
        return []
    resolved = str(path.resolve())
    mtime = path.stat().st_mtime
    if _glossary_cache[0] == resolved and _glossary_cache[1] == mtime and _glossary_cache[2]:
        return _glossary_cache[2]
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        _glossary_cache = (resolved, mtime, [])
        return []
    _glossary_cache = (resolved, mtime, raw)
    return raw


def _term_pattern(term: str) -> re.Pattern[str]:
    escaped = re.escape(term.strip())
    return re.compile(_BOUND + escaped + _BOUND_END, re.IGNORECASE)


def mentioned_glossary_entries(message: str, glossary_path: str) -> list[tuple[str, str]]:
    """
    Возвращает пары (Термин, Определение) для терминов из глоссария,
    которые встречаются в message как отдельное вхождение (не подстрока внутри другого слова).
    Длинные термины проверяются первыми, чтобы «Извлечённый урок» не ломался коротким «урок».
    """
    path = Path(glossary_path)
    rows = _load_glossary(path)
    if not rows or not (message or "").strip():
        return []

    pairs: list[tuple[str, str, int]] = []
    seen_spans: list[tuple[int, int]] = []

    def overlaps(a: int, b: int) -> bool:
        for s, e in seen_spans:
            if not (b <= s or a >= e):
                return True
        return False

    # Сначала длинные названия — приоритет при частичном пересечении формулировок
    sorted_rows = sorted(
        (r for r in rows if isinstance(r, dict)),
        key=lambda r: len(str(r.get("Термин") or "")),
        reverse=True,
    )

    for row in sorted_rows:
        term = str(row.get("Термин") or "").strip()
        definition = str(row.get("Определение") or "").strip()
        if not term or not definition:
            continue
        try:
            pat = _term_pattern(term)
        except re.error:
            continue
        for m in pat.finditer(message):
            a, b = m.span()
            if overlaps(a, b):
                continue
            pairs.append((term, definition, a))
            seen_spans.append((a, b))
            break  # одного вхождения термина достаточно

    pairs.sort(key=lambda x: x[2])
    return [(t, d) for t, d, _ in pairs]


def prepend_glossary_block(context: str, entries: list[tuple[str, str]]) -> str:
    if not entries:
        return context
    lines = [f'«{t}»: {d}' for t, d in entries]
    block = "[ГЛОССАРИЙ ЕБДИУ — официальные формулировки]\n" + "\n".join(lines)
    if context.strip():
        return block + "\n\n---\n\n" + context
    return block
