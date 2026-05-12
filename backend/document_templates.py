"""
Загрузчик шаблонов документов из папки `Шаблоны/` (ch_2.txt, ch_9.txt, ch_10.txt, ch_11.txt и т.п.).

Каждый файл — JSON-подобная структура: список словарей-полей, у каждого поля есть
`description` (человеко-читаемая подпись), `required` (bool), `type`.
Первое поле в файле — заголовок документа (его `description` — имя шаблона).

Загрузчик устойчив к лёгкой битости JSON (например, в ch_2.txt отсутствует `},` между
двумя верхнеуровневыми объектами): извлекает все `"ключ": {...}` блоки регулярным
проходом по тексту, игнорируя структурные ошибки.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

_FIELD_BLOCK_RE = re.compile(
    r'"([A-Za-z_][A-Za-z0-9_]*)"\s*:\s*(\{[^{}]*\})',
    re.DOTALL,
)


def _parse_template_file(path: Path) -> list[tuple[str, dict[str, Any]]]:
    """Возвращает упорядоченный список (ключ_поля, spec) из файла шаблона."""
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return []
    out: list[tuple[str, dict[str, Any]]] = []
    seen: set[str] = set()
    for m in _FIELD_BLOCK_RE.finditer(text):
        key = m.group(1)
        if key in seen:
            continue
        try:
            spec = json.loads(m.group(2))
        except json.JSONDecodeError:
            continue
        if not isinstance(spec, dict):
            continue
        # отсекаем «вложенные» спецификации (формат-поля внутри типа) — у них нет description
        if "description" not in spec:
            continue
        out.append((key, spec))
        seen.add(key)
    return out


def load_document_templates(dir_path: Path) -> dict[str, dict[str, Any]]:
    """Читает все *.txt из dir_path и возвращает {имя_шаблона: {...}}.

    Структура значения:
        {
            "file": "ch_2.txt",
            "title": "Формат заявки на документирование урока (улучшения)",
            "required": [(field_key, description), ...],
            "optional": [(field_key, description), ...],
            "reports_kinds": ["Формат заявки на документирование урока (улучшения)"],
        }
    Имя шаблона = title (берётся из description первого поля файла).
    `reports_kinds` — список значений `Вид_шаблона` из reports.json, к которым относится
    этот шаблон (для title вида "А / Б" — две позиции).
    """
    if not dir_path.is_dir():
        return {}
    result: dict[str, dict[str, Any]] = {}
    for path in sorted(dir_path.glob("*.txt")):
        fields = _parse_template_file(path)
        if not fields:
            continue
        title = str(fields[0][1].get("description") or "").strip()
        if not title:
            continue
        required: list[tuple[str, str]] = []
        optional: list[tuple[str, str]] = []
        for key, spec in fields[1:]:
            desc = str(spec.get("description") or key).strip()
            if bool(spec.get("required")):
                required.append((key, desc))
            else:
                optional.append((key, desc))
        # Если заголовок составной ("А / Б") — разворачиваем в две отдельные записи каталога
        # с одинаковыми полями. Так пользователь обязан выбрать одно из значений, а LLM не
        # путается с «первой половиной» заголовка.
        sub_titles = [s.strip() for s in re.split(r"\s*/\s*", title) if s.strip()]
        if len(sub_titles) <= 1:
            sub_titles = [title]
        for sub in sub_titles:
            result[sub] = {
                "file": path.name,
                "title": sub,
                "required": required,
                "optional": optional,
                "reports_kinds": [sub],
            }
    return result


def load_letter_templates(dir_path: Path) -> dict[str, dict[str, Any]]:
    """Шаблоны писем (samples/letters/*.txt). Структура та же, что у документов,
    но заголовок ответа модель будет брать из ЗАПРОСА пользователя
    (служебная записка / письмо-запрос / уведомление и т. п.), а не из шаблона."""
    return load_document_templates(dir_path)


def select_template(
    user_message: str, templates: dict[str, dict[str, Any]]
) -> str | None:
    """Грубое сопоставление запроса пользователя с заголовком шаблона.
    Возвращает title однозначно подходящего шаблона, иначе None.

    Логика: для каждого заголовка считаем, сколько «значащих» слов из него
    встретилось в запросе (длиннее 4 символов, в нижнем регистре). Выигрывает
    кандидат с максимальным числом совпадений, если оно ≥ 2 и строго больше
    второго места (иначе неоднозначно).
    """
    msg = (user_message or "").lower().replace("ё", "е")
    if not msg.strip() or not templates:
        return None
    scores: list[tuple[str, int]] = []
    for title in templates.keys():
        words = re.findall(r"[а-яa-z]{5,}", title.lower().replace("ё", "е"))
        if not words:
            continue
        score = sum(1 for w in words if w in msg)
        scores.append((title, score))
    if not scores:
        return None
    scores.sort(key=lambda x: x[1], reverse=True)
    best_title, best_score = scores[0]
    second_score = scores[1][1] if len(scores) > 1 else 0
    if best_score >= 2 and best_score > second_score:
        return best_title
    return None


def render_focused_template_block(
    templates: dict[str, dict[str, Any]],
    selected_title: str | None,
    reports_path: Path,
    *,
    max_examples: int = 1,
    max_field_chars: int = 220,
) -> str:
    """Если выбран один шаблон — выводим его поля + JSON-примеры. Иначе — только
    короткий список доступных шаблонов (без примеров), чтобы LLM попросила уточнить.
    """
    if not templates:
        return "Каталог шаблонов документов недоступен."
    if selected_title and selected_title in templates:
        tpl = templates[selected_title]
        chunks: list[str] = [
            f"=== ВЫБРАННЫЙ ШАБЛОН: «{selected_title}» ===",
            "Обязательные поля (required) — выводи в документе:",
        ]
        for i, (_k, desc) in enumerate(tpl["required"], start=1):
            chunks.append(f"  {i}. {desc}")
        if tpl["optional"]:
            chunks.append("Необязательные поля (optional) — перечисляй в конце как предложение дополнить:")
            for _k, desc in tpl["optional"]:
                chunks.append(f"  - {desc}")
        examples = collect_style_examples(
            reports_path, tpl.get("reports_kinds") or [], max_examples=max_examples
        )
        if examples:
            chunks.append("Образцы стиля заполнения (из reports.json, тот же «Вид_шаблона»):")
            skip_meta = {"Имя_шаблона", "Вид_шаблона"}
            for ex in examples:
                short: dict[str, Any] = {}
                for k, v in ex.items():
                    if k in skip_meta or v in (None, ""):
                        continue
                    if not isinstance(v, str):
                        v = str(v)
                    if len(v) > max_field_chars:
                        v = v[:max_field_chars].rstrip() + "…"
                    short[k] = v
                chunks.append("  " + json.dumps(short, ensure_ascii=False))
        return "\n".join(chunks)
    # Неоднозначно — отдаём только список заголовков (короткий блок).
    titles = list(templates.keys())
    lines = ["ДОСТУПНЫЕ ШАБЛОНЫ ДОКУМЕНТОВ (выбор шаблона неоднозначен — задай уточнение):"]
    for t in titles:
        lines.append(f"  — {t}")
    return "\n".join(lines)


def render_focused_letter_block(
    templates: dict[str, dict[str, Any]],
    letters_path: Path,
    *,
    max_examples: int = 1,
    max_field_chars: int = 220,
) -> str:
    """Письма — шаблон один. Всегда подмешиваем его целиком + 1 пример."""
    if not templates:
        return "Каталог шаблонов писем недоступен."
    # Берём первый (и обычно единственный) шаблон.
    title, tpl = next(iter(templates.items()))
    chunks: list[str] = [
        f"=== ШАБЛОН ПИСЬМА: «{title}» ===",
        "Обязательные поля (required) — выводи в письме:",
    ]
    for i, (_k, desc) in enumerate(tpl["required"], start=1):
        chunks.append(f"  {i}. {desc}")
    if tpl["optional"]:
        chunks.append("Необязательные поля (optional) — перечисляй в конце как предложение дополнить:")
        for _k, desc in tpl["optional"]:
            chunks.append(f"  - {desc}")
    if letters_path.is_file() and max_examples > 0:
        try:
            raw = json.loads(letters_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            raw = []
        if isinstance(raw, list):
            skip_meta = {"Имя_документа", "Вид_документа"}
            taken = 0
            for it in raw:
                if not isinstance(it, dict):
                    continue
                short: dict[str, Any] = {}
                for k, v in it.items():
                    if k in skip_meta or v in (None, ""):
                        continue
                    if not isinstance(v, str):
                        v = str(v)
                    if len(v) > max_field_chars:
                        v = v[:max_field_chars].rstrip() + "…"
                    short[k] = v
                if taken == 0:
                    chunks.append("Образец стиля письма (из letters.json):")
                chunks.append("  " + json.dumps(short, ensure_ascii=False))
                taken += 1
                if taken >= max_examples:
                    break
    return "\n".join(chunks)


def collect_style_examples(
    reports_path: Path, reports_kinds: list[str], *, max_examples: int = 2
) -> list[dict[str, Any]]:
    """Возвращает до max_examples записей из reports.json, где Вид_шаблона совпадает
    с одним из reports_kinds. Используется как образец стиля для заполнения полей.
    """
    if not reports_path.is_file() or not reports_kinds:
        return []
    try:
        raw = json.loads(reports_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    if not isinstance(raw, list):
        return []
    target = {k.strip() for k in reports_kinds}
    out: list[dict[str, Any]] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        kind = (item.get("Вид_шаблона") or "").strip()
        if kind in target:
            out.append(item)
            if len(out) >= max_examples:
                break
    return out


def render_template_block(
    templates: dict[str, dict[str, Any]],
    reports_path: Path,
    *,
    max_examples: int = 1,
    max_field_chars: int = 220,
) -> str:
    """Готовит текст для подмешивания в промпт document-режима.
    Включает: заголовки шаблонов, required/optional подписи полей и компактный
    пример стиля из reports.json (1 запись на шаблон, поля усечены).

    Блок строится ОДИН раз при старте сервиса и переиспользуется во всех запросах —
    Groq кэширует одинаковый префикс промпта, поэтому за повторные обращения к
    одинаковому блоку токены платятся только при первом обращении.
    """
    if not templates:
        return "Каталог шаблонов документов недоступен."
    chunks: list[str] = []
    skip_meta = {"Имя_шаблона", "Вид_шаблона", "Дата_утверждения"}
    for idx, (title, tpl) in enumerate(templates.items(), start=1):
        chunks.append(f"=== ШАБЛОН {idx}: «{title}» ===")
        chunks.append("Обязательные поля (required) — выводи в документе:")
        for i, (_k, desc) in enumerate(tpl["required"], start=1):
            chunks.append(f"  {i}. {desc}")
        if tpl["optional"]:
            chunks.append("Необязательные поля (optional) — перечисляй в конце как предложение дополнить:")
            for _k, desc in tpl["optional"]:
                chunks.append(f"  - {desc}")
        examples = collect_style_examples(
            reports_path, tpl.get("reports_kinds") or [], max_examples=max_examples
        )
        if examples:
            chunks.append("Образец стиля заполнения (пример из reports.json, тот же «Вид_шаблона»):")
            for ex in examples:
                short: dict[str, Any] = {}
                for k, v in ex.items():
                    if k in skip_meta or v in (None, ""):
                        continue
                    if not isinstance(v, str):
                        v = str(v)
                    if len(v) > max_field_chars:
                        v = v[:max_field_chars].rstrip() + "…"
                    short[k] = v
                chunks.append("  " + json.dumps(short, ensure_ascii=False))
        chunks.append("")
    return "\n".join(chunks).rstrip()


def render_letter_block(
    templates: dict[str, dict[str, Any]],
    letters_path: Path,
    *,
    max_examples: int = 1,
    max_field_chars: int = 220,
) -> str:
    """Готовит текст для подмешивания в промпт mail-режима.

    Особенности по сравнению с документами:
    - Шаблон письма ОДИН (общая структура: реквизиты, тема, текст, подписанты).
    - Заголовок (первая строка ответа) берётся из ЗАПРОСА пользователя
      (служебная записка, письмо-запрос, уведомление и т. п.) — НЕ из шаблона.
    - В качестве образцов стиля используется letters.json по совпадающему «Вид_документа».
    """
    if not templates:
        return "Каталог шаблонов писем недоступен."
    chunks: list[str] = []
    skip_meta = {"Имя_документа", "Вид_документа"}
    for idx, (title, tpl) in enumerate(templates.items(), start=1):
        chunks.append(f"=== ШАБЛОН ПИСЬМА {idx}: «{title}» ===")
        chunks.append("Обязательные поля (required) — выводи в письме:")
        for i, (_k, desc) in enumerate(tpl["required"], start=1):
            chunks.append(f"  {i}. {desc}")
        if tpl["optional"]:
            chunks.append("Необязательные поля (optional) — перечисляй в конце как предложение дополнить:")
            for _k, desc in tpl["optional"]:
                chunks.append(f"  - {desc}")
        # Стиль письма перенимаем из letters.json (там Вид_документа = «Служебная записка», «Письмо-запрос» и т. п.).
        # Берём первые попавшиеся записи (без фильтра по подвиду — стиль у писем общий).
        examples: list[dict[str, Any]] = []
        if letters_path.is_file() and max_examples > 0:
            try:
                raw = json.loads(letters_path.read_text(encoding="utf-8"))
                if isinstance(raw, list):
                    for it in raw:
                        if isinstance(it, dict):
                            examples.append(it)
                        if len(examples) >= max_examples:
                            break
            except (OSError, json.JSONDecodeError):
                examples = []
        if examples:
            chunks.append("Образец стиля письма (пример из letters.json):")
            for ex in examples:
                short: dict[str, Any] = {}
                for k, v in ex.items():
                    if k in skip_meta or v in (None, ""):
                        continue
                    if not isinstance(v, str):
                        v = str(v)
                    if len(v) > max_field_chars:
                        v = v[:max_field_chars].rstrip() + "…"
                    short[k] = v
                chunks.append("  " + json.dumps(short, ensure_ascii=False))
        chunks.append("")
    return "\n".join(chunks).rstrip()
