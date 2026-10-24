"""Compatibility entry point for the v0.21 impact bank."""
from pathlib import Path
import runpy
runpy.run_path(str(Path(__file__).with_name("prepare_sfx_bank.py")),run_name="__main__")
