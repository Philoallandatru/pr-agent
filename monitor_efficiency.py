"""
AI效率指标监控面板 - 基于SQLite数据库

无需Prometheus/Grafana，直接查询数据库生成报表
"""
import json
import sqlite3
import sys
from datetime import datetime, timedelta
from pathlib import Path

# 设置Windows控制台UTF-8编码
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass


class EfficiencyMonitor:
    """效率指标监控器"""

    def __init__(self, db_path="pr_agent.db"):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row

    def get_summary(self, days=7):
        """获取汇总统计"""
        cutoff = datetime.now() - timedelta(days=days)
        cursor = self.conn.cursor()

        cursor.execute("""
            SELECT
                COUNT(*) as total_reviews,
                SUM(issues_found_total) as total_issues,
                SUM(issues_high_severity) as high_severity_issues,
                SUM(code_suggestions_count) as total_suggestions,
                SUM(tokens_total) as total_tokens,
                SUM(api_cost_usd) as total_cost,
                SUM(estimated_human_time_saved_minutes) as total_time_saved,
                AVG(review_processing_time_seconds) as avg_processing_time,
                AVG(pr_complexity_score) as avg_complexity
            FROM efficiency_metrics
            WHERE created_at > ?
        """, (cutoff.isoformat(),))

        return dict(cursor.fetchone())

    def get_daily_stats(self, days=7):
        """获取每日统计"""
        cutoff = datetime.now() - timedelta(days=days)
        cursor = self.conn.cursor()

        cursor.execute("""
            SELECT
                DATE(created_at) as date,
                COUNT(*) as reviews,
                SUM(issues_found_total) as issues,
                SUM(api_cost_usd) as cost,
                SUM(estimated_human_time_saved_minutes) as time_saved
            FROM efficiency_metrics
            WHERE created_at > ?
            GROUP BY DATE(created_at)
            ORDER BY date DESC
        """, (cutoff.isoformat(),))

        return [dict(row) for row in cursor.fetchall()]

    def get_top_languages(self, limit=5):
        """获取最常review的语言"""
        cursor = self.conn.cursor()

        cursor.execute("""
            SELECT pr_languages, COUNT(*) as count
            FROM efficiency_metrics
            WHERE pr_languages IS NOT NULL
            GROUP BY pr_languages
            ORDER BY count DESC
            LIMIT ?
        """, (limit,))

        results = []
        for row in cursor.fetchall():
            try:
                languages = json.loads(row['pr_languages'])
                results.append({
                    'languages': ', '.join(languages),
                    'count': row['count']
                })
            except Exception:
                pass

        return results

    def get_cost_by_model(self):
        """按模型统计成本"""
        cursor = self.conn.cursor()

        cursor.execute("""
            SELECT
                model_used,
                COUNT(*) as reviews,
                SUM(api_cost_usd) as total_cost,
                AVG(api_cost_usd) as avg_cost
            FROM efficiency_metrics
            WHERE model_used IS NOT NULL
            GROUP BY model_used
            ORDER BY total_cost DESC
        """)

        return [dict(row) for row in cursor.fetchall()]

    def get_roi_analysis(self):
        """ROI分析"""
        summary = self.get_summary(days=30)

        total_time_saved = summary['total_time_saved'] or 0
        total_cost = summary['total_cost'] or 0

        # 假设人工审查成本为 $50/小时
        human_cost_per_minute = 50 / 60
        total_value = total_time_saved * human_cost_per_minute

        if total_cost > 0:
            roi = ((total_value - total_cost) / total_cost) * 100
        else:
            roi = 0

        return {
            'total_time_saved_minutes': total_time_saved,
            'total_time_saved_hours': total_time_saved / 60,
            'total_api_cost': total_cost,
            'estimated_value': total_value,
            'roi_percentage': roi,
            'net_savings': total_value - total_cost
        }

    def display_dashboard(self):
        """显示监控面板"""
        print("=" * 80)
        print("PR-Agent AI效率监控面板")
        print("=" * 80)

        # 汇总统计
        print("\n[最近7天汇总]")
        print("-" * 80)
        summary = self.get_summary(days=7)
        print(f"  总Review数:        {summary['total_reviews'] or 0}")
        print(f"  发现问题总数:      {summary['total_issues'] or 0}")
        print(f"  高严重性问题:      {summary['high_severity_issues'] or 0}")
        print(f"  代码建议数:        {summary['total_suggestions'] or 0}")
        print(f"  总Token使用:       {summary['total_tokens'] or 0:,}")
        print(f"  总API成本:         ${summary['total_cost'] or 0:.2f}")
        print(f"  节省时间:          {(summary['total_time_saved'] or 0) / 60:.1f} 小时")
        print(f"  平均处理时间:      {summary['avg_processing_time'] or 0:.1f} 秒")
        print(f"  平均复杂度:        {summary['avg_complexity'] or 0:.2f}")

        # ROI分析
        print("\n[ROI分析（最近30天）]")
        print("-" * 80)
        roi = self.get_roi_analysis()
        print(f"  节省时间:          {roi['total_time_saved_hours']:.1f} 小时")
        print(f"  API成本:           ${roi['total_api_cost']:.2f}")
        print(f"  估算价值:          ${roi['estimated_value']:.2f}")
        print(f"  净节省:            ${roi['net_savings']:.2f}")
        print(f"  ROI:               {roi['roi_percentage']:.1f}%")

        # 每日趋势
        print("\n[每日趋势]")
        print("-" * 80)
        daily = self.get_daily_stats(days=7)
        for day in daily:
            print(f"  {day['date']}: "
                  f"{day['reviews']}次review, "
                  f"{day['issues']}个问题, "
                  f"${day['cost'] or 0:.2f}, "
                  f"{(day['time_saved'] or 0) / 60:.1f}h节省")

        # 语言分布
        print("\n[最常review的语言]")
        print("-" * 80)
        languages = self.get_top_languages(limit=5)
        for lang in languages:
            print(f"  {lang['languages']}: {lang['count']}次")

        # 模型成本
        print("\n[按模型统计]")
        print("-" * 80)
        models = self.get_cost_by_model()
        for model in models:
            print(f"  {model['model_used'] or 'Unknown'}: "
                  f"{model['reviews']}次review, "
                  f"总成本${model['total_cost'] or 0:.2f}, "
                  f"平均${model['avg_cost'] or 0:.4f}")

        print("\n" + "=" * 80)

    def export_csv(self, output_file="efficiency_metrics.csv", days=None):
        """导出为CSV"""
        cursor = self.conn.cursor()

        if days:
            cutoff = datetime.now() - timedelta(days=days)
            cursor.execute(
                "SELECT * FROM efficiency_metrics WHERE created_at >= ? ORDER BY created_at DESC",
                (cutoff,)
            )
        else:
            cursor.execute("SELECT * FROM efficiency_metrics ORDER BY created_at DESC")

        import csv
        with open(output_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            # 写入表头
            writer.writerow([desc[0] for desc in cursor.description])
            # 写入数据
            writer.writerows(cursor.fetchall())

        print(f"已导出到 {output_file}")

    def close(self):
        """关闭数据库连接"""
        self.conn.close()


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description='PR-Agent效率指标监控面板')
    parser.add_argument('--db-path', default='pr_agent.db', help='数据库文件路径')
    parser.add_argument('--export', help='导出CSV文件路径')
    parser.add_argument('--days', type=int, default=7, help='统计天数')
    args = parser.parse_args()

    if not Path(args.db_path).exists():
        print(f"错误: 数据库文件不存在: {args.db_path}")
        print("   请确认PR-Agent已运行并收集了指标数据")
        return

    monitor = EfficiencyMonitor(args.db_path)

    try:
        # 显示面板
        monitor.display_dashboard()

        # 如果指定了导出路径，直接导出
        if args.export:
            monitor.export_csv(args.export, days=args.days)
            print(f"\n已导出到: {args.export}")

    finally:
        monitor.close()


if __name__ == "__main__":
    main()
