"""
Database performance benchmarks.

Tests database query performance, connection pooling, and transaction throughput.
"""

import time
import statistics
import sqlite3
from typing import List, Dict, Any
from dataclasses import dataclass
from pathlib import Path
import tempfile
import json
from datetime import datetime


@dataclass
class DBBenchmarkResult:
    """Results from a database benchmark."""
    name: str
    operations: int
    duration: float
    ops_per_second: float
    mean_time: float
    median_time: float
    p95_time: float
    min_time: float
    max_time: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            'name': self.name,
            'operations': self.operations,
            'duration': self.duration,
            'ops_per_second': self.ops_per_second,
            'mean_time': self.mean_time,
            'median_time': self.median_time,
            'p95_time': self.p95_time,
            'min_time': self.min_time,
            'max_time': self.max_time
        }


class DatabaseBenchmark:
    """Benchmark suite for database operations."""

    def __init__(self, db_path: str = None):
        if db_path is None:
            self.temp_dir = tempfile.mkdtemp()
            self.db_path = str(Path(self.temp_dir) / "benchmark.db")
        else:
            self.db_path = db_path
            self.temp_dir = None

        self.results: List[DBBenchmarkResult] = []
        self._setup_database()

    def _setup_database(self):
        """Create test database schema."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Create test tables
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS repositories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                url TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS reviews (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                repository_id INTEGER NOT NULL,
                pr_number INTEGER NOT NULL,
                status TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (repository_id) REFERENCES repositories(id)
            )
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_reviews_repo
            ON reviews(repository_id)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_reviews_status
            ON reviews(status)
        """)

        conn.commit()
        conn.close()

    def _calculate_percentile(self, values: List[float], percentile: float) -> float:
        """Calculate percentile from a list of values."""
        if not values:
            return 0.0
        sorted_values = sorted(values)
        index = int(len(sorted_values) * percentile / 100)
        return sorted_values[min(index, len(sorted_values) - 1)]

    def benchmark_inserts(self, num_operations: int = 1000) -> DBBenchmarkResult:
        """Benchmark INSERT operations."""
        print(f"\nBenchmarking INSERT operations ({num_operations} ops)...")

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        times = []
        start_total = time.perf_counter()

        for i in range(num_operations):
            start = time.perf_counter()
            cursor.execute(
                "INSERT INTO repositories (name, url) VALUES (?, ?)",
                (f"repo_{i}", f"https://example.com/repo_{i}")
            )
            times.append(time.perf_counter() - start)

        conn.commit()
        duration = time.perf_counter() - start_total
        conn.close()

        result = DBBenchmarkResult(
            name="INSERT",
            operations=num_operations,
            duration=duration,
            ops_per_second=num_operations / duration,
            mean_time=statistics.mean(times),
            median_time=statistics.median(times),
            p95_time=self._calculate_percentile(times, 95),
            min_time=min(times),
            max_time=max(times)
        )

        self.results.append(result)
        self._print_result(result)
        return result

    def benchmark_batch_inserts(self, num_operations: int = 1000, batch_size: int = 100) -> DBBenchmarkResult:
        """Benchmark batch INSERT operations."""
        print(f"\nBenchmarking batch INSERT operations ({num_operations} ops, batch size {batch_size})...")

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        times = []
        start_total = time.perf_counter()

        for batch_start in range(0, num_operations, batch_size):
            batch_end = min(batch_start + batch_size, num_operations)
            batch_data = [
                (f"repo_batch_{i}", f"https://example.com/repo_batch_{i}")
                for i in range(batch_start, batch_end)
            ]

            start = time.perf_counter()
            cursor.executemany(
                "INSERT INTO repositories (name, url) VALUES (?, ?)",
                batch_data
            )
            conn.commit()
            times.append(time.perf_counter() - start)

        duration = time.perf_counter() - start_total
        conn.close()

        result = DBBenchmarkResult(
            name="Batch INSERT",
            operations=num_operations,
            duration=duration,
            ops_per_second=num_operations / duration,
            mean_time=statistics.mean(times),
            median_time=statistics.median(times),
            p95_time=self._calculate_percentile(times, 95),
            min_time=min(times),
            max_time=max(times)
        )

        self.results.append(result)
        self._print_result(result)
        return result

    def benchmark_selects(self, num_operations: int = 1000) -> DBBenchmarkResult:
        """Benchmark SELECT operations."""
        print(f"\nBenchmarking SELECT operations ({num_operations} ops)...")

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Ensure we have data
        cursor.execute("SELECT COUNT(*) FROM repositories")
        count = cursor.fetchone()[0]
        if count == 0:
            print("  No data found, inserting test data...")
            self.benchmark_inserts(1000)

        times = []
        start_total = time.perf_counter()

        for i in range(num_operations):
            start = time.perf_counter()
            cursor.execute("SELECT * FROM repositories WHERE id = ?", (i % count + 1,))
            cursor.fetchone()
            times.append(time.perf_counter() - start)

        duration = time.perf_counter() - start_total
        conn.close()

        result = DBBenchmarkResult(
            name="SELECT by ID",
            operations=num_operations,
            duration=duration,
            ops_per_second=num_operations / duration,
            mean_time=statistics.mean(times),
            median_time=statistics.median(times),
            p95_time=self._calculate_percentile(times, 95),
            min_time=min(times),
            max_time=max(times)
        )

        self.results.append(result)
        self._print_result(result)
        return result

    def benchmark_joins(self, num_operations: int = 500) -> DBBenchmarkResult:
        """Benchmark JOIN operations."""
        print(f"\nBenchmarking JOIN operations ({num_operations} ops)...")

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Insert test data for reviews
        cursor.execute("SELECT id FROM repositories LIMIT 10")
        repo_ids = [row[0] for row in cursor.fetchall()]

        if not repo_ids:
            print("  No repositories found, skipping JOIN benchmark")
            return None

        for repo_id in repo_ids:
            for i in range(10):
                cursor.execute(
                    "INSERT INTO reviews (repository_id, pr_number, status) VALUES (?, ?, ?)",
                    (repo_id, i, "success" if i % 2 == 0 else "failed")
                )
        conn.commit()

        times = []
        start_total = time.perf_counter()

        for i in range(num_operations):
            start = time.perf_counter()
            cursor.execute("""
                SELECT r.name, COUNT(rv.id) as review_count
                FROM repositories r
                LEFT JOIN reviews rv ON r.id = rv.repository_id
                WHERE r.id = ?
                GROUP BY r.id
            """, (repo_ids[i % len(repo_ids)],))
            cursor.fetchall()
            times.append(time.perf_counter() - start)

        duration = time.perf_counter() - start_total
        conn.close()

        result = DBBenchmarkResult(
            name="JOIN with GROUP BY",
            operations=num_operations,
            duration=duration,
            ops_per_second=num_operations / duration,
            mean_time=statistics.mean(times),
            median_time=statistics.median(times),
            p95_time=self._calculate_percentile(times, 95),
            min_time=min(times),
            max_time=max(times)
        )

        self.results.append(result)
        self._print_result(result)
        return result

    def benchmark_updates(self, num_operations: int = 1000) -> DBBenchmarkResult:
        """Benchmark UPDATE operations."""
        print(f"\nBenchmarking UPDATE operations ({num_operations} ops)...")

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM repositories")
        count = cursor.fetchone()[0]

        times = []
        start_total = time.perf_counter()

        for i in range(num_operations):
            start = time.perf_counter()
            cursor.execute(
                "UPDATE repositories SET name = ? WHERE id = ?",
                (f"updated_repo_{i}", i % count + 1)
            )
            conn.commit()
            times.append(time.perf_counter() - start)

        duration = time.perf_counter() - start_total
        conn.close()

        result = DBBenchmarkResult(
            name="UPDATE",
            operations=num_operations,
            duration=duration,
            ops_per_second=num_operations / duration,
            mean_time=statistics.mean(times),
            median_time=statistics.median(times),
            p95_time=self._calculate_percentile(times, 95),
            min_time=min(times),
            max_time=max(times)
        )

        self.results.append(result)
        self._print_result(result)
        return result

    def benchmark_transactions(self, num_operations: int = 100) -> DBBenchmarkResult:
        """Benchmark transaction throughput."""
        print(f"\nBenchmarking transactions ({num_operations} transactions)...")

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        times = []
        start_total = time.perf_counter()

        for i in range(num_operations):
            start = time.perf_counter()
            cursor.execute("BEGIN TRANSACTION")
            for j in range(10):
                cursor.execute(
                    "INSERT INTO repositories (name, url) VALUES (?, ?)",
                    (f"txn_repo_{i}_{j}", f"https://example.com/txn_{i}_{j}")
                )
            cursor.execute("COMMIT")
            times.append(time.perf_counter() - start)

        duration = time.perf_counter() - start_total
        conn.close()

        result = DBBenchmarkResult(
            name="Transactions (10 ops each)",
            operations=num_operations,
            duration=duration,
            ops_per_second=num_operations / duration,
            mean_time=statistics.mean(times),
            median_time=statistics.median(times),
            p95_time=self._calculate_percentile(times, 95),
            min_time=min(times),
            max_time=max(times)
        )

        self.results.append(result)
        self._print_result(result)
        return result

    def _print_result(self, result: DBBenchmarkResult):
        """Print benchmark result."""
        print(f"  Operations/sec: {result.ops_per_second:.2f}")
        print(f"  Mean time: {result.mean_time * 1000:.3f}ms")
        print(f"  Median time: {result.median_time * 1000:.3f}ms")
        print(f"  P95 time: {result.p95_time * 1000:.3f}ms")
        print(f"  Min/Max: {result.min_time * 1000:.3f}ms / {result.max_time * 1000:.3f}ms")

    def run_all_benchmarks(self):
        """Run all database benchmarks."""
        print("=" * 80)
        print("Database Performance Benchmarks")
        print("=" * 80)

        self.benchmark_inserts(1000)
        self.benchmark_batch_inserts(1000, 100)
        self.benchmark_selects(1000)
        self.benchmark_joins(500)
        self.benchmark_updates(500)
        self.benchmark_transactions(100)

    def generate_report(self, output_file: str = None) -> Dict[str, Any]:
        """Generate benchmark report."""
        report = {
            'timestamp': datetime.now().isoformat(),
            'db_path': self.db_path,
            'benchmarks': [r.to_dict() for r in self.results],
            'summary': {
                'total_benchmarks': len(self.results),
                'average_ops_per_second': statistics.mean([r.ops_per_second for r in self.results])
            }
        }

        if output_file:
            with open(output_file, 'w') as f:
                json.dump(report, f, indent=2)
            print(f"\nReport saved to: {output_file}")

        return report

    def print_summary(self):
        """Print summary of all benchmarks."""
        print("\n" + "=" * 80)
        print("BENCHMARK SUMMARY")
        print("=" * 80)

        for result in self.results:
            print(f"\n{result.name}:")
            print(f"  {result.ops_per_second:.2f} ops/sec")
            print(f"  {result.mean_time * 1000:.3f}ms mean")

    def cleanup(self):
        """Clean up temporary files."""
        if self.temp_dir:
            import shutil
            shutil.rmtree(self.temp_dir, ignore_errors=True)


def main():
    """Run database benchmarks."""
    import argparse

    parser = argparse.ArgumentParser(description='Database Performance Benchmarks')
    parser.add_argument('--db', help='Database path (default: temporary)')
    parser.add_argument('--output', help='Output file for JSON report')

    args = parser.parse_args()

    benchmark = DatabaseBenchmark(db_path=args.db)

    try:
        benchmark.run_all_benchmarks()
        benchmark.print_summary()

        if args.output:
            benchmark.generate_report(args.output)

    finally:
        benchmark.cleanup()


if __name__ == '__main__':
    main()
