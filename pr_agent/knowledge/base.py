"""
Knowledge base system for code review best practices and patterns.
"""
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional, Set, Any
import json
from pathlib import Path


class KnowledgeType(Enum):
    """Type of knowledge entry."""
    BEST_PRACTICE = "best_practice"
    ANTI_PATTERN = "anti_pattern"
    CODE_PATTERN = "code_pattern"
    CASE_STUDY = "case_study"
    GUIDELINE = "guideline"
    FAQ = "faq"


class Severity(Enum):
    """Severity level for patterns."""
    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class KnowledgeEntry:
    """A knowledge base entry."""
    id: str
    title: str
    type: KnowledgeType
    content: str
    tags: List[str]
    language: Optional[str] = None
    severity: Optional[Severity] = None
    examples: List[Dict[str, str]] = field(default_factory=list)
    related_entries: List[str] = field(default_factory=list)
    references: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    view_count: int = 0
    helpful_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SearchResult:
    """Search result with relevance score."""
    entry: KnowledgeEntry
    relevance_score: float
    matched_fields: List[str]


class KnowledgeBase:
    """Knowledge base management system."""

    def __init__(self, storage_path: Optional[Path] = None):
        """Initialize knowledge base."""
        self.storage_path = storage_path or Path(".pr_agent/knowledge")
        self.entries: Dict[str, KnowledgeEntry] = {}
        self.tag_index: Dict[str, Set[str]] = {}
        self.language_index: Dict[str, Set[str]] = {}
        self.type_index: Dict[KnowledgeType, Set[str]] = {}

        # Load existing entries
        if self.storage_path.exists():
            self._load_entries()

    def add_entry(
        self,
        entry_id: str,
        title: str,
        type: KnowledgeType,
        content: str,
        tags: List[str],
        language: Optional[str] = None,
        severity: Optional[Severity] = None,
        examples: Optional[List[Dict[str, str]]] = None,
        related_entries: Optional[List[str]] = None,
        references: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> KnowledgeEntry:
        """Add a new knowledge entry."""
        if entry_id in self.entries:
            raise ValueError(f"Entry {entry_id} already exists")

        entry = KnowledgeEntry(
            id=entry_id,
            title=title,
            type=type,
            content=content,
            tags=tags,
            language=language,
            severity=severity,
            examples=examples or [],
            related_entries=related_entries or [],
            references=references or [],
            metadata=metadata or {}
        )

        self.entries[entry_id] = entry
        self._update_indexes(entry)
        self._save_entry(entry)

        return entry

    def get_entry(self, entry_id: str) -> Optional[KnowledgeEntry]:
        """Get an entry by ID."""
        entry = self.entries.get(entry_id)
        if entry:
            entry.view_count += 1
            self._save_entry(entry)
        return entry

    def update_entry(
        self,
        entry_id: str,
        title: Optional[str] = None,
        content: Optional[str] = None,
        tags: Optional[List[str]] = None,
        language: Optional[str] = None,
        severity: Optional[Severity] = None,
        examples: Optional[List[Dict[str, str]]] = None,
        related_entries: Optional[List[str]] = None,
        references: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> KnowledgeEntry:
        """Update an existing entry."""
        entry = self.entries.get(entry_id)
        if not entry:
            raise ValueError(f"Entry {entry_id} not found")

        # Remove from old indexes
        self._remove_from_indexes(entry)

        # Update fields
        if title is not None:
            entry.title = title
        if content is not None:
            entry.content = content
        if tags is not None:
            entry.tags = tags
        if language is not None:
            entry.language = language
        if severity is not None:
            entry.severity = severity
        if examples is not None:
            entry.examples = examples
        if related_entries is not None:
            entry.related_entries = related_entries
        if references is not None:
            entry.references = references
        if metadata is not None:
            entry.metadata.update(metadata)

        entry.updated_at = datetime.now(timezone.utc)

        # Update indexes
        self._update_indexes(entry)
        self._save_entry(entry)

        return entry

    def delete_entry(self, entry_id: str) -> bool:
        """Delete an entry."""
        entry = self.entries.get(entry_id)
        if not entry:
            return False

        self._remove_from_indexes(entry)
        del self.entries[entry_id]

        # Delete file
        entry_file = self.storage_path / f"{entry_id}.json"
        if entry_file.exists():
            entry_file.unlink()

        return True

    def search(
        self,
        query: str,
        type: Optional[KnowledgeType] = None,
        tags: Optional[List[str]] = None,
        language: Optional[str] = None,
        limit: int = 10
    ) -> List[SearchResult]:
        """Search knowledge base."""
        results = []
        query_lower = query.lower()

        # Filter by type, tags, language
        candidate_ids = set(self.entries.keys())

        if type:
            candidate_ids &= self.type_index.get(type, set())

        if tags:
            for tag in tags:
                candidate_ids &= self.tag_index.get(tag, set())

        if language:
            candidate_ids &= self.language_index.get(language, set())

        # Score candidates
        for entry_id in candidate_ids:
            entry = self.entries[entry_id]
            score = 0.0
            matched_fields = []

            # Title match (highest weight)
            if query_lower in entry.title.lower():
                score += 10.0
                matched_fields.append("title")

            # Content match
            if query_lower in entry.content.lower():
                score += 5.0
                matched_fields.append("content")

            # Tag match
            for tag in entry.tags:
                if query_lower in tag.lower():
                    score += 3.0
                    matched_fields.append("tags")
                    break

            # Example match
            for example in entry.examples:
                if any(query_lower in str(v).lower() for v in example.values()):
                    score += 2.0
                    matched_fields.append("examples")
                    break

            # Boost by popularity
            score += entry.view_count * 0.01
            score += entry.helpful_count * 0.1

            if score > 0:
                results.append(SearchResult(
                    entry=entry,
                    relevance_score=score,
                    matched_fields=matched_fields
                ))

        # Sort by relevance
        results.sort(key=lambda r: r.relevance_score, reverse=True)

        return results[:limit]

    def get_by_tags(self, tags: List[str]) -> List[KnowledgeEntry]:
        """Get entries by tags."""
        entry_ids = set(self.entries.keys())
        for tag in tags:
            entry_ids &= self.tag_index.get(tag, set())

        return [self.entries[eid] for eid in entry_ids]

    def get_by_type(self, type: KnowledgeType) -> List[KnowledgeEntry]:
        """Get entries by type."""
        entry_ids = self.type_index.get(type, set())
        return [self.entries[eid] for eid in entry_ids]

    def get_by_language(self, language: str) -> List[KnowledgeEntry]:
        """Get entries by language."""
        entry_ids = self.language_index.get(language, set())
        return [self.entries[eid] for eid in entry_ids]

    def get_related(self, entry_id: str, limit: int = 5) -> List[KnowledgeEntry]:
        """Get related entries."""
        entry = self.entries.get(entry_id)
        if not entry:
            return []

        # Get explicitly related entries
        related = []
        for rel_id in entry.related_entries:
            if rel_id in self.entries:
                related.append(self.entries[rel_id])

        # Find similar entries by tags
        if len(related) < limit:
            similar = self.get_by_tags(entry.tags)
            for sim_entry in similar:
                if sim_entry.id != entry_id and sim_entry not in related:
                    related.append(sim_entry)
                    if len(related) >= limit:
                        break

        return related[:limit]

    def mark_helpful(self, entry_id: str) -> bool:
        """Mark an entry as helpful."""
        entry = self.entries.get(entry_id)
        if not entry:
            return False

        entry.helpful_count += 1
        self._save_entry(entry)
        return True

    def get_popular(self, limit: int = 10) -> List[KnowledgeEntry]:
        """Get most popular entries."""
        entries = list(self.entries.values())
        entries.sort(key=lambda e: (e.helpful_count, e.view_count), reverse=True)
        return entries[:limit]

    def get_recent(self, limit: int = 10) -> List[KnowledgeEntry]:
        """Get most recent entries."""
        entries = list(self.entries.values())
        entries.sort(key=lambda e: e.created_at, reverse=True)
        return entries[:limit]

    def get_statistics(self) -> Dict[str, Any]:
        """Get knowledge base statistics."""
        return {
            "total_entries": len(self.entries),
            "by_type": {
                type.value: len(self.type_index.get(type, set()))
                for type in KnowledgeType
            },
            "by_language": {
                lang: len(entry_ids)
                for lang, entry_ids in self.language_index.items()
            },
            "total_tags": len(self.tag_index),
            "total_views": sum(e.view_count for e in self.entries.values()),
            "total_helpful": sum(e.helpful_count for e in self.entries.values())
        }

    def export_data(self) -> Dict[str, Any]:
        """Export all data."""
        return {
            "entries": [
                self._entry_to_dict(entry)
                for entry in self.entries.values()
            ],
            "statistics": self.get_statistics()
        }

    def import_data(self, data: Dict[str, Any]):
        """Import data."""
        for entry_data in data.get("entries", []):
            entry = self._dict_to_entry(entry_data)
            self.entries[entry.id] = entry
            self._update_indexes(entry)
            self._save_entry(entry)

    def _update_indexes(self, entry: KnowledgeEntry):
        """Update indexes for an entry."""
        # Tag index
        for tag in entry.tags:
            if tag not in self.tag_index:
                self.tag_index[tag] = set()
            self.tag_index[tag].add(entry.id)

        # Language index
        if entry.language:
            if entry.language not in self.language_index:
                self.language_index[entry.language] = set()
            self.language_index[entry.language].add(entry.id)

        # Type index
        if entry.type not in self.type_index:
            self.type_index[entry.type] = set()
        self.type_index[entry.type].add(entry.id)

    def _remove_from_indexes(self, entry: KnowledgeEntry):
        """Remove entry from indexes."""
        # Tag index
        for tag in entry.tags:
            if tag in self.tag_index:
                self.tag_index[tag].discard(entry.id)

        # Language index
        if entry.language and entry.language in self.language_index:
            self.language_index[entry.language].discard(entry.id)

        # Type index
        if entry.type in self.type_index:
            self.type_index[entry.type].discard(entry.id)

    def _save_entry(self, entry: KnowledgeEntry):
        """Save entry to disk."""
        self.storage_path.mkdir(parents=True, exist_ok=True)
        entry_file = self.storage_path / f"{entry.id}.json"

        with open(entry_file, 'w', encoding='utf-8') as f:
            json.dump(self._entry_to_dict(entry), f, indent=2, ensure_ascii=False)

    def _load_entries(self):
        """Load entries from disk."""
        for entry_file in self.storage_path.glob("*.json"):
            try:
                with open(entry_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    entry = self._dict_to_entry(data)
                    self.entries[entry.id] = entry
                    self._update_indexes(entry)
            except Exception:
                pass

    def _entry_to_dict(self, entry: KnowledgeEntry) -> Dict[str, Any]:
        """Convert entry to dictionary."""
        return {
            "id": entry.id,
            "title": entry.title,
            "type": entry.type.value,
            "content": entry.content,
            "tags": entry.tags,
            "language": entry.language,
            "severity": entry.severity.value if entry.severity else None,
            "examples": entry.examples,
            "related_entries": entry.related_entries,
            "references": entry.references,
            "created_at": entry.created_at.isoformat(),
            "updated_at": entry.updated_at.isoformat(),
            "view_count": entry.view_count,
            "helpful_count": entry.helpful_count,
            "metadata": entry.metadata
        }

    def _dict_to_entry(self, data: Dict[str, Any]) -> KnowledgeEntry:
        """Convert dictionary to entry."""
        return KnowledgeEntry(
            id=data["id"],
            title=data["title"],
            type=KnowledgeType(data["type"]),
            content=data["content"],
            tags=data["tags"],
            language=data.get("language"),
            severity=Severity(data["severity"]) if data.get("severity") else None,
            examples=data.get("examples", []),
            related_entries=data.get("related_entries", []),
            references=data.get("references", []),
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"]),
            view_count=data.get("view_count", 0),
            helpful_count=data.get("helpful_count", 0),
            metadata=data.get("metadata", {})
        )
