"""
Pytest config — đảm bảo project root nằm trong sys.path để `import app` chạy được
dù gọi `pytest tests/` trực tiếp (CI) hay `python -m pytest` (local).
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
