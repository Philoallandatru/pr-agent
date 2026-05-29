"""
Database Schema and ORM for PR-Agent Web Platform

SQLite database for storing repositories, PR reviews, prompts, and logs.
"""

import json
import sqlite3
from pathlib import Path
from typing import Dict, List, Optional

from pr_agent.config_loader import get_settings


class Database:
    """Database manager for PR-Agent web platform"""

    def __init__(self, db_path: Optional[str] = None):
        """
        Initialize database connection

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path or get_settings().get(
            "web_platform.database_path",
            "pr_agent.db"
        )
        self.db_path = Path(self.db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        self.conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._create_tables()

    def _create_tables(self):
        """Create database tables if they don't exist"""
        cursor = self.conn.cursor()

        # Repositories table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS repositories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_key TEXT NOT NULL,
                repo_slug TEXT NOT NULL,
                polling_enabled BOOLEAN DEFAULT 1,
                polling_interval INTEGER DEFAULT 300,
                custom_prompts TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(project_key, repo_slug)
            )
        """)

        # PR reviews table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS pr_reviews (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                repository_id INTEGER NOT NULL,
                pr_id INTEGER NOT NULL,
                pr_title TEXT,
                pr_author TEXT,
                pr_url TEXT,
                commands_run TEXT,
                review_result TEXT,
                status TEXT DEFAULT 'pending',
                error_message TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP,
                FOREIGN KEY(repository_id) REFERENCES repositories(id) ON DELETE CASCADE
            )
        """)

        # System logs table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS system_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                level TEXT NOT NULL,
                message TEXT NOT NULL,
                details TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Prompt templates table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS prompt_templates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                repository_id INTEGER,
                command TEXT NOT NULL,
                template TEXT NOT NULL,
                is_active BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(repository_id) REFERENCES repositories(id) ON DELETE CASCADE
            )
        """)

        # Efficiency metrics table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS efficiency_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pr_review_id INTEGER NOT NULL,

                issues_found_total INTEGER DEFAULT 0,
                issues_high_severity INTEGER DEFAULT 0,
                issues_medium_severity INTEGER DEFAULT 0,
                issues_low_severity INTEGER DEFAULT 0,
                security_issues_found INTEGER DEFAULT 0,
                code_suggestions_count INTEGER DEFAULT 0,

                estimated_review_effort INTEGER,
                review_response_time_seconds REAL,
                review_processing_time_seconds REAL NOT NULL,
                estimated_human_time_saved_minutes REAL,

                tokens_prompt INTEGER DEFAULT 0,
                tokens_completion INTEGER DEFAULT 0,
                tokens_total INTEGER DEFAULT 0,
                api_calls_count INTEGER DEFAULT 0,
                api_cost_usd REAL,

                pr_size_lines INTEGER DEFAULT 0,
                pr_files_count INTEGER DEFAULT 0,
                pr_languages TEXT,
                pr_complexity_score REAL,

                model_used TEXT,
                review_type TEXT,
                agentic_search_iterations INTEGER DEFAULT 0,

                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

                FOREIGN KEY(pr_review_id) REFERENCES pr_reviews(id) ON DELETE CASCADE
            )
        """)

        # Create indexes
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_pr_reviews_repo
            ON pr_reviews(repository_id)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_pr_reviews_status
            ON pr_reviews(status)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_system_logs_timestamp
            ON system_logs(timestamp)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_efficiency_metrics_pr_review
            ON efficiency_metrics(pr_review_id)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_efficiency_metrics_created_at
            ON efficiency_metrics(created_at)
        """)

        self.conn.commit()

    # Repository operations
    def add_repository(
        self,
        project_key: str,
        repo_slug: str,
        polling_enabled: bool = True,
        polling_interval: int = 300,
        custom_prompts: Optional[Dict] = None
    ) -> int:
        """Add a new repository"""
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO repositories (project_key, repo_slug, polling_enabled, polling_interval, custom_prompts)
            VALUES (?, ?, ?, ?, ?)
        """, (
            project_key,
            repo_slug,
            polling_enabled,
            polling_interval,
            json.dumps(custom_prompts) if custom_prompts else None
        ))
        self.conn.commit()
        return cursor.lastrowid

    def get_repository(self, repo_id: int) -> Optional[Dict]:
        """Get repository by ID"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM repositories WHERE id = ?", (repo_id,))
        row = cursor.fetchone()
        return dict(row) if row else None

    def get_all_repositories(self) -> List[Dict]:
        """Get all repositories"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM repositories ORDER BY created_at DESC")
        return [dict(row) for row in cursor.fetchall()]

    def update_repository(
        self,
        repo_id: int,
        polling_enabled: Optional[bool] = None,
        polling_interval: Optional[int] = None,
        custom_prompts: Optional[Dict] = None
    ):
        """Update repository settings"""
        updates = []
        params = []

        if polling_enabled is not None:
            updates.append("polling_enabled = ?")
            params.append(polling_enabled)
        if polling_interval is not None:
            updates.append("polling_interval = ?")
            params.append(polling_interval)
        if custom_prompts is not None:
            updates.append("custom_prompts = ?")
            params.append(json.dumps(custom_prompts))

        if updates:
            updates.append("updated_at = CURRENT_TIMESTAMP")
            params.append(repo_id)

            cursor = self.conn.cursor()
            cursor.execute(f"""
                UPDATE repositories
                SET {', '.join(updates)}
                WHERE id = ?
            """, params)
            self.conn.commit()

    def delete_repository(self, repo_id: int):
        """Delete repository"""
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM repositories WHERE id = ?", (repo_id,))
        self.conn.commit()

    # PR review operations
    def add_pr_review(
        self,
        repository_id: int,
        pr_id: int,
        pr_title: str,
        pr_author: str,
        pr_url: str,
        commands_run: List[str],
        status: str = "pending"
    ) -> int:
        """Add a new PR review record"""
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO pr_reviews
            (repository_id, pr_id, pr_title, pr_author, pr_url, commands_run, status)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            repository_id,
            pr_id,
            pr_title,
            pr_author,
            pr_url,
            json.dumps(commands_run),
            status
        ))
        self.conn.commit()
        return cursor.lastrowid

    def update_pr_review(
        self,
        review_id: int,
        status: Optional[str] = None,
        review_result: Optional[Dict] = None,
        error_message: Optional[str] = None
    ):
        """Update PR review status and results"""
        updates = []
        params = []

        if status is not None:
            updates.append("status = ?")
            params.append(status)
        if review_result is not None:
            updates.append("review_result = ?")
            params.append(json.dumps(review_result))
        if error_message is not None:
            updates.append("error_message = ?")
            params.append(error_message)

        if status in ["completed", "failed"]:
            updates.append("completed_at = CURRENT_TIMESTAMP")

        if updates:
            params.append(review_id)
            cursor = self.conn.cursor()
            cursor.execute(f"""
                UPDATE pr_reviews
                SET {', '.join(updates)}
                WHERE id = ?
            """, params)
            self.conn.commit()

    def get_pr_review(self, review_id: int) -> Optional[Dict]:
        """Get PR review by ID"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM pr_reviews WHERE id = ?", (review_id,))
        row = cursor.fetchone()
        return dict(row) if row else None

    def get_pr_reviews(
        self,
        repository_id: Optional[int] = None,
        status: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict]:
        """Get PR reviews with filters"""
        query = "SELECT * FROM pr_reviews WHERE 1=1"
        params = []

        if repository_id is not None:
            query += " AND repository_id = ?"
            params.append(repository_id)
        if status is not None:
            query += " AND status = ?"
            params.append(status)

        query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        cursor = self.conn.cursor()
        cursor.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]

    def is_pr_reviewed(self, pr_url: str) -> bool:
        """Check if a PR has already been reviewed"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT COUNT(*) as count FROM pr_reviews
            WHERE pr_url = ? AND status = 'completed'
        """, (pr_url,))
        result = cursor.fetchone()
        return result['count'] > 0

    def get_pr_review_by_url(self, pr_url: str) -> Optional[Dict]:
        """Get PR review by URL"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT * FROM pr_reviews
            WHERE pr_url = ?
            ORDER BY created_at DESC
            LIMIT 1
        """, (pr_url,))
        row = cursor.fetchone()
        return dict(row) if row else None

    # System logs operations
    def add_log(self, level: str, message: str, details: Optional[Dict] = None):
        """Add system log entry"""
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO system_logs (level, message, details)
            VALUES (?, ?, ?)
        """, (level, message, json.dumps(details) if details else None))
        self.conn.commit()

    def get_logs(
        self,
        level: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict]:
        """Get system logs"""
        query = "SELECT * FROM system_logs WHERE 1=1"
        params = []

        if level is not None:
            query += " AND level = ?"
            params.append(level)

        query += " ORDER BY timestamp DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        cursor = self.conn.cursor()
        cursor.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]

    # Prompt template operations
    def add_prompt_template(
        self,
        command: str,
        template: str,
        repository_id: Optional[int] = None,
        is_active: bool = True
    ) -> int:
        """Add prompt template"""
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO prompt_templates (repository_id, command, template, is_active)
            VALUES (?, ?, ?, ?)
        """, (repository_id, command, template, is_active))
        self.conn.commit()
        return cursor.lastrowid

    def get_prompt_templates(
        self,
        repository_id: Optional[int] = None,
        command: Optional[str] = None
    ) -> List[Dict]:
        """Get prompt templates"""
        query = "SELECT * FROM prompt_templates WHERE 1=1"
        params = []

        if repository_id is not None:
            query += " AND repository_id = ?"
            params.append(repository_id)
        if command is not None:
            query += " AND command = ?"
            params.append(command)

        query += " ORDER BY created_at DESC"

        cursor = self.conn.cursor()
        cursor.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]

    def update_prompt_template(
        self,
        template_id: int,
        template: Optional[str] = None,
        is_active: Optional[bool] = None
    ):
        """Update prompt template"""
        updates = []
        params = []

        if template is not None:
            updates.append("template = ?")
            params.append(template)
        if is_active is not None:
            updates.append("is_active = ?")
            params.append(is_active)

        if updates:
            updates.append("updated_at = CURRENT_TIMESTAMP")
            params.append(template_id)

            cursor = self.conn.cursor()
            cursor.execute(f"""
                UPDATE prompt_templates
                SET {', '.join(updates)}
                WHERE id = ?
            """, params)
            self.conn.commit()

    def delete_prompt_template(self, template_id: int):
        """Delete prompt template"""
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM prompt_templates WHERE id = ?", (template_id,))
        self.conn.commit()

    # Efficiency metrics operations
    def add_efficiency_metrics(
        self,
        pr_review_id: int,
        metrics: Dict
    ) -> int:
        """Add efficiency metrics record"""
        cursor = self.conn.cursor()

        # 构建字段和值列表
        fields = ['pr_review_id']
        values = [pr_review_id]
        placeholders = ['?']

        for key, value in metrics.items():
            fields.append(key)
            values.append(value)
            placeholders.append('?')

        query = f"""
            INSERT INTO efficiency_metrics ({', '.join(fields)})
            VALUES ({', '.join(placeholders)})
        """

        cursor.execute(query, values)
        self.conn.commit()
        return cursor.lastrowid

    def get_efficiency_metrics(
        self,
        pr_review_id: Optional[int] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict]:
        """Get efficiency metrics with filters"""
        query = "SELECT * FROM efficiency_metrics WHERE 1=1"
        params = []

        if pr_review_id is not None:
            query += " AND pr_review_id = ?"
            params.append(pr_review_id)

        query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        cursor = self.conn.cursor()
        cursor.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]

    # Statistics
    def get_statistics(self) -> Dict:
        """Get platform statistics"""
        cursor = self.conn.cursor()

        # Total repositories
        cursor.execute("SELECT COUNT(*) as count FROM repositories")
        total_repos = cursor.fetchone()['count']

        # Total reviews
        cursor.execute("SELECT COUNT(*) as count FROM pr_reviews")
        total_reviews = cursor.fetchone()['count']

        # Reviews by status
        cursor.execute("""
            SELECT status, COUNT(*) as count
            FROM pr_reviews
            GROUP BY status
        """)
        reviews_by_status = {row['status']: row['count'] for row in cursor.fetchall()}

        # Recent reviews (last 24h)
        cursor.execute("""
            SELECT COUNT(*) as count
            FROM pr_reviews
            WHERE created_at > datetime('now', '-1 day')
        """)
        recent_reviews = cursor.fetchone()['count']

        return {
            'total_repositories': total_repos,
            'total_reviews': total_reviews,
            'reviews_by_status': reviews_by_status,
            'recent_reviews_24h': recent_reviews
        }

    def close(self):
        """Close database connection"""
        self.conn.close()
