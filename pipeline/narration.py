#!/usr/bin/env python3
"""Narration stage. Implementation: stage_narration.py."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from stage_narration import main

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--self-check":
        from stage_narration import _self_check

        _self_check()
    else:
        sys.exit(main())
