#!/usr/bin/env python3
"""Backward-compatible entry point for the BeeChinese OpenHands agent framework."""

import os
from pathlib import Path
import sys
import warnings


ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

os.environ.setdefault("OPENHANDS_SUPPRESS_BANNER", "1")
warnings.simplefilter("ignore", DeprecationWarning)

from beechinese_agent.orchestrator import main


if __name__ == "__main__":
    raise SystemExit(main())
