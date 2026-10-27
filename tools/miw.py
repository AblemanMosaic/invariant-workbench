#!/usr/bin/env python3
"""Local launcher. No implicit package installation, network calls or auto-upgrades."""
from pathlib import Path
import sys
sys.dont_write_bytecode = True
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'src'),str(ROOT/'vendor/ucm'),str(ROOT/'vendor/mosaic')]
if __name__=='__main__':
    from miw.cli import main
    raise SystemExit(main())
