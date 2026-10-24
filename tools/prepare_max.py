"""Compatibility entry point: prepare the original SoR2 Max, including combat data."""
from pathlib import Path
import runpy,sys
p=Path(__file__).resolve().parents[1]
if '--asm'not in sys.argv:sys.argv+=['--asm',str(p/'original/vendor/SOR2.asm')]
runpy.run_path(str(p/'tools/prepare_max_sor2.py'),run_name='__main__')
