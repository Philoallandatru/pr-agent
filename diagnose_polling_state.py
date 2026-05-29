"""
诊断PollingState问题的脚本
"""
import json
from pathlib import Path
from pr_agent.storage.polling_state import PollingState
from pr_agent.config_loader import get_settings

def diagnose_polling_state():
    print("=== PollingState 诊断 ===\n")

    # 1. 检查配置
    state_file_path = get_settings().get(
        "bitbucket_server.polling_state_file",
        ".pr_agent_polling_state.json"
    )
    print(f"1. 配置的状态文件路径: {state_file_path}")

    # 2. 检查文件是否存在
    state_file = Path(state_file_path)
    print(f"2. 文件是否存在: {state_file.exists()}")

    if state_file.exists():
        print(f"3. 文件大小: {state_file.stat().st_size} bytes")

        # 4. 读取文件内容
        try:
            with open(state_file, 'r') as f:
                content = f.read()
                print(f"4. 文件内容长度: {len(content)} 字符")

                if content:
                    state_data = json.loads(content)
                    print(f"5. 记录的仓库数: {len(state_data)}")

                    total_prs = sum(len(prs) for prs in state_data.values())
                    print(f"6. 记录的PR总数: {total_prs}")

                    # 显示前5个PR
                    print("\n7. 前5个PR记录:")
                    count = 0
                    for repo_key, prs in state_data.items():
                        for pr_id, pr_state in prs.items():
                            if count >= 5:
                                break
                            print(f"   - {repo_key}#{pr_id}: version={pr_state.get('version')}, "
                                  f"status={pr_state.get('status')}, "
                                  f"last_processed={pr_state.get('last_processed')}")
                            count += 1
                        if count >= 5:
                            break
                else:
                    print("4. 文件为空！")
        except Exception as e:
            print(f"4. 读取文件失败: {e}")
    else:
        print("3. 文件不存在，将在首次轮询时创建")

    # 8. 测试PollingState类
    print("\n8. 测试PollingState类:")
    try:
        state = PollingState()
        stats = state.get_statistics()
        print(f"   - 总仓库数: {stats['total_repositories']}")
        print(f"   - 总PR数: {stats['total_prs_tracked']}")
        print(f"   - 24小时内处理: {stats['prs_processed_last_24h']}")
        print(f"   - 状态文件: {stats['state_file']}")
        print(f"   - 文件存在: {stats['state_file_exists']}")
    except Exception as e:
        print(f"   - 初始化失败: {e}")

    # 9. 测试写入
    print("\n9. 测试写入功能:")
    try:
        state = PollingState()
        test_repo = "TEST/test-repo"
        test_pr_id = 99999
        test_version = 1

        # 尝试标记为processing
        result = state.try_mark_processing(test_repo, test_pr_id, test_version, ["review"])
        print(f"   - try_mark_processing 返回: {result}")

        if result:
            # 更新为completed
            state.update_pr_state(test_repo, test_pr_id, test_version, ["review"], status="completed")
            print(f"   - 已更新状态为completed")

            # 再次尝试
            result2 = state.try_mark_processing(test_repo, test_pr_id, test_version, ["review"])
            print(f"   - 再次try_mark_processing 返回: {result2} (应该是False)")

            if not result2:
                print("   ✅ 去重机制工作正常！")
            else:
                print("   ❌ 去重机制失败！")
        else:
            print("   - 测试PR已存在")

    except Exception as e:
        print(f"   - 测试失败: {e}")
        import traceback
        traceback.print_exc()

    print("\n=== 诊断完成 ===")

if __name__ == "__main__":
    diagnose_polling_state()
