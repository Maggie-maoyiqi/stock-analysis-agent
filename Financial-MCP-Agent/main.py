import asyncio
import sys
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.services.analysis_service import run_analysis_workflow  # noqa: E402
from src.utils.logging_config import ERROR_ICON, SUCCESS_ICON, setup_logger  # noqa: E402

load_dotenv()
logger = setup_logger(__name__)


async def run_analysis(query: str) -> str:
    """运行股票分析。"""
    final_state = await run_analysis_workflow(query)
    report = final_state.get("final_report", "报告生成失败")

    print("\n" + "=" * 80)
    print("📊 股票分析报告")
    print("=" * 80)
    print(report)
    print("=" * 80)
    print("⚠️ 免责声明: 本报告仅供参考，不构成投资建议。")

    if final_state.get("report_file"):
        logger.info("%s 报告文件: %s", SUCCESS_ICON, final_state["report_file"])

    if final_state.get("errors"):
        logger.warning("%s 运行中存在问题: %s", ERROR_ICON, "; ".join(final_state["errors"]))

    return report


def main():
    """主函数。"""
    import argparse

    parser = argparse.ArgumentParser(description="A股智能分析系统")
    parser.add_argument("--command", "-c", type=str, help="分析命令，如 '帮我分析茅台'")
    parser.add_argument("--interactive", "-i", action="store_true", help="交互模式")
    args = parser.parse_args()

    if args.interactive:
        print("A股智能分析系统 (输入 'exit' 退出)")
        print("-" * 40)
        while True:
            query = input("\n请输入问题: ").strip()
            if query.lower() in ["exit", "quit", "q"]:
                break
            if query:
                asyncio.run(run_analysis(query))
    elif args.command:
        asyncio.run(run_analysis(args.command))
    else:
        asyncio.run(run_analysis("帮我分析贵州茅台(600519)这只股票值得投资吗"))


if __name__ == "__main__":
    main()
