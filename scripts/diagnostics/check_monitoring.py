#!/usr/bin/env python
"""
监控工具测试脚本

验证所有监控工具是否正常工作
"""
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

# 设置Windows控制台UTF-8编码
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass


def test_database_exists():
    """测试数据库文件是否存在"""
    print("=" * 80)
    print("测试1: 检查数据库文件")
    print("-" * 80)

    db_path = Path("pr_agent.db")
    if db_path.exists():
        size = db_path.stat().st_size
        print(f"✓ 数据库文件存在: {db_path}")
        print(f"  文件大小: {size / 1024:.2f} KB")
        return True
    else:
        print(f"✗ 数据库文件不存在: {db_path}")
        print("  请先运行PR审查以收集数据")
        return False


def test_database_schema():
    """测试数据库表结构"""
    print("\n" + "=" * 80)
    print("测试2: 检查数据库表结构")
    print("-" * 80)

    try:
        import sqlite3
        conn = sqlite3.connect("pr_agent.db")
        cursor = conn.cursor()

        # 检查efficiency_metrics表
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='efficiency_metrics'"
        )
        if cursor.fetchone():
            print("✓ efficiency_metrics表存在")

            # 检查记录数
            cursor.execute("SELECT COUNT(*) FROM efficiency_metrics")
            count = cursor.fetchone()[0]
            print(f"  记录数: {count}")

            if count > 0:
                # 显示最新记录
                cursor.execute(
                    "SELECT pr_review_id, created_at, estimated_human_time_saved_minutes "
                    "FROM efficiency_metrics ORDER BY created_at DESC LIMIT 1"
                )
                row = cursor.fetchone()
                print(f"  最新记录: PR#{row[0]}, 时间: {row[1]}, 节省: {row[2]}分钟")

            conn.close()
            return count > 0
        else:
            print("✗ efficiency_metrics表不存在")
            conn.close()
            return False

    except Exception as e:
        print(f"✗ 数据库检查失败: {e}")
        return False


def test_monitor_efficiency():
    """测试SQLite监控工具"""
    print("\n" + "=" * 80)
    print("测试3: SQLite监控工具")
    print("-" * 80)

    try:
        from pr_agent.monitoring.efficiency_monitor import EfficiencyMonitor

        monitor = EfficiencyMonitor("pr_agent.db")

        # 测试获取摘要
        summary = monitor.get_summary(days=7)
        print(f"✓ 获取摘要成功")
        print(f"  总Review数: {summary['total_reviews']}")
        print(f"  总成本: ${summary['total_cost'] or 0:.2f}")

        # 测试ROI分析
        roi = monitor.get_roi_analysis()
        print(f"✓ ROI分析成功")
        print(f"  ROI: {roi['roi_percentage']:.1f}%")

        monitor.close()
        return True

    except Exception as e:
        print(f"✗ 监控工具测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_csv_export():
    """测试CSV导出"""
    print("\n" + "=" * 80)
    print("测试4: CSV导出功能")
    print("-" * 80)

    try:
        from pr_agent.monitoring.efficiency_monitor import EfficiencyMonitor

        monitor = EfficiencyMonitor("pr_agent.db")
        test_file = "test_export.csv"

        monitor.export_csv(test_file, days=30)
        monitor.close()

        # 检查文件是否创建
        if Path(test_file).exists():
            size = Path(test_file).stat().st_size
            print(f"✓ CSV导出成功: {test_file}")
            print(f"  文件大小: {size} 字节")

            # 清理测试文件
            Path(test_file).unlink()
            return True
        else:
            print(f"✗ CSV文件未创建")
            return False

    except Exception as e:
        print(f"✗ CSV导出失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_view_metrics():
    """测试Prometheus查看器"""
    print("\n" + "=" * 80)
    print("测试5: Prometheus指标查看器")
    print("-" * 80)

    try:
        # 只检查模块是否可以导入
        import pr_agent.monitoring.metrics_viewer
        print("✓ pr_agent.monitoring.metrics_viewer模块导入成功")
        print("  注意: 需要PR-Agent服务运行才能查看实时指标")
        return True

    except Exception as e:
        print(f"✗ pr_agent.monitoring.metrics_viewer导入失败: {e}")
        return False


def test_web_monitor():
    """测试Web监控界面"""
    print("\n" + "=" * 80)
    print("测试6: Web监控界面")
    print("-" * 80)

    try:
        # 检查Flask是否安装
        import flask
        print("✓ Flask已安装")

        # 检查web_dashboard模块
        import pr_agent.monitoring.web_dashboard
        print("✓ pr_agent.monitoring.web_dashboard模块导入成功")
        print("  使用 'python -m pr_agent.monitoring.web_dashboard' 启动Web服务")
        return True

    except ImportError as e:
        print(f"✗ 依赖缺失: {e}")
        print("  运行: pip install flask")
        return False
    except Exception as e:
        print(f"✗ web_dashboard检查失败: {e}")
        return False


def main():
    """运行所有测试"""
    print("\n")
    print("╔" + "=" * 78 + "╗")
    print("║" + " " * 20 + "PR-Agent 监控工具测试套件" + " " * 32 + "║")
    print("╚" + "=" * 78 + "╝")
    print()

    results = []

    # 运行测试
    results.append(("数据库文件", test_database_exists()))
    results.append(("数据库表结构", test_database_schema()))
    results.append(("SQLite监控工具", test_monitor_efficiency()))
    results.append(("CSV导出", test_csv_export()))
    results.append(("Prometheus查看器", test_view_metrics()))
    results.append(("Web监控界面", test_web_monitor()))

    # 汇总结果
    print("\n" + "=" * 80)
    print("测试结果汇总")
    print("=" * 80)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for name, result in results:
        status = "✓ 通过" if result else "✗ 失败"
        print(f"  {status:8} - {name}")

    print("-" * 80)
    print(f"总计: {passed}/{total} 通过")

    if passed == total:
        print("\n✓ 所有测试通过！监控工具已就绪。")
        print("\n快速开始:")
        print("  python -m pr_agent.monitoring.efficiency_monitor              # 查看监控面板")
        print("  python -m pr_agent.monitoring.efficiency_monitor --export metrics.csv  # 导出数据")
        print("  python -m pr_agent.monitoring.web_dashboard                   # 启动Web界面")
        return 0
    else:
        print(f"\n✗ {total - passed} 个测试失败")
        print("\n请查看上面的错误信息并修复问题")
        return 1


if __name__ == "__main__":
    sys.exit(main())
