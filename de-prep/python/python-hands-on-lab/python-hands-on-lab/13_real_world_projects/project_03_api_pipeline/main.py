"""Entry point: python main.py --output output/ [--fail-rate 0.1] [--base-url http://127.0.0.1:8765/v1]"""
import sys

from api_ingest.cli import main

if __name__ == "__main__":
    sys.exit(main())
