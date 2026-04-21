"""
Database migration system for PR-Agent.

Provides version control for database schema changes.
"""

import os
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional
from pr_agent.config_loader import get_settings


class Migration:
    """Base class for database migrations."""

    def __init__(self, version: str, description: str):
        self.version = version
        self.description = description
        self.timestamp = datetime.now()

    def up(self, conn: sqlite3.Connection):
        """Apply the migration."""
        raise NotImplementedError

    def down(self, conn: sqlite3.Connection):
        """Rollback the migration."""
        raise NotImplementedError


class MigrationManager:
    """Manages database migrations."""

    def __init__(self, db_path: Optional[str] = None):
        if db_path is None:
            db_path = get_settings().get("WEB_PLATFORM.DATABASE_PATH", "pr_agent.db")
        self.db_path = db_path
        self.migrations_dir = Path(__file__).parent / "migrations"
        self.migrations_dir.mkdir(exist_ok=True)
        self._ensure_migrations_table()

    def _ensure_migrations_table(self):
        """Create migrations tracking table if it doesn't exist."""
        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    version TEXT PRIMARY KEY,
                    description TEXT NOT NULL,
                    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.commit()
        finally:
            conn.close()

    def get_applied_migrations(self) -> List[str]:
        """Get list of applied migration versions."""
        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.execute(
                "SELECT version FROM schema_migrations ORDER BY version"
            )
            return [row[0] for row in cursor.fetchall()]
        finally:
            conn.close()

    def get_pending_migrations(self) -> List[Migration]:
        """Get list of pending migrations."""
        applied = set(self.get_applied_migrations())
        all_migrations = self._discover_migrations()
        return [m for m in all_migrations if m.version not in applied]

    def _discover_migrations(self) -> List[Migration]:
        """Discover all migration files."""
        migrations = []

        # Import migration modules
        import importlib.util
        for file in sorted(self.migrations_dir.glob("*.py")):
            if file.name.startswith("_"):
                continue

            spec = importlib.util.spec_from_file_location(file.stem, file)
            if spec and spec.loader:
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)

                # Look for Migration class
                for attr_name in dir(module):
                    attr = getattr(module, attr_name)
                    if (isinstance(attr, type) and
                        issubclass(attr, Migration) and
                        attr is not Migration):
                        migrations.append(attr())

        return sorted(migrations, key=lambda m: m.version)

    def migrate(self, target_version: Optional[str] = None):
        """
        Apply pending migrations up to target version.

        Args:
            target_version: Version to migrate to (None = latest)
        """
        pending = self.get_pending_migrations()

        if target_version:
            pending = [m for m in pending if m.version <= target_version]

        if not pending:
            print("No pending migrations.")
            return

        conn = sqlite3.connect(self.db_path)
        try:
            for migration in pending:
                print(f"Applying migration {migration.version}: {migration.description}")

                # Apply migration
                migration.up(conn)

                # Record migration
                conn.execute(
                    "INSERT INTO schema_migrations (version, description) VALUES (?, ?)",
                    (migration.version, migration.description)
                )
                conn.commit()

                print(f"✓ Migration {migration.version} applied successfully")

        except Exception as e:
            conn.rollback()
            print(f"✗ Migration failed: {e}")
            raise
        finally:
            conn.close()

    def rollback(self, target_version: Optional[str] = None):
        """
        Rollback migrations to target version.

        Args:
            target_version: Version to rollback to (None = rollback one)
        """
        applied = self.get_applied_migrations()

        if not applied:
            print("No migrations to rollback.")
            return

        if target_version is None:
            # Rollback last migration
            to_rollback = [applied[-1]]
        else:
            # Rollback to target version
            to_rollback = [v for v in applied if v > target_version]

        if not to_rollback:
            print("No migrations to rollback.")
            return

        all_migrations = {m.version: m for m in self._discover_migrations()}
        conn = sqlite3.connect(self.db_path)

        try:
            for version in reversed(to_rollback):
                migration = all_migrations.get(version)
                if not migration:
                    print(f"Warning: Migration {version} not found, skipping rollback")
                    continue

                print(f"Rolling back migration {version}: {migration.description}")

                # Rollback migration
                migration.down(conn)

                # Remove migration record
                conn.execute(
                    "DELETE FROM schema_migrations WHERE version = ?",
                    (version,)
                )
                conn.commit()

                print(f"✓ Migration {version} rolled back successfully")

        except Exception as e:
            conn.rollback()
            print(f"✗ Rollback failed: {e}")
            raise
        finally:
            conn.close()

    def status(self) -> Dict[str, any]:
        """Get migration status."""
        applied = self.get_applied_migrations()
        pending = self.get_pending_migrations()

        return {
            "applied_count": len(applied),
            "pending_count": len(pending),
            "applied": applied,
            "pending": [{"version": m.version, "description": m.description}
                       for m in pending],
            "current_version": applied[-1] if applied else None
        }

    def create_migration(self, description: str) -> Path:
        """
        Create a new migration file.

        Args:
            description: Migration description

        Returns:
            Path to created migration file
        """
        # Generate version (timestamp-based)
        version = datetime.now().strftime("%Y%m%d%H%M%S")

        # Create filename
        filename = f"{version}_{description.lower().replace(' ', '_')}.py"
        filepath = self.migrations_dir / filename

        # Migration template
        template = f'''"""
Migration: {description}
Version: {version}
Created: {datetime.now().isoformat()}
"""

from pr_agent.storage.migration import Migration
import sqlite3


class Migration{version}(Migration):
    """
    {description}
    """

    def __init__(self):
        super().__init__(
            version="{version}",
            description="{description}"
        )

    def up(self, conn: sqlite3.Connection):
        """Apply the migration."""
        # TODO: Implement migration
        # Example:
        # conn.execute("""
        #     CREATE TABLE example (
        #         id INTEGER PRIMARY KEY,
        #         name TEXT NOT NULL
        #     )
        # """)
        pass

    def down(self, conn: sqlite3.Connection):
        """Rollback the migration."""
        # TODO: Implement rollback
        # Example:
        # conn.execute("DROP TABLE IF EXISTS example")
        pass
'''

        filepath.write_text(template)
        print(f"Created migration: {filepath}")
        return filepath


# CLI interface
def main():
    """CLI for database migrations."""
    import sys

    manager = MigrationManager()

    if len(sys.argv) < 2:
        print("Usage: python -m pr_agent.storage.migration <command> [args]")
        print("\nCommands:")
        print("  status              - Show migration status")
        print("  migrate [version]   - Apply pending migrations")
        print("  rollback [version]  - Rollback migrations")
        print("  create <description> - Create new migration")
        return

    command = sys.argv[1]

    if command == "status":
        status = manager.status()
        print(f"\nDatabase: {manager.db_path}")
        print(f"Current version: {status['current_version'] or 'None'}")
        print(f"Applied migrations: {status['applied_count']}")
        print(f"Pending migrations: {status['pending_count']}")

        if status['applied']:
            print("\nApplied:")
            for version in status['applied']:
                print(f"  ✓ {version}")

        if status['pending']:
            print("\nPending:")
            for migration in status['pending']:
                print(f"  • {migration['version']}: {migration['description']}")

    elif command == "migrate":
        target = sys.argv[2] if len(sys.argv) > 2 else None
        manager.migrate(target)

    elif command == "rollback":
        target = sys.argv[2] if len(sys.argv) > 2 else None
        manager.rollback(target)

    elif command == "create":
        if len(sys.argv) < 3:
            print("Error: Description required")
            print("Usage: python -m pr_agent.storage.migration create <description>")
            return
        description = " ".join(sys.argv[2:])
        manager.create_migration(description)

    else:
        print(f"Unknown command: {command}")


if __name__ == "__main__":
    main()
