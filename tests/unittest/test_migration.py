"""
Unit tests for database migration system.
"""

import pytest
import sqlite3
import tempfile
from pathlib import Path
from pr_agent.storage.migration import Migration, MigrationManager


class DummyMigration(Migration):
    """Dummy migration class for testing."""

    def __init__(self):
        super().__init__(
            version="20260101000001",
            description="Test migration"
        )

    def up(self, conn: sqlite3.Connection):
        conn.execute("CREATE TABLE test_table (id INTEGER PRIMARY KEY, name TEXT)")

    def down(self, conn: sqlite3.Connection):
        conn.execute("DROP TABLE IF EXISTS test_table")


class TestMigrationManager:
    """Test MigrationManager functionality."""

    @pytest.fixture
    def temp_db(self):
        """Create temporary database."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        yield db_path
        Path(db_path).unlink(missing_ok=True)

    @pytest.fixture
    def temp_migrations_dir(self):
        """Create temporary migrations directory."""
        import tempfile
        import shutil
        temp_dir = Path(tempfile.mkdtemp())
        yield temp_dir
        # Cleanup - use shutil for better Windows compatibility
        try:
            shutil.rmtree(temp_dir, ignore_errors=True)
        except:
            pass

    @pytest.fixture
    def manager(self, temp_db, temp_migrations_dir):
        """Create migration manager with isolated environment."""
        mgr = MigrationManager(db_path=temp_db)
        mgr.migrations_dir = temp_migrations_dir
        return mgr

    def test_ensure_migrations_table(self, manager, temp_db):
        """Test migrations table creation."""
        conn = sqlite3.connect(temp_db)
        try:
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='schema_migrations'"
            )
            assert cursor.fetchone() is not None
        finally:
            conn.close()

    def test_get_applied_migrations_empty(self, manager):
        """Test getting applied migrations when none exist."""
        applied = manager.get_applied_migrations()
        assert applied == []

    def test_status_initial(self, manager):
        """Test status with no migrations."""
        status = manager.status()
        assert status['applied_count'] == 0
        assert status['current_version'] is None
        assert status['applied'] == []

    def test_create_migration(self, manager):
        """Test creating a new migration file."""
        filepath = manager.create_migration("Add test column")

        assert filepath.exists()
        assert filepath.suffix == ".py"
        assert "add_test_column" in filepath.name

        # Check file content
        content = filepath.read_text()
        assert "Add test column" in content
        assert "def up(self, conn: sqlite3.Connection):" in content
        assert "def down(self, conn: sqlite3.Connection):" in content

        # Cleanup
        filepath.unlink()

    def test_migrate_up(self, manager, temp_db):
        """Test applying migrations."""
        # Create test migration file
        migration_file = manager.migrations_dir / "20260101000001_test.py"
        migration_file.write_text("""
from pr_agent.storage.migration import Migration
import sqlite3

class Migration20260101000001(Migration):
    def __init__(self):
        super().__init__("20260101000001", "Test migration")

    def up(self, conn: sqlite3.Connection):
        conn.execute("CREATE TABLE test_table (id INTEGER PRIMARY KEY)")

    def down(self, conn: sqlite3.Connection):
        conn.execute("DROP TABLE IF EXISTS test_table")
""")

        # Apply migration
        manager.migrate()

        # Check migration was applied
        applied = manager.get_applied_migrations()
        assert "20260101000001" in applied

        # Check table was created
        conn = sqlite3.connect(temp_db)
        try:
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='test_table'"
            )
            assert cursor.fetchone() is not None
        finally:
            conn.close()

    def test_rollback(self, manager, temp_db):
        """Test rolling back migrations."""
        # Create and apply test migration
        migration_file = manager.migrations_dir / "20260101000001_test.py"
        migration_file.write_text("""
from pr_agent.storage.migration import Migration
import sqlite3

class Migration20260101000001(Migration):
    def __init__(self):
        super().__init__("20260101000001", "Test migration")

    def up(self, conn: sqlite3.Connection):
        conn.execute("CREATE TABLE test_table (id INTEGER PRIMARY KEY)")

    def down(self, conn: sqlite3.Connection):
        conn.execute("DROP TABLE IF EXISTS test_table")
""")

        # Apply migration
        manager.migrate()

        # Rollback migration
        manager.rollback()

        # Check migration was removed
        applied = manager.get_applied_migrations()
        assert "20260101000001" not in applied

        # Check table was dropped
        conn = sqlite3.connect(temp_db)
        try:
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='test_table'"
            )
            assert cursor.fetchone() is None
        finally:
            conn.close()

    def test_status_with_migrations(self, manager):
        """Test status with applied and pending migrations."""
        # Create test migration
        migration_file = manager.migrations_dir / "20260101000001_test.py"
        migration_file.write_text("""
from pr_agent.storage.migration import Migration
import sqlite3

class Migration20260101000001(Migration):
    def __init__(self):
        super().__init__("20260101000001", "Test migration")

    def up(self, conn: sqlite3.Connection):
        pass

    def down(self, conn: sqlite3.Connection):
        pass
""")

        # Apply migration
        manager.migrate()

        # Check status
        status = manager.status()
        assert status['applied_count'] == 1
        assert status['pending_count'] == 0
        assert status['current_version'] == "20260101000001"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

    def test_ensure_migrations_table(self, manager, temp_db):
        """Test migrations table creation."""
        conn = sqlite3.connect(temp_db)
        try:
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='schema_migrations'"
            )
            assert cursor.fetchone() is not None
        finally:
            conn.close()

    def test_get_applied_migrations_empty(self, manager):
        """Test getting applied migrations when none exist."""
        applied = manager.get_applied_migrations()
        assert applied == []

    def test_status_initial(self, manager):
        """Test status with no migrations."""
        status = manager.status()
        assert status['applied_count'] == 0
        assert status['current_version'] is None
        assert status['applied'] == []

    def test_create_migration(self, manager):
        """Test creating a new migration file."""
        filepath = manager.create_migration("Add test column")

        assert filepath.exists()
        assert filepath.suffix == ".py"
        assert "add_test_column" in filepath.name

        # Check file content
        content = filepath.read_text()
        assert "Add test column" in content
        assert "def up(self, conn: sqlite3.Connection):" in content
        assert "def down(self, conn: sqlite3.Connection):" in content

        # Cleanup
        filepath.unlink()

    def test_migrate_up(self, manager, temp_db):
        """Test applying migrations."""
        # Create test migration file
        migration_file = manager.migrations_dir / "20260101000001_test.py"
        migration_file.write_text("""
from pr_agent.storage.migration import Migration
import sqlite3

class Migration20260101000001(Migration):
    def __init__(self):
        super().__init__("20260101000001", "Test migration")

    def up(self, conn: sqlite3.Connection):
        conn.execute("CREATE TABLE test_table (id INTEGER PRIMARY KEY)")

    def down(self, conn: sqlite3.Connection):
        conn.execute("DROP TABLE IF EXISTS test_table")
""")

        try:
            # Apply migration
            manager.migrate()

            # Check migration was applied
            applied = manager.get_applied_migrations()
            assert "20260101000001" in applied

            # Check table was created
            conn = sqlite3.connect(temp_db)
            try:
                cursor = conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name='test_table'"
                )
                assert cursor.fetchone() is not None
            finally:
                conn.close()

        finally:
            migration_file.unlink(missing_ok=True)

    def test_rollback(self, manager, temp_db):
        """Test rolling back migrations."""
        # Create and apply test migration
        migration_file = manager.migrations_dir / "20260101000001_test.py"
        migration_file.write_text("""
from pr_agent.storage.migration import Migration
import sqlite3

class Migration20260101000001(Migration):
    def __init__(self):
        super().__init__("20260101000001", "Test migration")

    def up(self, conn: sqlite3.Connection):
        conn.execute("CREATE TABLE test_table (id INTEGER PRIMARY KEY)")

    def down(self, conn: sqlite3.Connection):
        conn.execute("DROP TABLE IF EXISTS test_table")
""")

        try:
            # Apply migration
            manager.migrate()

            # Rollback migration
            manager.rollback()

            # Check migration was removed
            applied = manager.get_applied_migrations()
            assert "20260101000001" not in applied

            # Check table was dropped
            conn = sqlite3.connect(temp_db)
            try:
                cursor = conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name='test_table'"
                )
                assert cursor.fetchone() is None
            finally:
                conn.close()

        finally:
            migration_file.unlink(missing_ok=True)

    def test_status_with_migrations(self, manager):
        """Test status with applied and pending migrations."""
        # Create test migration
        migration_file = manager.migrations_dir / "20260101000001_test.py"
        migration_file.write_text("""
from pr_agent.storage.migration import Migration
import sqlite3

class Migration20260101000001(Migration):
    def __init__(self):
        super().__init__("20260101000001", "Test migration")

    def up(self, conn: sqlite3.Connection):
        pass

    def down(self, conn: sqlite3.Connection):
        pass
""")

        try:
            # Apply migration
            manager.migrate()

            # Check status
            status = manager.status()
            assert status['applied_count'] == 1
            assert status['pending_count'] == 0
            assert status['current_version'] == "20260101000001"

        finally:
            migration_file.unlink(missing_ok=True)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
