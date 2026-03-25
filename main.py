"""ASIN 智能健康度分析平台 — 命令行交互入口。

用法: uv run python main.py
"""

from __future__ import annotations

import sys

from src.agents.supervisor_agent import create_supervisor_agent


def main() -> None:
    print("=" * 60)
    print("  ASIN 智能健康度分析平台")
    print("  Multi-Agent 系统 (Strands Agents SDK)")
    print("=" * 60)
    print()
    print("正在初始化 Supervisor Agent...")

    try:
        supervisor = create_supervisor_agent()
    except Exception as e:
        print(f"Agent 初始化失败: {e}")
        print("请检查 AWS Bedrock 凭证和区域配置。")
        sys.exit(1)

    print("初始化完成！输入问题开始分析（输入 quit 退出）")
    print()
    print("示例问题:")
    print("  - 查询 B000000008 的健康度评分")
    print("  - 帮我全面分析 B000000000 的状态")
    print("  - 列出所有危险状态的 ASIN")
    print("  - 当前整体 ASIN 健康度如何")
    print("  - 退货率高应该怎么处理")
    print("-" * 60)

    while True:
        try:
            user_input = input("\n你: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n再见！")
            break

        if not user_input:
            continue
        if user_input.lower() in ("quit", "exit", "q"):
            print("再见！")
            break

        try:
            response = supervisor(user_input)
            print(f"\n助手: {response}")
        except Exception as e:
            print(f"\n处理出错: {e}")


if __name__ == "__main__":
    main()
