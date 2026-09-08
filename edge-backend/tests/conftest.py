import sys
from pathlib import Path


EDGE_BACKEND = Path(__file__).resolve().parents[1]
if str(EDGE_BACKEND) not in sys.path:
    sys.path.insert(0, str(EDGE_BACKEND))
