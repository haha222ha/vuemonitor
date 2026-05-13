import os, sys
_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "shared"))
if _root not in sys.path:
    sys.path.insert(0, _root)
