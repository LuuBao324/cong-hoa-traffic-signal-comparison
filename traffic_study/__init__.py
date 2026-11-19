"""Cong Hoa traffic simulation and paired signal-control experiments."""

from importlib.metadata import PackageNotFoundError, distribution
import sys

# A system SUMO PYTHONPATH can otherwise shadow the versions installed in the venv.
try:
    _library_root = str(distribution("sumolib").locate_file(""))
except PackageNotFoundError:
    _library_root = None
if _library_root in sys.path:
    sys.path.remove(_library_root)
    sys.path.insert(0, _library_root)
