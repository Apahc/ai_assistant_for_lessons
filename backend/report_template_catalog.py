"""Человекочитаемые подписи полей отчётных шаблонов из JSON-схем в data/report_template_schemas/."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

_PARTICIPANT_RE = re.compile(r"^participant_(\d+)_(.+)$")


def human_field_label(field_key: str, spec: dict[str, Any]) -> str:
    desc = (spec.get("description") or "").strip()
    m = _PARTICIPANT_RE.match(field_key)
    if m:
        n = m.group(1)
        if desc:
            return f"Участник {n}: {desc}"
        return f"Участник {n}: {field_key}"
    return desc or field_key


def _ordered_field_entries(fields: dict[str, Any]) -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    for key in fields.keys():
        spec = fields[key]
        if not isinstance(spec, dict):
            continue
        out.append((key, human_field_label(key, spec)))
    return out


def load_kind_to_ordered_labels(schemas_dir: Path) -> dict[str, list[tuple[str, str]]]:
    """Читает appendix_*.json с ключами template_kind и fields."""
    if not schemas_dir.is_dir():
        return {}
    result: dict[str, list[tuple[str, str]]] = {}
    for path in sorted(schemas_dir.glob("*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(data, dict):
            continue
        kind = (data.get("template_kind") or "").strip()
        fields = data.get("fields")
        if not kind or not isinstance(fields, dict):
            continue
        result[kind] = _ordered_field_entries(fields)
    return result
