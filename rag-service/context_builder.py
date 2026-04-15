from schemas import Mode


def assemble_context(mode: Mode, lesson_results: list[dict], meta_results: list[dict]) -> tuple[str, str, list[str]]:
    lesson_blocks = [
        f"[{item['metadata'].get('lesson_id', item['id'])}] {item.get('title', '')}\n{item['text']}"
        for item in lesson_results
    ]
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
