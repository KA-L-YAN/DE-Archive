"""Entry point: python main.py run --input ../../datasets/daily --warehouse warehouse --state state/state.json"""
import sys

from incremental_etl.cli import main

if __name__ == "__main__":
    sys.exit(main())
