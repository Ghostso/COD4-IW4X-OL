import sys
sys.stdout.reconfigure(encoding='utf-8')
from pathlib import Path
path = Path(r'COD OL\IIPS\iips.dll')
text = path.read_bytes()
for start in [0x33f60, 0x365e0, 0x37310]:
    chunk = text[start:start+200]
    print('---', hex(start), '---')
    print(chunk.decode('utf-16le','ignore'))
