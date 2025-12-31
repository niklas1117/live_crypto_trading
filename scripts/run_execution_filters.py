import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from bot import run_live_entry_filters_and_execute_trades
from bot.rules.execution_filter import upper_donchian_breach

run_live_entry_filters_and_execute_trades(
    return_based_entry_filters=[upper_donchian_breach],
)