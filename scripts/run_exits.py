import sys
from pathlib import Path


# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from bot.trade_live import run_live_exit_filters_and_execute_exits

run_live_exit_filters_and_execute_exits(
    exit_filters=[],
    schedule_minutes=[0, 30],
    rerun_once_first=True # run once and then schedule
)