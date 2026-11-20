"""Entry point: python main.py --input ../../datasets/incoming --output output/"""
import sys

from csv_etl.cli import main

if __name__ == "__main__":
    sys.exit(main())
