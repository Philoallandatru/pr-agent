"""
简单的Prometheus指标查看器 - 无需Grafana

直接访问 /metrics 端点并格式化显示
"""
import sys
from collections import defaultdict

import requests

# 设置Windows控制台UTF-8编码
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass


def fetch_and_display_metrics(url="http://localhost:8080/metrics", name_filter=None):
    """获取并显示Prometheus指标"""
    try:
        response = requests.get(url)
        response.raise_for_status()

        metrics = defaultdict(list)

        # 解析Prometheus文本格式
        for line in response.text.split('\n'):
            line = line.strip()
            if not line or line.startswith('#'):
                continue

            # 提取AI效率指标
            if 'pr_agent_ai_' in line and (not name_filter or name_filter in line):
                parts = line.split()
                if len(parts) >= 2:
                    metric_name = parts[0].split('{')[0]
                    metrics[metric_name].append(line)

        # 显示指标
        print("=" * 80)
        print("PR-Agent AI效率指标")
        print("=" * 80)

        for metric_name, lines in sorted(metrics.items()):
            print(f"\n[{metric_name}]")
            print("-" * 80)
            for line in lines[:10]:  # 只显示前10条
                print(f"  {line}")
            if len(lines) > 10:
                print(f"  ... 还有 {len(lines) - 10} 条")

        print("\n" + "=" * 80)

    except requests.exceptions.ConnectionError:
        print("错误: 无法连接到PR-Agent服务")
        print(f"   请确认服务运行在 {url}")
    except Exception as e:
        print(f"错误: {e}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Prometheus指标查看器')
    parser.add_argument('--url', default='http://localhost:8080/metrics',
                        help='Prometheus metrics端点URL')
    parser.add_argument('--filter', default=None, help='仅显示包含该文本的指标')
    args = parser.parse_args()

    fetch_and_display_metrics(args.url, args.filter)
