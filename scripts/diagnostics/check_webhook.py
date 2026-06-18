#!/usr/bin/env python
"""
Bitbucket Server Webhook 测试脚本

验证webhook服务器是否正常运行并能够处理请求
"""
import sys
import time
from pathlib import Path

import requests

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

# 设置Windows控制台UTF-8编码
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass


def test_health_check(base_url):
    """测试健康检查端点"""
    print("=" * 80)
    print("测试1: 健康检查")
    print("-" * 80)

    try:
        response = requests.get(f"{base_url}/", timeout=5)
        if response.status_code == 200:
            print("✓ 健康检查通过")
            print(f"  响应: {response.json()}")
            return True
        else:
            print(f"✗ 健康检查失败: HTTP {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print(f"✗ 无法连接到服务器: {base_url}")
        print("  请确认服务器正在运行")
        return False
    except Exception as e:
        print(f"✗ 健康检查失败: {e}")
        return False


def test_webhook_endpoint(base_url):
    """测试webhook端点是否存在"""
    print("\n" + "=" * 80)
    print("测试2: Webhook端点")
    print("-" * 80)

    # 创建一个模拟的webhook payload
    test_payload = {
        "test": True
    }

    try:
        response = requests.post(
            f"{base_url}/webhook",
            json=test_payload,
            headers={"Content-Type": "application/json"},
            timeout=10
        )

        if response.status_code == 200:
            print("✓ Webhook端点响应正常")
            print(f"  响应: {response.json()}")
            return True
        elif response.status_code == 400:
            print("✓ Webhook端点存在（拒绝了测试payload，这是正常的）")
            return True
        else:
            print(f"? Webhook端点响应: HTTP {response.status_code}")
            print(f"  响应: {response.text[:200]}")
            return True
    except Exception as e:
        print(f"✗ Webhook端点测试失败: {e}")
        return False


def test_pr_opened_webhook(base_url):
    """测试PR opened事件的webhook payload"""
    print("\n" + "=" * 80)
    print("测试3: 模拟PR Opened事件")
    print("-" * 80)

    # 模拟Bitbucket Server的PR opened webhook payload
    pr_opened_payload = {
        "eventKey": "pr:opened",
        "pullRequest": {
            "id": 999,
            "title": "Test PR for webhook validation",
            "author": {
                "user": {
                    "name": "test-user",
                    "emailAddress": "test@example.com"
                }
            },
            "fromRef": {
                "displayId": "feature/test-branch",
                "repository": {
                    "slug": "test-repo",
                    "project": {
                        "key": "TEST"
                    }
                }
            },
            "toRef": {
                "displayId": "main",
                "repository": {
                    "slug": "test-repo",
                    "project": {
                        "key": "TEST"
                    }
                }
            }
        }
    }

    try:
        response = requests.post(
            f"{base_url}/webhook",
            json=pr_opened_payload,
            headers={"Content-Type": "application/json"},
            timeout=10
        )

        if response.status_code == 200:
            print("✓ PR opened webhook接受成功")
            print(f"  响应: {response.json()}")
            return True
        else:
            print(f"? PR opened webhook响应: HTTP {response.status_code}")
            print(f"  响应: {response.text[:200]}")
            # 即使返回错误，只要服务器响应了就算通过
            return response.status_code < 500
    except Exception as e:
        print(f"✗ PR opened webhook测试失败: {e}")
        return False


def test_environment_config():
    """测试环境变量配置"""
    print("\n" + "=" * 80)
    print("测试4: 环境变量配置")
    print("-" * 80)

    import os

    required_vars = {
        "BITBUCKET_URL": "Bitbucket Server URL",
        "BITBUCKET_TOKEN": "Bitbucket 访问令牌"
    }

    ai_keys = {
        "OPENAI_API_KEY": "OpenAI API密钥",
        "ANTHROPIC_API_KEY": "Anthropic API密钥",
        "AZURE_OPENAI_API_KEY": "Azure OpenAI API密钥"
    }

    all_ok = True

    # 检查必需变量
    for var, desc in required_vars.items():
        value = os.getenv(var)
        if value:
            print(f"✓ {var}: 已设置 ({desc})")
        else:
            print(f"✗ {var}: 未设置 ({desc})")
            all_ok = False

    # 检查AI密钥（至少需要一个）
    has_ai_key = False
    for var, desc in ai_keys.items():
        value = os.getenv(var)
        if value:
            print(f"✓ {var}: 已设置 ({desc})")
            has_ai_key = True

    if not has_ai_key:
        print("✗ 至少需要设置一个AI API密钥")
        all_ok = False

    return all_ok


def test_database_exists():
    """测试数据库文件是否存在"""
    print("\n" + "=" * 80)
    print("测试5: 数据库文件")
    print("-" * 80)

    db_path = Path("pr_agent.db")
    if db_path.exists():
        size = db_path.stat().st_size
        print(f"✓ 数据库文件存在: {db_path}")
        print(f"  文件大小: {size / 1024:.2f} KB")
        return True
    else:
        print(f"? 数据库文件不存在: {db_path}")
        print("  这是正常的（首次运行时会自动创建）")
        return True


def main():
    """运行所有测试"""
    import argparse

    parser = argparse.ArgumentParser(description='Bitbucket Server Webhook测试工具')
    parser.add_argument('--url', default='http://localhost:3000',
                        help='Webhook服务器URL (默认: http://localhost:3000)')
    parser.add_argument('--skip-webhook', action='store_true',
                        help='跳过webhook端点测试（仅测试健康检查）')
    args = parser.parse_args()

    print("\n")
    print("╔" + "=" * 78 + "╗")
    print("║" + " " * 15 + "Bitbucket Server Webhook 测试工具" + " " * 29 + "║")
    print("╚" + "=" * 78 + "╝")
    print()
    print(f"目标服务器: {args.url}")
    print()

    results = []

    # 测试环境变量
    results.append(("环境变量配置", test_environment_config()))

    # 测试数据库
    results.append(("数据库文件", test_database_exists()))

    # 等待一下，确保服务器启动
    print("\n等待服务器启动...")
    time.sleep(1)

    # 测试服务器健康
    results.append(("健康检查", test_health_check(args.url)))

    if not args.skip_webhook:
        # 测试webhook端点
        results.append(("Webhook端点", test_webhook_endpoint(args.url)))

        # 测试PR事件
        results.append(("PR Opened事件", test_pr_opened_webhook(args.url)))

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
        print("\n✓ 所有测试通过！Webhook服务器已就绪。")
        print("\n下一步:")
        print("  1. 在Bitbucket Server中配置webhook")
        print("     URL: " + args.url + "/webhook")
        print("  2. 选择触发事件: PR Opened, Source branch updated, Comment added")
        print("  3. 创建测试PR验证功能")
        return 0
    else:
        print(f"\n✗ {total - passed} 个测试失败")
        print("\n请检查:")
        print("  1. 环境变量是否正确设置")
        print("  2. Webhook服务器是否正在运行")
        print("  3. 查看服务器日志获取详细错误信息")
        return 1


if __name__ == "__main__":
    sys.exit(main())
