from pathlib import Path
path = Path(r'COD OL\IIPS\iips.dll')
text = path.read_bytes()
print(text.count(b'IIPSHostApp.ini'), text.count(b'IIPSHostApp.exe'))
