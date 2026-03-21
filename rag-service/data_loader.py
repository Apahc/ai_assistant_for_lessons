import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class SourceDocument:
    id: str
    title: str
    text: str
    source_type: str
    metadata: dict[str, Any]


class DataLoader:
    def __init__(self, lessons_path: str, meta_path: str) -> None:
        self.lessons_path = Path(lessons_path)
        self.meta_path = Path(meta_path)

    def load_lessons(self) -> list[SourceDocument]:
        if not self.lessons_path.exists():
            return []
        raw_lessons = json.loads(self.lessons_path.read_text(encoding="utf-8"))
        return [self._normalize_lesson(item) for item in raw_lessons]

    def load_meta(self) -> list[SourceDocument]:
        if not self.meta_path.exists():
            return []
        suffix = self.meta_path.suffix.lower()
        if suffix in {".txt", ".md"}:
            text = self.meta_path.read_text(encoding="utf-8").strip()
            if not text:
                return []
            return [
                SourceDocument(
                    id="portal-meta::0",
                    title="Portal metadata",
                    text=text,
                    source_type="meta",
                    metadata={"source_type": "meta", "title": "Portal metadata"},
                )
            ]
        if suffix == ".json":
            raw_meta = json.loads(self.meta_path.read_text(encoding="utf-8"))
            if isinstance(raw_meta, list):
                documents = []
                for index, item in enumerate(raw_meta):
                    documents.append(self._normalize_meta_item(item, index))
                return [item for item in documents if item.text]
            return [self._normalize_meta_item(raw_meta, 0)]
        return []

    def _normalize_lesson(self, raw: dict[str, Any]) -> SourceDocument:
        lesson_id = str(raw.get("ID_урока") or raw.get("lesson_id") or raw.get("id") or "")
        title = str(
            raw.get("Наименование_урока")
            or raw.get("Название урока")
            or raw.get("Наименование")
            or raw.get("Тема")
            or lesson_id
            or "lesson"
        )
        scalar_items: list[str] = []
        metadata: dict[str, Any] = {}
        for key, value in raw.items():
            if isinstance(value, (str, int, float, bool)) and value not in ("", None):
                text_value = str(value).strip()
                metadata[key] = text_value
                if not text_value.startswith("\\\\"):
                    scalar_items.append(f"{key}: {text_value}")
        return SourceDocument(
            id=lesson_id or title,
            title=title,
            text="\n".join(scalar_items),
            source_type="lesson",
            metadata=metadata,
        )

    def _normalize_meta_item(self, raw: Any, index: int) -> SourceDocument:
        if isinstance(raw, str):
            return SourceDocument(
                id=f"portal-meta::{index}",
                title=f"Portal metadata {index + 1}",
                text=raw.strip(),
                source_type="meta",
                metadata={"source_type": "meta"},
            )

        if isinstance(raw, dict):
            title = str(raw.get("title") or raw.get("name") or raw.get("section") or f"Portal metadata {index + 1}")
            scalar_items: list[str] = []
            metadata: dict[str, Any] = {}
            for key, value in raw.items():
                if isinstance(value, (str, int, float, bool)) and value not in ("", None):
                    text_value = str(value).strip()
                    metadata[key] = text_value
                    scalar_items.append(f"{key}: {text_value}")
            return SourceDocument(
                id=str(raw.get("id") or f"portal-meta::{index}"),
                title=title,
                text="\n".join(scalar_items),
                source_type="meta",
                metadata=metadata,
            )

        return SourceDocument(
            id=f"portal-meta::{index}",
            title=f"Portal metadata {index + 1}",
            text="",
            source_type="meta",
            metadata={},
        )
