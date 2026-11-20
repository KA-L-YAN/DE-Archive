"""Entry point: python main.py --input ../../datasets/logs/app.log --output output/"""
import sys

from log_analyzer.cli import main

if __name__ == "__main__":
    sys.exit(main())
