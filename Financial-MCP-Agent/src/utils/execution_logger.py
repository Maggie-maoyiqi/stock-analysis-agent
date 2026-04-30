"""执行日志记录。"""
import json
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]


class ExecutionLogger:
    """记录Agent执行过程。"""

    def __init__(self, log_dir: str = "logs"):
        self.log_dir = (PROJECT_ROOT / log_dir).resolve()
        self.log_dir.mkdir(exist_ok=True)

    def log_interaction(self, agent_name: str, input_data: dict, output_data: dict, duration: float):
        """记录LLM交互。"""
        log_file = self.log_dir / f"{agent_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        payload = {
            "agent": agent_name,
            "timestamp": datetime.now().isoformat(),
            "input": input_data,
            "output": output_data,
            "duration_seconds": duration,
        }
        log_file.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def get_execution_logger():
    """获取执行日志记录器实例。"""
    return ExecutionLogger()
