import json
import os
import tempfile
from datetime import datetime
from pathlib import Path

LOGS_DIR = Path(os.path.join(tempfile.gettempdir(), "glowai_logs"))

try:
    LOGS_DIR.mkdir(exist_ok=True)
except Exception:
    pass


class Logger:
    def __init__(self, session_id: str = "default"):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.session_id = session_id
        self.log_path = LOGS_DIR / f"session_{timestamp}.log"
        self.entries: list = []

    def log_turn(
        self,
        turn: int,
        input: str,
        tools_used: list,
        result: str,
        final_answer: str,
    ):
        entry = {
            "turn": turn,
            "timestamp": datetime.now().isoformat(),
            "input": input,
            "tools_used": tools_used,
            "result": result[:500],
            "final_answer": final_answer[:500],
        }
        self.entries.append(entry)

        line = json.dumps(entry, ensure_ascii=False)
        with open(self.log_path, "a", encoding="utf-8") as f:
            f.write(line + "\n")

    def save(self):
        summary = {
            "session_id": self.session_id,
            "started_at": datetime.now().isoformat(),
            "total_turns": len(self.entries),
        }
        summary_path = LOGS_DIR / f"summary_{self.session_id}.json"
        with open(summary_path, "w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)


def get_logger(session_id: str = "default") -> Logger:
    return Logger(session_id=session_id)