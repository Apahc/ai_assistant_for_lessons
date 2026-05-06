from schemas import Mode

_SOURCE_LABEL = {
    "lesson": "УРОК",
    "report": "ОТЧЁТ",
    "info_sheet": "ИНФОЛИСТ",
    "letter": "ПИСЬМО",
    "glossary": "ГЛОССАРИЙ",
}


def _record_index_from_doc_id(doc_id: str) -> str | None:
    """Порядковый номер записи в json (последний сегмент doc_id до :: чанка)."""
    if not doc_id or not str(doc_id).strip():
        return None
    base = str(doc_id).split("::", 1)[0].strip()
    parts = base.split(":")
    if len(parts) >= 3:
        tail = parts[-1]
        return tail if tail.isdigit() else None
    return None


def _truncate_title(title: str, max_len: int = 140) -> str:
    t = (title or "").strip()
    if len(t) <= max_len:
        return t
    return f"{t[: max_len - 1]}…"


def _human_auxiliary_citation(tag: str, meta: dict, item: dict) -> str:
    """Человекочитаемая ссылка на письмо/отчёт/инфолист вместо сырого letter:noid:7."""
    title = (item.get("title") or "").strip()
    doc_id = str(meta.get("doc_id") or "").strip()
    idx = _record_index_from_doc_id(doc_id)
    title_short = _truncate_title(title, 120)
    if idx and title_short:
        return f"{tag} №{idx} — {title_short}"
    if idx:
        return f"{tag} №{idx}"
    if title_short:
        return f"{tag}: {title_short}"
    return tag


def _block_label(item: dict) -> str:
    meta = item.get("metadata") or {}
    st = item.get("source_type") or meta.get("source_type") or "lesson"
    title = (item.get("title") or "").strip()
    if st == "lesson":
        lid = meta.get("ID_урока") or meta.get("lesson_id") or ""
        lid = str(lid).strip()
        if lid:
            return f"[{lid}] {title}".strip()
        return f"[УРОК] {title}".strip() if title else "[УРОК]"
    if st == "glossary":
        return f"[ГЛОССАРИЙ: {meta.get('Термин', title)}]"
    tag = _SOURCE_LABEL.get(st, "МАТЕРИАЛ")
    cite = _human_auxiliary_citation(tag, meta, item)
    return f"[{cite}]"


def assemble_context(mode: Mode, lesson_results: list[dict], meta_results: list[dict]) -> tuple[str, str, list[str]]:
    lesson_blocks = [f"{_block_label(item)}\n{item['text']}" for item in lesson_results]
    meta_blocks = [
        f"[META] {item.get('title', '')}\n{item['text']}"
        for item in meta_results
    ]

    # context = уроки + мета (количество меты уже ограничено в _retrieve_meta по mode)
    if mode == "search":
        context_blocks = lesson_blocks
    elif mode == "mail":
        context_blocks = lesson_blocks + meta_blocks[:1]
    elif mode == "document":
        context_blocks = lesson_blocks + meta_blocks[:2]
    else:
        context_blocks = lesson_blocks + meta_blocks

    context = "\n\n".join(context_blocks)
    meta_context = "\n\n".join(meta_blocks)
    lessons_texts = [item["text"] for item in lesson_results]

    return context, meta_context, lessons_texts
