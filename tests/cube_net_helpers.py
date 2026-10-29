"""Compatibility import for the shared exact cube-folding implementation."""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from cube_folding import fold_cube_net, free_polyominoes
