"""
Analytics and Reporting Module

Provides advanced analytics for code quality trends, team efficiency,
review quality scoring, and custom report generation.
"""

from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from collections import defaultdict
import json

from pr_agent.storage.database import Database
from pr_agent.log import get_logger


class AnalyticsEngine:
    """
    Analytics engine for generating insights and reports.

    Features:
    - Code quality trends over time
    - Team efficiency metrics
    - Review quality scoring
    - Custom report generation
    """

    def __init__(self, database: Database):
        """
        Initialize analytics engine.

        Args:
            database: Database instance
        """
        self.db = database
        self.logger = get_logger()

    def get_code_quality_trends(
        self,
        repository_id: Optional[int] = None,
        days: int = 30
    ) -> Dict[str, Any]:
        """
        Analyze code quality trends over time.

        Args:
            repository_id: Filter by repository (None = all)
            days: Number of days to analyze

        Returns:
            Dictionary with trend data
        """
        cursor = self.db.conn.cursor()
        start_date = datetime.now() - timedelta(days=days)

        # Build query
        query = """
            SELECT
                DATE(created_at) as date,
                COUNT(*) as total_reviews,
                SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed,
                SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed,
                AVG(
                    CASE
                        WHEN completed_at IS NOT NULL
                        THEN (julianday(completed_at) - julianday(created_at)) * 24 * 60
                        ELSE NULL
                    END
                ) as avg_duration_minutes
            FROM pr_reviews
            WHERE created_at >= ?
        """
        params = [start_date.isoformat()]

        if repository_id:
            query += " AND repository_id = ?"
            params.append(repository_id)

        query += " GROUP BY DATE(created_at) ORDER BY date"

        cursor.execute(query, params)
        rows = cursor.fetchall()

        # Format results
        trends = {
            "period": {"start": start_date.isoformat(), "end": datetime.now().isoformat()},
            "daily_data": [],
            "summary": {
                "total_reviews": 0,
                "completed_reviews": 0,
                "failed_reviews": 0,
                "avg_duration_minutes": 0,
                "success_rate": 0
            }
        }

        total_reviews = 0
        total_completed = 0
        total_failed = 0
        total_duration = 0
        duration_count = 0

        for row in rows:
            date, reviews, completed, failed, avg_duration = row

            trends["daily_data"].append({
                "date": date,
                "total_reviews": reviews,
                "completed": completed,
                "failed": failed,
                "success_rate": (completed / reviews * 100) if reviews > 0 else 0,
                "avg_duration_minutes": round(avg_duration, 2) if avg_duration else 0
            })

            total_reviews += reviews
            total_completed += completed
            total_failed += failed
            if avg_duration:
                total_duration += avg_duration
                duration_count += 1

        # Calculate summary
        trends["summary"]["total_reviews"] = total_reviews
        trends["summary"]["completed_reviews"] = total_completed
        trends["summary"]["failed_reviews"] = total_failed
        trends["summary"]["success_rate"] = (
            round(total_completed / total_reviews * 100, 2) if total_reviews > 0 else 0
        )
        trends["summary"]["avg_duration_minutes"] = (
            round(total_duration / duration_count, 2) if duration_count > 0 else 0
        )

        return trends

    def get_team_efficiency_metrics(
        self,
        repository_id: Optional[int] = None,
        days: int = 30
    ) -> Dict[str, Any]:
        """
        Calculate team efficiency metrics.

        Args:
            repository_id: Filter by repository
            days: Number of days to analyze

        Returns:
            Dictionary with efficiency metrics
        """
        cursor = self.db.conn.cursor()
        start_date = datetime.now() - timedelta(days=days)

        # Reviews per day
        query = """
            SELECT
                COUNT(*) as total_reviews,
                COUNT(DISTINCT pr_author) as unique_authors,
                AVG(
                    CASE
                        WHEN completed_at IS NOT NULL
                        THEN (julianday(completed_at) - julianday(created_at)) * 24
                        ELSE NULL
                    END
                ) as avg_review_time_hours
            FROM pr_reviews
            WHERE created_at >= ?
        """
        params = [start_date.isoformat()]

        if repository_id:
            query += " AND repository_id = ?"
            params.append(repository_id)

        cursor.execute(query, params)
        row = cursor.fetchone()

        total_reviews = row[0] or 0
        unique_authors = row[1] or 0
        avg_review_time = row[2] or 0

        # Reviews by author
        query = """
            SELECT
                pr_author,
                COUNT(*) as review_count,
                SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed_count
            FROM pr_reviews
            WHERE created_at >= ?
        """
        params = [start_date.isoformat()]

        if repository_id:
            query += " AND repository_id = ?"
            params.append(repository_id)

        query += " GROUP BY pr_author ORDER BY review_count DESC LIMIT 10"

        cursor.execute(query, params)
        top_authors = [
            {
                "author": row[0],
                "total_reviews": row[1],
                "completed_reviews": row[2],
                "success_rate": round(row[2] / row[1] * 100, 2) if row[1] > 0 else 0
            }
            for row in cursor.fetchall()
        ]

        # Peak hours analysis
        query = """
            SELECT
                CAST(strftime('%H', created_at) AS INTEGER) as hour,
                COUNT(*) as review_count
            FROM pr_reviews
            WHERE created_at >= ?
        """
        params = [start_date.isoformat()]

        if repository_id:
            query += " AND repository_id = ?"
            params.append(repository_id)

        query += " GROUP BY hour ORDER BY hour"

        cursor.execute(query, params)
        hourly_distribution = [
            {"hour": row[0], "count": row[1]}
            for row in cursor.fetchall()
        ]

        return {
            "period": {"start": start_date.isoformat(), "end": datetime.now().isoformat()},
            "summary": {
                "total_reviews": total_reviews,
                "unique_authors": unique_authors,
                "avg_review_time_hours": round(avg_review_time, 2),
                "reviews_per_day": round(total_reviews / days, 2),
                "reviews_per_author": round(total_reviews / unique_authors, 2) if unique_authors > 0 else 0
            },
            "top_authors": top_authors,
            "hourly_distribution": hourly_distribution
        }

    def get_review_quality_score(
        self,
        repository_id: Optional[int] = None,
        days: int = 30
    ) -> Dict[str, Any]:
        """
        Calculate review quality score based on multiple factors.

        Scoring factors:
        - Success rate (40%)
        - Review speed (30%)
        - Coverage (30%)

        Args:
            repository_id: Filter by repository
            days: Number of days to analyze

        Returns:
            Dictionary with quality score and breakdown
        """
        cursor = self.db.conn.cursor()
        start_date = datetime.now() - timedelta(days=days)

        query = """
            SELECT
                COUNT(*) as total,
                SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed,
                AVG(
                    CASE
                        WHEN completed_at IS NOT NULL
                        THEN (julianday(completed_at) - julianday(created_at)) * 24
                        ELSE NULL
                    END
                ) as avg_hours
            FROM pr_reviews
            WHERE created_at >= ?
        """
        params = [start_date.isoformat()]

        if repository_id:
            query += " AND repository_id = ?"
            params.append(repository_id)

        cursor.execute(query, params)
        row = cursor.fetchone()

        total = row[0] or 0
        completed = row[1] or 0
        avg_hours = row[2] or 0

        # Calculate component scores (0-100)
        success_rate = (completed / total * 100) if total > 0 else 0
        success_score = success_rate  # Direct mapping

        # Speed score (faster is better, target < 2 hours)
        if avg_hours == 0:
            speed_score = 0
        elif avg_hours <= 1:
            speed_score = 100
        elif avg_hours <= 2:
            speed_score = 80
        elif avg_hours <= 4:
            speed_score = 60
        elif avg_hours <= 8:
            speed_score = 40
        else:
            speed_score = 20

        # Coverage score (based on review frequency)
        expected_reviews_per_day = 5  # Configurable
        actual_reviews_per_day = total / days if days > 0 else 0
        coverage_score = min(100, (actual_reviews_per_day / expected_reviews_per_day) * 100)

        # Weighted total score
        total_score = (
            success_score * 0.4 +
            speed_score * 0.3 +
            coverage_score * 0.3
        )

        # Grade
        if total_score >= 90:
            grade = "A"
        elif total_score >= 80:
            grade = "B"
        elif total_score >= 70:
            grade = "C"
        elif total_score >= 60:
            grade = "D"
        else:
            grade = "F"

        return {
            "period": {"start": start_date.isoformat(), "end": datetime.now().isoformat()},
            "overall_score": round(total_score, 2),
            "grade": grade,
            "components": {
                "success": {
                    "score": round(success_score, 2),
                    "weight": 40,
                    "metrics": {
                        "total_reviews": total,
                        "completed_reviews": completed,
                        "success_rate": round(success_rate, 2)
                    }
                },
                "speed": {
                    "score": round(speed_score, 2),
                    "weight": 30,
                    "metrics": {
                        "avg_review_time_hours": round(avg_hours, 2)
                    }
                },
                "coverage": {
                    "score": round(coverage_score, 2),
                    "weight": 30,
                    "metrics": {
                        "reviews_per_day": round(actual_reviews_per_day, 2),
                        "target_per_day": expected_reviews_per_day
                    }
                }
            }
        }

    def get_repository_comparison(self, days: int = 30) -> List[Dict[str, Any]]:
        """
        Compare metrics across all repositories.

        Args:
            days: Number of days to analyze

        Returns:
            List of repository metrics
        """
        cursor = self.db.conn.cursor()
        start_date = datetime.now() - timedelta(days=days)

        query = """
            SELECT
                r.id,
                r.project_key,
                r.repo_slug,
                COUNT(pr.id) as total_reviews,
                SUM(CASE WHEN pr.status = 'completed' THEN 1 ELSE 0 END) as completed,
                AVG(
                    CASE
                        WHEN pr.completed_at IS NOT NULL
                        THEN (julianday(pr.completed_at) - julianday(pr.created_at)) * 24
                        ELSE NULL
                    END
                ) as avg_hours
            FROM repositories r
            LEFT JOIN pr_reviews pr ON r.id = pr.repository_id
                AND pr.created_at >= ?
            GROUP BY r.id
            ORDER BY total_reviews DESC
        """

        cursor.execute(query, [start_date.isoformat()])

        results = []
        for row in cursor.fetchall():
            repo_id, project_key, repo_slug, total, completed, avg_hours = row

            success_rate = (completed / total * 100) if total > 0 else 0

            results.append({
                "repository_id": repo_id,
                "repository": f"{project_key}/{repo_slug}",
                "total_reviews": total,
                "completed_reviews": completed,
                "success_rate": round(success_rate, 2),
                "avg_review_time_hours": round(avg_hours, 2) if avg_hours else 0
            })

        return results

    def generate_custom_report(
        self,
        report_type: str,
        filters: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Generate custom report based on type and filters.

        Args:
            report_type: Type of report (summary, detailed, comparison)
            filters: Optional filters (repository_id, date_range, etc.)

        Returns:
            Generated report data
        """
        filters = filters or {}
        days = filters.get("days", 30)
        repository_id = filters.get("repository_id")

        if report_type == "summary":
            return {
                "type": "summary",
                "generated_at": datetime.now().isoformat(),
                "quality_trends": self.get_code_quality_trends(repository_id, days),
                "efficiency_metrics": self.get_team_efficiency_metrics(repository_id, days),
                "quality_score": self.get_review_quality_score(repository_id, days)
            }

        elif report_type == "detailed":
            return {
                "type": "detailed",
                "generated_at": datetime.now().isoformat(),
                "quality_trends": self.get_code_quality_trends(repository_id, days),
                "efficiency_metrics": self.get_team_efficiency_metrics(repository_id, days),
                "quality_score": self.get_review_quality_score(repository_id, days),
                "repository_comparison": self.get_repository_comparison(days)
            }

        elif report_type == "comparison":
            return {
                "type": "comparison",
                "generated_at": datetime.now().isoformat(),
                "repositories": self.get_repository_comparison(days)
            }

        else:
            raise ValueError(f"Unknown report type: {report_type}")

    def get_overview(self, days: int = 30) -> Dict[str, Any]:
        """
        Get high-level analytics overview.

        Args:
            days: Number of days to analyze

        Returns:
            Overview data
        """
        return {
            "generated_at": datetime.now().isoformat(),
            "period_days": days,
            "quality_score": self.get_review_quality_score(None, days),
            "efficiency": self.get_team_efficiency_metrics(None, days),
            "trends": self.get_code_quality_trends(None, days)
        }

    def get_trends(self, metric: str, days: int = 30) -> Dict[str, Any]:
        """
        Get trend data for a specific metric.

        Args:
            metric: Metric name (review_count, success_rate, duration)
            days: Number of days to analyze

        Returns:
            Trend data
        """
        trends = self.get_code_quality_trends(None, days)

        if metric == "review_count":
            data = [{"date": d["date"], "value": d["total_reviews"]} for d in trends["daily_data"]]
        elif metric == "success_rate":
            data = [{"date": d["date"], "value": d["success_rate"]} for d in trends["daily_data"]]
        elif metric == "duration":
            data = [{"date": d["date"], "value": d["avg_duration_minutes"]} for d in trends["daily_data"]]
        else:
            raise ValueError(f"Unknown metric: {metric}")

        return {
            "metric": metric,
            "period_days": days,
            "data": data
        }

    def get_repository_analytics(self, repo_id: int, days: int = 30) -> Dict[str, Any]:
        """
        Get analytics for a specific repository.

        Args:
            repo_id: Repository ID
            days: Number of days to analyze

        Returns:
            Repository analytics
        """
        return {
            "repository_id": repo_id,
            "generated_at": datetime.now().isoformat(),
            "period_days": days,
            "quality_trends": self.get_code_quality_trends(repo_id, days),
            "efficiency_metrics": self.get_team_efficiency_metrics(repo_id, days),
            "quality_score": self.get_review_quality_score(repo_id, days)
        }

    def generate_report(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        format: str = "json"
    ) -> Any:
        """
        Generate comprehensive analytics report.

        Args:
            start_date: Start date for report
            end_date: End date for report
            format: Output format (json, csv, text)

        Returns:
            Report in requested format
        """
        end_date = end_date or datetime.now()
        start_date = start_date or (end_date - timedelta(days=30))
        days = (end_date - start_date).days

        report_data = {
            "type": "comprehensive",
            "generated_at": datetime.now().isoformat(),
            "period": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat(),
                "days": days
            },
            "quality_trends": self.get_code_quality_trends(None, days),
            "efficiency_metrics": self.get_team_efficiency_metrics(None, days),
            "quality_score": self.get_review_quality_score(None, days),
            "repository_comparison": self.get_repository_comparison(days)
        }

        if format == "json":
            return report_data
        elif format == "csv":
            # Convert to CSV format
            import io
            import csv
            output = io.StringIO()
            writer = csv.writer(output)

            # Write summary
            writer.writerow(["PR-Agent Analytics Report"])
            writer.writerow(["Generated", report_data["generated_at"]])
            writer.writerow(["Period", f"{start_date.date()} to {end_date.date()}"])
            writer.writerow([])

            # Write quality score
            score = report_data["quality_score"]
            writer.writerow(["Quality Score", score["overall_score"], score["grade"]])
            writer.writerow([])

            # Write repository comparison
            writer.writerow(["Repository Comparison"])
            repos = report_data["repository_comparison"]
            if repos:
                writer.writerow(repos[0].keys())
                for repo in repos:
                    writer.writerow(repo.values())

            return output.getvalue()
        elif format == "text":
            # Convert to text format
            lines = []
            lines.append("=" * 60)
            lines.append("PR-Agent Analytics Report")
            lines.append("=" * 60)
            lines.append(f"Generated: {report_data['generated_at']}")
            lines.append(f"Period: {start_date.date()} to {end_date.date()} ({days} days)")
            lines.append("")

            # Quality score
            score = report_data["quality_score"]
            lines.append(f"Overall Quality Score: {score['overall_score']:.2f} (Grade: {score['grade']})")
            lines.append("")

            # Summary
            summary = report_data["quality_trends"]["summary"]
            lines.append("Summary:")
            lines.append(f"  Total Reviews: {summary['total_reviews']}")
            lines.append(f"  Completed: {summary['completed_reviews']}")
            lines.append(f"  Success Rate: {summary['success_rate']:.2f}%")
            lines.append(f"  Avg Duration: {summary['avg_duration_minutes']:.2f} minutes")
            lines.append("")

            # Repository comparison
            lines.append("Repository Comparison:")
            for repo in report_data["repository_comparison"]:
                lines.append(f"  {repo['repository']}:")
                lines.append(f"    Reviews: {repo['total_reviews']}")
                lines.append(f"    Success Rate: {repo['success_rate']:.2f}%")
                lines.append("")

            return "\n".join(lines)
        else:
            raise ValueError(f"Unknown format: {format}")


def export_report_to_json(report: Dict[str, Any], filepath: str):
    """Export report to JSON file."""
    with open(filepath, 'w') as f:
        json.dump(report, f, indent=2)


def export_report_to_csv(report: Dict[str, Any], filepath: str):
    """Export report to CSV file."""
    import csv

    # Extract tabular data based on report type
    if report["type"] == "comparison":
        data = report["repositories"]
        if not data:
            return

        with open(filepath, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=data[0].keys())
            writer.writeheader()
            writer.writerows(data)

    elif "quality_trends" in report:
        data = report["quality_trends"]["daily_data"]
        if not data:
            return

        with open(filepath, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=data[0].keys())
            writer.writeheader()
            writer.writerows(data)
