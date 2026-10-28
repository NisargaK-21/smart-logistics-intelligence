import sys
from pathlib import Path

# Ensure project root is in sys.path so 'backend.app...' is always importable
root_dir = Path(__file__).resolve().parent.parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))
