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
    def __init__(
        self,
        lessons_path: str,
        meta_path: str,
        *,
        reports_path: str | None = None,
        information_sheets_path: str | None = None,
        letters_path: str | None = None,
        glossary_path: str | None = None,
    ) -> None:
        self.lessons_path = Path(lessons_path)
        self.meta_path = Path(meta_path)
        self.reports_path = Path(reports_path) if reports_path else None
        self.information_sheets_path = Path(information_sheets_path) if information_sheets_path else None
        self.letters_path = Path(letters_path) if letters_path else None
        self.glossary_path = Path(glossary_path) if glossary_path else None

    def load_lessons(self) -> list[SourceDocument]:
        if not self.lessons_path.exists():
            return []
        raw_lessons = json.loads(self.lessons_path.read_text(encoding="utf-8"))
        return [self._normalize_lesson(item) for item in raw_lessons]

    def load_reports(self) -> list[SourceDocument]:
        return self._load_json_array(self.reports_path, "report", title_keys=("Имя_шаблона", "Наименование_урока"))

    def load_information_sheets(self) -> list[SourceDocument]:
        return self._load_json_array(
            self.information_sheets_path,
            "info_sheet",
            title_keys=("Наименование_урока", "Вид_документа"),
        )

    def load_letters(self) -> list[SourceDocument]:
        return self._load_json_array(self.letters_path, "letter", title_keys=("Тема", "Имя_документа"))

    def load_glossary(self) -> list[SourceDocument]:
        if not self.glossary_path or not self.glossary_path.exists():
            return []
        raw = json.loads(self.glossary_path.read_text(encoding="utf-8"))
        if not isinstance(raw, list):
            return []
        out: list[SourceDocument] = []
        for index, item in enumerate(raw):
            if not isinstance(item, dict):
                continue
            term = str(item.get("Термин") or f"term_{index}").strip()
            doc_id = f"glossary::{index}"
            title = term or f"Глоссарий {index + 1}"
            doc = self._flatten_record(item, source_type="glossary", doc_id=doc_id, title=title)
            if doc.text:
                out.append(doc)
        return out

    def load_lessons_corpus(self) -> list[SourceDocument]:
        """Уроки + отчёты + инфолисты + письма + глоссарий для одной поисковой коллекции."""
        return (
            self.load_lessons()
            + self.load_reports()
            + self.load_information_sheets()
            + self.load_letters()
            + self.load_glossary()
        )

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

    def _load_json_array(
        self,
        path: Path | None,
        source_type: str,
        *,
        title_keys: tuple[str, ...],
    ) -> list[SourceDocument]:
        if not path or not path.exists():
            return []
        raw = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(raw, list):
            return []
        out: list[SourceDocument] = []
        for index, item in enumerate(raw):
            if not isinstance(item, dict):
                continue
            lid = str(item.get("ID_урока") or item.get("lesson_id") or "").strip()
            doc_id = f"{source_type}:{lid or 'noid'}:{index}"
            title = ""
            for key in title_keys:
                v = item.get(key)
                if isinstance(v, str) and v.strip():
                    title = v.strip()
                    break
            if not title:
                title = doc_id
            doc = self._flatten_record(item, source_type=source_type, doc_id=doc_id, title=title)
            if doc.text:
                out.append(doc)
        return out

    def _value_to_lines(self, key: str, value: Any) -> tuple[dict[str, Any], list[str]]:
        """Скаляры и вложенные структуры -> метаданные и строки для индексации."""
        meta: dict[str, Any] = {}
        lines: list[str] = []
        if isinstance(value, (str, int, float, bool)) and value not in ("", None):
            text_value = str(value).strip()
            meta[key] = text_value
            if not text_value.startswith("\\\\"):
                lines.append(f"{key}: {text_value}")
        elif isinstance(value, dict | list):
            dumped = json.dumps(value, ensure_ascii=False)
            meta[key] = dumped
            lines.append(f"{key}: {dumped}")
        return meta, lines

    def _flatten_record(
        self,
        raw: dict[str, Any],
        *,
        source_type: str,
        doc_id: str,
        title: str,
    ) -> SourceDocument:
        scalar_items: list[str] = []
        metadata: dict[str, Any] = {"source_type": source_type}
        for key, value in raw.items():
            m, lines = self._value_to_lines(key, value)
            metadata.update(m)
            scalar_items.extend(lines)
        return SourceDocument(
            id=doc_id,
            title=title,
            text="\n".join(scalar_items),
            source_type=source_type,
            metadata=metadata,
        )

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
            elif isinstance(value, dict | list):
                dumped = json.dumps(value, ensure_ascii=False)
                metadata[key] = dumped
                scalar_items.append(f"{key}: {dumped}")
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
                elif isinstance(value, dict | list):
                    dumped = json.dumps(value, ensure_ascii=False)
                    metadata[key] = dumped
                    scalar_items.append(f"{key}: {dumped}")
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
