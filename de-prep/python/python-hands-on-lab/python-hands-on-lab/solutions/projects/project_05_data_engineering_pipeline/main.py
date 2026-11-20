"""Entry point: python main.py --config platform.toml run   (same as python -m dataplat ...)"""
import sys

from dataplat.cli import main

if __name__ == "__main__":
    sys.exit(main())
