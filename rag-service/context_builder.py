from schemas import Mode

_SOURCE_LABEL = {
    "lesson": "УРОК",
    "report": "ОТЧЁТ",
    "info_sheet": "ИНФОЛИСТ",
    "letter": "ПИСЬМО",
    "glossary": "ГЛОССАРИЙ",
}


def _block_label(item: dict) -> str:
    meta = item.get("metadata") or {}
    st = item.get("source_type") or meta.get("source_type") or "lesson"
    lid = meta.get("ID_урока") or meta.get("lesson_id") or item.get("id", "")
    title = (item.get("title") or "").strip()
    if st == "lesson":
        return f"[{lid}] {title}".strip()
    if st == "glossary":
        return f"[ГЛОССАРИЙ: {meta.get('Термин', title)}]"
    tag = _SOURCE_LABEL.get(st, "МАТЕРИАЛ")
    return f"[{tag} {lid}] {title}".strip()


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
