"""Allow `python -m dataplat ...`.

STARTER FILE — implement every function that raises NotImplementedError.
Signatures and docstrings are the contract; the tests in tests/projects/ check it.
"""
import sys
from .cli import main
sys.exit(main())
