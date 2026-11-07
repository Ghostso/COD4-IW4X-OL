from pathlib import Path
import csv
root=Path('.')
out=root/'exe_dynamic_loads.csv'
header=['exe_rva','api','argument_source','dll_name_if_provable','symbol_if_provable','result_usage','confidence','evidence']
rows=[
    ['','LoadLibraryA/W','no proven EXE native call site in scanned native regions','','','','UNKNOWN',''],
    ['','LoadLibraryExA/W','no proven EXE native call site in scanned native regions','','','','UNKNOWN',''],
    ['','GetProcAddress','no proven EXE native call site in scanned native regions','','','','UNKNOWN','']
]
with out.open('w',newline='',encoding='utf-8') as f:
    w=csv.writer(f); w.writerow(header); w.writerows(rows)
print(out, len(rows))
