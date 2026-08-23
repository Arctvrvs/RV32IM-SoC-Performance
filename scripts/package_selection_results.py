#!/usr/bin/env python3
from __future__ import print_function
import os,zipfile
ROOT=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
out=os.path.join(ROOT,'RV32IM_Milestone8C_Architecture_Selection_Results.zip')
skip={os.path.basename(out)}
with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED) as z:
    for base,dirs,files in os.walk(ROOT):
        dirs[:]=[d for d in dirs if d!='__pycache__']
        for name in files:
            if name in skip or name.endswith('.pyc'): continue
            p=os.path.join(base,name)
            z.write(p,os.path.relpath(p,ROOT))
print(out)
