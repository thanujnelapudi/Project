import os
import glob
from datetime import datetime

files = glob.glob('uploads/*')
files.sort(key=os.path.getmtime, reverse=True)
for f in files[:5]:
    mtime = datetime.fromtimestamp(os.path.getmtime(f))
    print(f"{mtime} - {f}")

