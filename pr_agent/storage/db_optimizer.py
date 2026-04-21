"""
Database Query Optimizer

Provides query optimization, caching, and performance monitoring for database operations.
"""

from typing import Dict, List, Optional, Any, Callable
from functools import wraps
import time
import sqlite3

from pr_agent.storage.cache import get_cache
from pr_agent.log import get_logger


class QueryOptimizer:
    """
    Database query optimizer with caching and performance monitoring.

    Features:
    - Query result caching
    - Query performance tracking
    - Automatic index suggestions
    - Connection pooling
    """

    def __init__(self, database):
        """
        Initialize query optimizer.

        Args:
            database: Database instance to optimize
        """
        self.db = database
        self.cache = get_cache()
        self.logger = get_logger()
        self._query_stats: Dict[str, Dict] = {}

    def cached_query(self, cache_key: str, ttl: int = 300):
        """
        Decorator for caching query results.

        Args:
            cache_key: Cache key prefix
            ttl: Time to live in seconds

        Example:
            @optimizer.cached_query("repo", ttl=600)
            def get_repository(self, repo_id):
                return self.db.get_repository(repo_id)
        """
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            def wrapper(*args, **kwargs):
                # Generate cache key from function and arguments
                key_parts = [cache_key, func.__name__]
                key_parts.extend(str(arg) for arg in args[1:])  # Skip self
                key_parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()))
                full_key = ":".join(key_parts)

                # Try cache first
                cached_result = self.cache.get(full_key)
                if cached_result is not None:
                    self.logger.debug(f"Cache hit for {full_key}")
                    return cached_result

                # Execute query
                start_time = time.time()
                result = func(*args, **kwargs)
                duration = time.time() - start_time

                # Track performance
                self._track_query(func.__name__, duration)

                # Cache result
                self.cache.set(full_key, result, ttl=ttl)

                return result

            return wrapper
        return decorator

    def _track_query(self, query_name: str, duration: float):
        """Track query performance statistics."""
        if query_name not in self._query_stats:
            self._query_stats[query_name] = {
                "count": 0,
                "total_time": 0,
                "min_time": float('inf'),
                "max_time": 0
            }

        stats = self._query_stats[query_name]
        stats["count"] += 1
        stats["total_time"] += duration
        stats["min_time"] = min(stats["min_time"], duration)
        stats["max_time"] = max(stats["max_time"], duration)

        # Log slow queries
        if duration > 1.0:
            self.logger.warning(f"Slow query detected: {query_name} took {duration:.2f}s")

    def get_query_stats(self) -> Dict[str, Any]:
        """Get query performance statistics."""
        stats = {}
        for query_name, data in self._query_stats.items():
            avg_time = data["total_time"] / data["count"] if data["count"] > 0 else 0
            stats[query_name] = {
                "count": data["count"],
                "avg_time": avg_time,
                "min_time": data["min_time"],
                "max_time": data["max_time"],
                "total_time": data["total_time"]
            }
        return stats

    def analyze_indexes(self) -> List[Dict]:
        """
        Analyze database and suggest missing indexes.

        Returns:
            List of index suggestions
        """
        suggestions = []
        cursor = self.db.conn.cursor()

        try:
            # Check for missing indexes on foreign keys
            cursor.execute("""
                SELECT name, sql FROM sqlite_master
                WHERE type='table' AND sql IS NOT NULL
            """)

            for row in cursor.fetchall():
                table_name = row[0]
                table_sql = row[1]

                # Check for foreign key columns without indexes
                if "FOREIGN KEY" in table_sql:
                    # Get existing indexes
                    cursor.execute(f"PRAGMA index_list({table_name})")
                    existing_indexes = {idx[1] for idx in cursor.fetchall()}

                    # Suggest indexes for foreign keys
                    if "repository_id" in table_sql and f"idx_{table_name}_repository" not in existing_indexes:
                        suggestions.append({
                            "table": table_name,
                            "column": "repository_id",
                            "reason": "Foreign key without index",
                            "sql": f"CREATE INDEX idx_{table_name}_repository ON {table_name}(repository_id)"
                        })

            # Check for frequently queried columns
            for query_name, stats in self._query_stats.items():
                if stats["count"] > 100 and stats["total_time"] / stats["count"] > 0.1:
                    suggestions.append({
                        "query": query_name,
                        "reason": f"Slow query executed {stats['count']} times",
                        "avg_time": stats["total_time"] / stats["count"]
                    })

        except Exception as e:
            self.logger.error(f"Error analyzing indexes: {e}")

        return suggestions

    def optimize_database(self):
        """Run database optimization commands."""
        cursor = self.db.conn.cursor()

        try:
            # Analyze database for query optimization
            cursor.execute("ANALYZE")

            # Vacuum to reclaim space and defragment
            cursor.execute("VACUUM")

            self.db.conn.commit()
            self.logger.info("Database optimization completed")

        except Exception as e:
            self.logger.error(f"Error optimizing database: {e}")

    def add_missing_indexes(self):
        """Add recommended indexes to improve query performance."""
        cursor = self.db.conn.cursor()

        try:
            # Additional indexes for common queries
            indexes = [
                # PR reviews indexes
                "CREATE INDEX IF NOT EXISTS idx_pr_reviews_pr_id ON pr_reviews(pr_id)",
                "CREATE INDEX IF NOT EXISTS idx_pr_reviews_created_at ON pr_reviews(created_at DESC)",
                "CREATE INDEX IF NOT EXISTS idx_pr_reviews_repo_status ON pr_reviews(repository_id, status)",

                # System logs indexes
                "CREATE INDEX IF NOT EXISTS idx_system_logs_level ON system_logs(level)",
                "CREATE INDEX IF NOT EXISTS idx_system_logs_level_timestamp ON system_logs(level, timestamp DESC)",

                # Prompt templates indexes
                "CREATE INDEX IF NOT EXISTS idx_prompt_templates_command ON prompt_templates(command)",
                "CREATE INDEX IF NOT EXISTS idx_prompt_templates_repo_command ON prompt_templates(repository_id, command)",
                "CREATE INDEX IF NOT EXISTS idx_prompt_templates_active ON prompt_templates(is_active)",

                # Repositories indexes
                "CREATE INDEX IF NOT EXISTS idx_repositories_polling ON repositories(polling_enabled)",
                "CREATE INDEX IF NOT EXISTS idx_repositories_project ON repositories(project_key)"
            ]

            for index_sql in indexes:
                cursor.execute(index_sql)

            self.db.conn.commit()
            self.logger.info(f"Added {len(indexes)} performance indexes")

        except Exception as e:
            self.logger.error(f"Error adding indexes: {e}")


class CachedDatabase:
    """
    Wrapper around Database class with automatic caching.

    Provides cached versions of common database queries.
    """

    def __init__(self, database):
        """
        Initialize cached database wrapper.

        Args:
            database: Database instance to wrap
        """
        self.db = database
        self.optimizer = QueryOptimizer(database)
        self.cache = get_cache()
        self.logger = get_logger()

        # Add performance indexes
        self.optimizer.add_missing_indexes()

    def get_repository(self, repo_id: int) -> Optional[Dict]:
        """Get repository by ID (cached)."""
        cache_key = f"repo:{repo_id}"

        cached = self.cache.get(cache_key)
        if cached:
            return cached

        result = self.db.get_repository(repo_id)
        if result:
            self.cache.set(cache_key, result, ttl=1800)  # 30 minutes

        return result

    def get_all_repositories(self) -> List[Dict]:
        """Get all repositories (cached)."""
        cache_key = "repos:all"

        cached = self.cache.get(cache_key)
        if cached:
            return cached

        result = self.db.get_all_repositories()
        self.cache.set(cache_key, result, ttl=300)  # 5 minutes

        return result

    def get_pr_reviews(
        self,
        repository_id: Optional[int] = None,
        status: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict]:
        """Get PR reviews with caching."""
        cache_key = f"reviews:{repository_id}:{status}:{limit}:{offset}"

        cached = self.cache.get(cache_key)
        if cached:
            return cached

        result = self.db.get_pr_reviews(repository_id, status, limit, offset)
        self.cache.set(cache_key, result, ttl=300)  # 5 minutes

        return result

    def get_statistics(self) -> Dict:
        """Get platform statistics (cached)."""
        cache_key = "stats:platform"

        cached = self.cache.get(cache_key)
        if cached:
            return cached

        result = self.db.get_statistics()
        self.cache.set(cache_key, result, ttl=60)  # 1 minute

        return result

    def invalidate_repository_cache(self, repo_id: int):
        """Invalidate cache for a repository."""
        self.cache.delete(f"repo:{repo_id}")
        self.cache.clear("repos:all")

    def invalidate_reviews_cache(self, repository_id: Optional[int] = None):
        """Invalidate cache for PR reviews."""
        if repository_id:
            self.cache.clear(f"reviews:{repository_id}:*")
        else:
            self.cache.clear("reviews:*")

    def invalidate_stats_cache(self):
        """Invalidate statistics cache."""
        self.cache.delete("stats:platform")

    # Delegate other methods to underlying database
    def __getattr__(self, name):
        """Delegate unknown methods to underlying database."""
        return getattr(self.db, name)
