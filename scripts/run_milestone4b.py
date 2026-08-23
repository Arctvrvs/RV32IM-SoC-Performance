#!/usr/bin/env python3
from __future__ import print_function
import os, subprocess, sys
ROOT=os.path.abspath(os.path.join(os.path.dirname(__file__),'..'))
cmd=[sys.executable, os.path.join('scripts','run_milestone4.py')] + sys.argv[1:]
raise SystemExit(subprocess.call(cmd, cwd=ROOT))
