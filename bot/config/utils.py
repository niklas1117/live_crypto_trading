from pathlib import Path
import yaml

BASE_DIR = Path(__file__).resolve().parent

def write_tickers(tickers, filename='tickers.txt'):
    """

    Example
    -------
    .python
    # get all symbol prices and store in config
    prices = client.get_margin_all_pairs()
    write_tickers([p['symbol'] for p in prices if p['symbol'].endswith('USDT')])

    """
    out = BASE_DIR / filename
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open('w', encoding='utf-8') as f:
        for ticker in tickers:
            f.write(f"{ticker}\n")

def read_tickers(filename='tickers.txt'):
    in_file = BASE_DIR / filename
    if not in_file.exists():
        return []
    with in_file.open('r', encoding='utf-8') as f:
        return [line.strip() for line in f]

def read_config(filename='config.yaml'):
    config_file = BASE_DIR / filename
    if not config_file.exists():
        return {}
    with config_file.open('r', encoding='utf-8') as f:
        return yaml.safe_load(f)