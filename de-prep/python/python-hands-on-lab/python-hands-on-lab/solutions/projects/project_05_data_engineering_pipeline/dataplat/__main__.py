"""Allow `python -m dataplat ...`."""
import sys

from .cli import main

sys.exit(main())
