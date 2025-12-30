import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from bot import run_live_signal_filters
from bot.config.utils import read_tickers
from bot.rules.initial_filter import return_filter, volume_filter
from bot.rules.signal_filter import (breakout, volume_breakout)

tickers = read_tickers()

run_live_signal_filters(
    tickers, 
    initial_filters=[return_filter, volume_filter],
    signal_filters=[breakout, volume_breakout],
    schedule_minutes=[0, 30],
    rerun_once_first=True # run once and then schedule
)