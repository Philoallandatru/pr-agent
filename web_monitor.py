"""
简单的Web监控面板 - 无需Grafana

使用Flask提供一个简单的HTML监控页面
"""
import sqlite3
from datetime import datetime, timedelta

from flask import Flask, render_template_string

app = Flask(__name__)

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>PR-Agent 效率监控</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            margin: 0;
            padding: 20px;
            background: #f5f5f5;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
        }
        h1 {
            color: #333;
            border-bottom: 3px solid #4CAF50;
            padding-bottom: 10px;
        }
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin: 20px 0;
        }
        .stat-card {
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .stat-value {
            font-size: 32px;
            font-weight: bold;
            color: #4CAF50;
            margin: 10px 0;
        }
        .stat-label {
            color: #666;
            font-size: 14px;
        }
        .section {
            background: white;
            padding: 20px;
            margin: 20px 0;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        table {
            width: 100%;
            border-collapse: collapse;
        }
        th, td {
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }
        th {
            background: #f8f8f8;
            font-weight: 600;
        }
        .positive {
            color: #4CAF50;
        }
        .negative {
            color: #f44336;
        }
        .refresh-btn {
            background: #4CAF50;
            color: white;
            border: none;
            padding: 10px 20px;
            border-radius: 4px;
            cursor: pointer;
            font-size: 14px;
        }
        .refresh-btn:hover {
            background: #45a049;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🎯 PR-Agent AI效率监控</h1>
        <button class="refresh-btn" onclick="location.reload()">🔄 刷新</button>

        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-label">总Review数</div>
                <div class="stat-value">{{ summary.total_reviews or 0 }}</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">发现问题</div>
                <div class="stat-value">{{ summary.total_issues or 0 }}</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">API成本</div>
                <div class="stat-value">${{ "%.2f"|format(summary.total_cost or 0) }}</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">节省时间</div>
                <div class="stat-value">{{ "%.1f"|format((summary.total_time_saved or 0) / 60) }}h</div>
            </div>
        </div>

        <div class="section">
            <h2>💰 ROI分析（最近30天）</h2>
            <table>
                <tr>
                    <td>节省时间</td>
                    <td><strong>{{ "%.1f"|format(roi.total_time_saved_hours) }}</strong> 小时</td>
                </tr>
                <tr>
                    <td>API成本</td>
                    <td><strong>${{ "%.2f"|format(roi.total_api_cost) }}</strong></td>
                </tr>
                <tr>
                    <td>估算价值</td>
                    <td><strong>${{ "%.2f"|format(roi.estimated_value) }}</strong></td>
                </tr>
                <tr>
                    <td>净节省</td>
                    <td class="{{ 'positive' if roi.net_savings > 0 else 'negative' }}">
                        <strong>${{ "%.2f"|format(roi.net_savings) }}</strong>
                    </td>
                </tr>
                <tr>
                    <td>ROI</td>
                    <td class="{{ 'positive' if roi.roi_percentage > 0 else 'negative' }}">
                        <strong>{{ "%.1f"|format(roi.roi_percentage) }}%</strong>
                    </td>
                </tr>
            </table>
        </div>

        <div class="section">
            <h2>📈 每日趋势（最近7天）</h2>
            <table>
                <thead>
                    <tr>
                        <th>日期</th>
                        <th>Review数</th>
                        <th>问题数</th>
                        <th>成本</th>
                        <th>节省时间</th>
                    </tr>
                </thead>
                <tbody>
                    {% for day in daily_stats %}
                    <tr>
                        <td>{{ day.date }}</td>
                        <td>{{ day.reviews }}</td>
                        <td>{{ day.issues }}</td>
                        <td>${{ "%.2f"|format(day.cost or 0) }}</td>
                        <td>{{ "%.1f"|format((day.time_saved or 0) / 60) }}h</td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>

        <div class="section">
            <h2>🤖 按模型统计</h2>
            <table>
                <thead>
                    <tr>
                        <th>模型</th>
                        <th>Review数</th>
                        <th>总成本</th>
                        <th>平均成本</th>
                    </tr>
                </thead>
                <tbody>
                    {% for model in models %}
                    <tr>
                        <td>{{ model.model_used or 'Unknown' }}</td>
                        <td>{{ model.reviews }}</td>
                        <td>${{ "%.2f"|format(model.total_cost or 0) }}</td>
                        <td>${{ "%.4f"|format(model.avg_cost or 0) }}</td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>

        <p style="text-align: center; color: #999; margin-top: 40px;">
            最后更新: {{ now }}
        </p>
    </div>
</body>
</html>
"""


def get_db():
    """获取数据库连接"""
    conn = sqlite3.connect('pr_agent.db')
    conn.row_factory = sqlite3.Row
    return conn


@app.route('/')
def dashboard():
    """监控面板"""
    conn = get_db()
    cursor = conn.cursor()

    # 汇总统计
    cutoff_7d = (datetime.now() - timedelta(days=7)).isoformat()
    cursor.execute("""
        SELECT
            COUNT(*) as total_reviews,
            SUM(issues_found_total) as total_issues,
            SUM(api_cost_usd) as total_cost,
            SUM(estimated_human_time_saved_minutes) as total_time_saved
        FROM efficiency_metrics
        WHERE created_at > ?
    """, (cutoff_7d,))
    summary = dict(cursor.fetchone())

    # ROI分析
    cutoff_30d = (datetime.now() - timedelta(days=30)).isoformat()
    cursor.execute("""
        SELECT
            SUM(estimated_human_time_saved_minutes) as total_time_saved,
            SUM(api_cost_usd) as total_cost
        FROM efficiency_metrics
        WHERE created_at > ?
    """, (cutoff_30d,))
    roi_data = dict(cursor.fetchone())

    total_time_saved = roi_data['total_time_saved'] or 0
    total_cost = roi_data['total_cost'] or 0
    human_cost_per_minute = 50 / 60
    total_value = total_time_saved * human_cost_per_minute
    roi = ((total_value - total_cost) / total_cost * 100) if total_cost > 0 else 0

    roi = {
        'total_time_saved_hours': total_time_saved / 60,
        'total_api_cost': total_cost,
        'estimated_value': total_value,
        'roi_percentage': roi,
        'net_savings': total_value - total_cost
    }

    # 每日统计
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
    """, (cutoff_7d,))
    daily_stats = [dict(row) for row in cursor.fetchall()]

    # 模型统计
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
    models = [dict(row) for row in cursor.fetchall()]

    conn.close()

    return render_template_string(
        HTML_TEMPLATE,
        summary=summary,
        roi=roi,
        daily_stats=daily_stats,
        models=models,
        now=datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    )


if __name__ == '__main__':
    print("🚀 启动监控面板...")
    print("📊 访问: http://localhost:5000")
    app.run(host='0.0.0.0', port=5000, debug=False)
