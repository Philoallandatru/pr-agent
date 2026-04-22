"""Tests for knowledge base system."""

import pytest
import tempfile
from pathlib import Path
from pr_agent.knowledge import (
    KnowledgeBase,
    KnowledgeEntry,
    KnowledgeType,
    Severity
)


@pytest.fixture
def temp_storage():
    """Create temporary storage directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def kb(temp_storage):
    """Create knowledge base instance."""
    return KnowledgeBase(storage_path=temp_storage)


@pytest.fixture
def sample_entry_data():
    """Sample entry data."""
    return {
        "entry_id": "bp-001",
        "title": "Use meaningful variable names",
        "type": KnowledgeType.BEST_PRACTICE,
        "content": "Always use descriptive variable names that convey intent.",
        "tags": ["naming", "readability", "python"],
        "language": "python",
        "examples": [
            {
                "bad": "x = 10",
                "good": "max_retries = 10"
            }
        ]
    }


class TestKnowledgeEntry:
    """Test KnowledgeEntry dataclass."""

    def test_create_entry(self, sample_entry_data):
        """Test creating a knowledge entry."""
        entry = KnowledgeEntry(
            id=sample_entry_data["entry_id"],
            title=sample_entry_data["title"],
            type=sample_entry_data["type"],
            content=sample_entry_data["content"],
            tags=sample_entry_data["tags"]
        )

        assert entry.id == "bp-001"
        assert entry.title == "Use meaningful variable names"
        assert entry.type == KnowledgeType.BEST_PRACTICE
        assert len(entry.tags) == 3


class TestKnowledgeBase:
    """Test KnowledgeBase class."""

    def test_add_entry(self, kb, sample_entry_data):
        """Test adding an entry."""
        entry = kb.add_entry(**sample_entry_data)

        assert entry.id == "bp-001"
        assert entry.id in kb.entries
        assert len(kb.tag_index["python"]) == 1

    def test_add_duplicate_entry(self, kb, sample_entry_data):
        """Test adding duplicate entry raises error."""
        kb.add_entry(**sample_entry_data)

        with pytest.raises(ValueError, match="already exists"):
            kb.add_entry(**sample_entry_data)

    def test_get_entry(self, kb, sample_entry_data):
        """Test getting an entry."""
        kb.add_entry(**sample_entry_data)
        entry = kb.get_entry("bp-001")

        assert entry is not None
        assert entry.id == "bp-001"
        assert entry.view_count == 1

    def test_get_nonexistent_entry(self, kb):
        """Test getting nonexistent entry returns None."""
        entry = kb.get_entry("nonexistent")
        assert entry is None

    def test_update_entry(self, kb, sample_entry_data):
        """Test updating an entry."""
        kb.add_entry(**sample_entry_data)

        updated = kb.update_entry(
            "bp-001",
            title="Updated title",
            tags=["new-tag"]
        )

        assert updated.title == "Updated title"
        assert "new-tag" in updated.tags
        assert "new-tag" in kb.tag_index

    def test_update_nonexistent_entry(self, kb):
        """Test updating nonexistent entry raises error."""
        with pytest.raises(ValueError, match="not found"):
            kb.update_entry("nonexistent", title="New title")

    def test_delete_entry(self, kb, sample_entry_data):
        """Test deleting an entry."""
        kb.add_entry(**sample_entry_data)
        result = kb.delete_entry("bp-001")

        assert result is True
        assert "bp-001" not in kb.entries
        assert len(kb.tag_index.get("python", set())) == 0

    def test_delete_nonexistent_entry(self, kb):
        """Test deleting nonexistent entry returns False."""
        result = kb.delete_entry("nonexistent")
        assert result is False


class TestSearch:
    """Test search functionality."""

    def test_search_by_title(self, kb):
        """Test searching by title."""
        kb.add_entry(
            entry_id="bp-001",
            title="Use meaningful variable names",
            type=KnowledgeType.BEST_PRACTICE,
            content="Content here",
            tags=["naming"]
        )

        results = kb.search("variable names")

        assert len(results) == 1
        assert results[0].entry.id == "bp-001"
        assert "title" in results[0].matched_fields

    def test_search_by_content(self, kb):
        """Test searching by content."""
        kb.add_entry(
            entry_id="bp-001",
            title="Best Practice",
            type=KnowledgeType.BEST_PRACTICE,
            content="Always use descriptive variable names",
            tags=["naming"]
        )

        results = kb.search("descriptive")

        assert len(results) == 1
        assert "content" in results[0].matched_fields

    def test_search_by_tags(self, kb):
        """Test searching by tags."""
        kb.add_entry(
            entry_id="bp-001",
            title="Best Practice",
            type=KnowledgeType.BEST_PRACTICE,
            content="Content",
            tags=["python", "naming"]
        )

        results = kb.search("python")

        assert len(results) == 1
        assert "tags" in results[0].matched_fields

    def test_search_with_type_filter(self, kb):
        """Test searching with type filter."""
        kb.add_entry(
            entry_id="bp-001",
            title="Best Practice",
            type=KnowledgeType.BEST_PRACTICE,
            content="Content",
            tags=["python"]
        )
        kb.add_entry(
            entry_id="ap-001",
            title="Anti Pattern",
            type=KnowledgeType.ANTI_PATTERN,
            content="Content",
            tags=["python"]
        )

        results = kb.search("python", type=KnowledgeType.BEST_PRACTICE)

        assert len(results) == 1
        assert results[0].entry.type == KnowledgeType.BEST_PRACTICE

    def test_search_with_tags_filter(self, kb):
        """Test searching with tags filter."""
        kb.add_entry(
            entry_id="bp-001",
            title="Practice 1",
            type=KnowledgeType.BEST_PRACTICE,
            content="Content",
            tags=["python", "naming"]
        )
        kb.add_entry(
            entry_id="bp-002",
            title="Practice 2",
            type=KnowledgeType.BEST_PRACTICE,
            content="Content",
            tags=["python", "testing"]
        )

        results = kb.search("python", tags=["naming"])

        assert len(results) == 1
        assert results[0].entry.id == "bp-001"

    def test_search_with_language_filter(self, kb):
        """Test searching with language filter."""
        kb.add_entry(
            entry_id="bp-001",
            title="Python Practice",
            type=KnowledgeType.BEST_PRACTICE,
            content="Content",
            tags=["naming"],
            language="python"
        )
        kb.add_entry(
            entry_id="bp-002",
            title="Java Practice",
            type=KnowledgeType.BEST_PRACTICE,
            content="Content",
            tags=["naming"],
            language="java"
        )

        results = kb.search("Practice", language="python")

        assert len(results) == 1
        assert results[0].entry.language == "python"

    def test_search_limit(self, kb):
        """Test search result limit."""
        for i in range(20):
            kb.add_entry(
                entry_id=f"bp-{i:03d}",
                title=f"Practice {i}",
                type=KnowledgeType.BEST_PRACTICE,
                content="Common content",
                tags=["test"]
            )

        results = kb.search("Practice", limit=5)

        assert len(results) == 5

    def test_search_no_results(self, kb):
        """Test search with no results."""
        kb.add_entry(
            entry_id="bp-001",
            title="Best Practice",
            type=KnowledgeType.BEST_PRACTICE,
            content="Content",
            tags=["python"]
        )

        results = kb.search("nonexistent")

        assert len(results) == 0


class TestFiltering:
    """Test filtering methods."""

    def test_get_by_tags(self, kb):
        """Test getting entries by tags."""
        kb.add_entry(
            entry_id="bp-001",
            title="Practice 1",
            type=KnowledgeType.BEST_PRACTICE,
            content="Content",
            tags=["python", "naming"]
        )
        kb.add_entry(
            entry_id="bp-002",
            title="Practice 2",
            type=KnowledgeType.BEST_PRACTICE,
            content="Content",
            tags=["python", "testing"]
        )

        entries = kb.get_by_tags(["python", "naming"])

        assert len(entries) == 1
        assert entries[0].id == "bp-001"

    def test_get_by_type(self, kb):
        """Test getting entries by type."""
        kb.add_entry(
            entry_id="bp-001",
            title="Best Practice",
            type=KnowledgeType.BEST_PRACTICE,
            content="Content",
            tags=["python"]
        )
        kb.add_entry(
            entry_id="ap-001",
            title="Anti Pattern",
            type=KnowledgeType.ANTI_PATTERN,
            content="Content",
            tags=["python"]
        )

        entries = kb.get_by_type(KnowledgeType.BEST_PRACTICE)

        assert len(entries) == 1
        assert entries[0].type == KnowledgeType.BEST_PRACTICE

    def test_get_by_language(self, kb):
        """Test getting entries by language."""
        kb.add_entry(
            entry_id="bp-001",
            title="Python Practice",
            type=KnowledgeType.BEST_PRACTICE,
            content="Content",
            tags=["naming"],
            language="python"
        )
        kb.add_entry(
            entry_id="bp-002",
            title="Java Practice",
            type=KnowledgeType.BEST_PRACTICE,
            content="Content",
            tags=["naming"],
            language="java"
        )

        entries = kb.get_by_language("python")

        assert len(entries) == 1
        assert entries[0].language == "python"


class TestRelatedEntries:
    """Test related entries functionality."""

    def test_get_related_explicit(self, kb):
        """Test getting explicitly related entries."""
        kb.add_entry(
            entry_id="bp-001",
            title="Practice 1",
            type=KnowledgeType.BEST_PRACTICE,
            content="Content",
            tags=["python"],
            related_entries=["bp-002"]
        )
        kb.add_entry(
            entry_id="bp-002",
            title="Practice 2",
            type=KnowledgeType.BEST_PRACTICE,
            content="Content",
            tags=["python"]
        )

        related = kb.get_related("bp-001")

        assert len(related) >= 1
        assert any(e.id == "bp-002" for e in related)

    def test_get_related_by_tags(self, kb):
        """Test getting related entries by similar tags."""
        kb.add_entry(
            entry_id="bp-001",
            title="Practice 1",
            type=KnowledgeType.BEST_PRACTICE,
            content="Content",
            tags=["python", "naming"]
        )
        kb.add_entry(
            entry_id="bp-002",
            title="Practice 2",
            type=KnowledgeType.BEST_PRACTICE,
            content="Content",
            tags=["python", "naming"]
        )

        related = kb.get_related("bp-001")

        assert len(related) >= 1
        assert any(e.id == "bp-002" for e in related)

    def test_get_related_limit(self, kb):
        """Test related entries limit."""
        kb.add_entry(
            entry_id="bp-001",
            title="Practice 1",
            type=KnowledgeType.BEST_PRACTICE,
            content="Content",
            tags=["python"]
        )
        for i in range(10):
            kb.add_entry(
                entry_id=f"bp-{i+2:03d}",
                title=f"Practice {i+2}",
                type=KnowledgeType.BEST_PRACTICE,
                content="Content",
                tags=["python"]
            )

        related = kb.get_related("bp-001", limit=3)

        assert len(related) <= 3


class TestPopularityAndRecency:
    """Test popularity and recency features."""

    def test_mark_helpful(self, kb, sample_entry_data):
        """Test marking entry as helpful."""
        kb.add_entry(**sample_entry_data)
        result = kb.mark_helpful("bp-001")

        assert result is True
        entry = kb.get_entry("bp-001")
        assert entry.helpful_count == 1

    def test_mark_helpful_nonexistent(self, kb):
        """Test marking nonexistent entry as helpful."""
        result = kb.mark_helpful("nonexistent")
        assert result is False

    def test_get_popular(self, kb):
        """Test getting popular entries."""
        for i in range(5):
            kb.add_entry(
                entry_id=f"bp-{i:03d}",
                title=f"Practice {i}",
                type=KnowledgeType.BEST_PRACTICE,
                content="Content",
                tags=["test"]
            )
            # Mark some as helpful
            for _ in range(i):
                kb.mark_helpful(f"bp-{i:03d}")

        popular = kb.get_popular(limit=3)

        assert len(popular) == 3
        assert popular[0].helpful_count >= popular[1].helpful_count

    def test_get_recent(self, kb):
        """Test getting recent entries."""
        for i in range(5):
            kb.add_entry(
                entry_id=f"bp-{i:03d}",
                title=f"Practice {i}",
                type=KnowledgeType.BEST_PRACTICE,
                content="Content",
                tags=["test"]
            )

        recent = kb.get_recent(limit=3)

        assert len(recent) == 3


class TestStatistics:
    """Test statistics functionality."""

    def test_get_statistics(self, kb):
        """Test getting statistics."""
        kb.add_entry(
            entry_id="bp-001",
            title="Best Practice",
            type=KnowledgeType.BEST_PRACTICE,
            content="Content",
            tags=["python"],
            language="python"
        )
        kb.add_entry(
            entry_id="ap-001",
            title="Anti Pattern",
            type=KnowledgeType.ANTI_PATTERN,
            content="Content",
            tags=["java"],
            language="java"
        )

        stats = kb.get_statistics()

        assert stats["total_entries"] == 2
        assert stats["by_type"][KnowledgeType.BEST_PRACTICE.value] == 1
        assert stats["by_type"][KnowledgeType.ANTI_PATTERN.value] == 1
        assert "python" in stats["by_language"]
        assert stats["total_tags"] == 2


class TestImportExport:
    """Test import/export functionality."""

    def test_export_data(self, kb, sample_entry_data):
        """Test exporting data."""
        kb.add_entry(**sample_entry_data)
        data = kb.export_data()

        assert "entries" in data
        assert "statistics" in data
        assert len(data["entries"]) == 1

    def test_import_data(self, kb, temp_storage):
        """Test importing data."""
        # Create data to import
        data = {
            "entries": [
                {
                    "id": "bp-001",
                    "title": "Best Practice",
                    "type": "best_practice",
                    "content": "Content",
                    "tags": ["python"],
                    "language": "python",
                    "severity": None,
                    "examples": [],
                    "related_entries": [],
                    "references": [],
                    "created_at": "2024-01-01T00:00:00+00:00",
                    "updated_at": "2024-01-01T00:00:00+00:00",
                    "view_count": 0,
                    "helpful_count": 0,
                    "metadata": {}
                }
            ]
        }

        kb.import_data(data)

        assert len(kb.entries) == 1
        assert "bp-001" in kb.entries


class TestPersistence:
    """Test data persistence."""

    def test_entry_persisted_to_disk(self, kb, sample_entry_data):
        """Test that entries are saved to disk."""
        kb.add_entry(**sample_entry_data)

        entry_file = kb.storage_path / "bp-001.json"
        assert entry_file.exists()

    def test_load_entries_on_init(self, temp_storage, sample_entry_data):
        """Test loading entries on initialization."""
        # Create and populate first KB
        kb1 = KnowledgeBase(storage_path=temp_storage)
        kb1.add_entry(**sample_entry_data)

        # Create new KB with same storage
        kb2 = KnowledgeBase(storage_path=temp_storage)

        assert len(kb2.entries) == 1
        assert "bp-001" in kb2.entries
