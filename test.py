"""
Because of the automatic file discovery that happens in QAI,
PYTHONPATH is wrong if you `python -m pytest`
so run `python test.py` with test.py in the root and then it works
"""

import pytest

pytest.main()