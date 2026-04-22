"""
Migration: Initial schema
Version: 20260422000001
Created: 2026-04-22T00:00:01
"""

from pr_agent.storage.migration import Migration
import sqlite3


class Migration20260422000001(Migration):
    """
    Initial database schema for PR-Agent web platform.
    """

    def __init__(self):
        super().__init__(
            version="20260422000001",
            description="Initial schema"
        )

    def up(self, conn: sqlite3.Connection):
        """Apply the migration."""
        # Repositories table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS repositories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_key TEXT NOT NULL,
                repo_slug TEXT NOT NULL,
                name TEXT NOT NULL,
                url TEXT,
                enabled BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(project_key, repo_slug)
            )
        """)

        # PR reviews table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS pr_reviews (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                repository_id INTEGER NOT NULL,
                pr_number INTEGER NOT NULL,
                pr_title TEXT,
                pr_author TEXT,
                pr_url TEXT,
                review_status TEXT,
                review_result TEXT,
                commands TEXT,
                duration REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (repository_id) REFERENCES repositories(id),
                UNIQUE(repository_id, pr_number)
            )
        """)

        # Prompt templates table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS prompt_templates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                command TEXT NOT NULL,
                content TEXT NOT NULL,
                is_active BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # System logs table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS system_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                level TEXT NOT NULL,
                message TEXT NOT NULL,
                context TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Create indexes
        conn.execute("CREATE INDEX IF NOT EXISTS idx_repositories_enabled ON repositories(enabled)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_pr_reviews_repository ON pr_reviews(repository_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_pr_reviews_status ON pr_reviews(review_status)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_pr_reviews_created ON pr_reviews(created_at)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_system_logs_level ON system_logs(level)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_system_logs_created ON system_logs(created_at)")

    def down(self, conn: sqlite3.Connection):
        """Rollback the migration."""
        conn.execute("DROP TABLE IF EXISTS system_logs")
        conn.execute("DROP TABLE IF EXISTS prompt_templates")
        conn.execute("DROP TABLE IF EXISTS pr_reviews")
        conn.execute("DROP TABLE IF EXISTS repositories")
