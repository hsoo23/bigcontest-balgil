"""발길 에이전트 주간 브리핑을 돌린다 (D1).

실행: python scripts/run_agent.py --as-of 2025-10-14 [--roster 명부.csv] [--top 3]
입력 형식: docs/agent_입력형식.md
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from balgil.agent import main  # noqa: E402

if __name__ == "__main__":
    main()
