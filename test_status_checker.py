"""
StatusChecker 测试/使用脚本
用法:  python test_status_checker.py
"""

import os, sys
from config import COURSE_URL, SECTION4_URL
from status_checker import StatusChecker

STORAGE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".login_storage.json")


def test_check_assignments():
    print("=" * 60)
    print("测试1: 作业状态检测（三策略递进）")
    print("=" * 60)

    sc = StatusChecker(
        storage_file=STORAGE_FILE,
        headless=True,  # 虚拟浏览器模式（不可见）
        callback=lambda m: print(f"  {m}")
    )
    sc.start_browser(use_storage=True)

    if not sc.check_login():
        print("[-] 登录态无效，请先执行 main.py 登录")
        sc.close()
        return False

    # 三种策略可选: STRATEGY_FAST / STRATEGY_BALANCED / STRATEGY_ACCURATE
    results = sc.check_all_activities(
        section_url=COURSE_URL,
        strategy=StatusChecker.STRATEGY_BALANCED
    )

    print(f"\n检测结果 ({len(results)} 项):")
    for aid in sorted(results.keys()):
        info = results[aid]
        completed = info.get("completed", False)
        score = info.get("score", "")
        status = "✓ 已完成" if completed else "✗ 未完成"
        score_disp = f" [{score}]" if score else ""
        print(f"  id={aid:<4} {status}{score_disp}")

    sc.close()
    return results


def test_check_exams():
    print("\n" + "=" * 60)
    print("测试2: 考试状态检测")
    print("=" * 60)

    sc = StatusChecker(
        storage_file=STORAGE_FILE,
        headless=True,
        callback=lambda m: print(f"  {m}")
    )
    sc.start_browser(use_storage=True)

    if not sc.check_login():
        print("[-] 登录态无效")
        sc.close()
        return False

    results = sc.check_all_activities(
        section_url=SECTION4_URL,
        strategy=StatusChecker.STRATEGY_FAST
    )

    print(f"\n考试检测结果 ({len(results)} 项):")
    for aid in sorted(results.keys()):
        status = "✓ 已完成" if results[aid] else "✗ 未完成"
        print(f"  id={aid:<4} {status}")

    sc.close()
    return results


if __name__ == "__main__":
    test_check_assignments()
    # test_check_exams()
