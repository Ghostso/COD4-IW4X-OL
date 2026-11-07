from pathlib import Path
import csv
root=Path('.')
out=root/'exe_external_boundary_graph.csv'
header=['source','target_type','target','symbol_or_ordinal','confidence','notes']
rows=[
    ['codoMP_client_shipRetail.exe','external dll','codoMP_client_shipRetailBase.dll','ordinal_1','CONFIRMED','entry indirect thunk at 0xE5DC690'],
    ['codoMP_client_shipRetail.exe','external dll','UNKNOWN','?','UNKNOWN','unresolved indirect/absolute calls remain'],
    ['codoMP_client_shipRetail.exe','vm boundary','.tvm0','VM_BOUNDARY','UNKNOWN','tvm0 entry/side not analyzed']
]
with out.open('w',newline='',encoding='utf-8') as f:
    w=csv.writer(f); w.writerow(header); w.writerows(rows)
print(out, len(rows))
