from pathlib import Path
import csv
root=Path('.')
out=root/'exe_external_symbols.csv'
header=['exe_rva','instruction_type','target','target_module','target_symbol_or_ordinal','edge_type','confidence','evidence']
rows=[
    ['0xE5DC690','call [0x0E9DC665]','0x0E9DC665','codoMP_client_shipRetailBase.dll','ordinal_1','EXTERNAL_IAT','CONFIRMED','static custom binding at 0x0E9DC635; import dir size 0; export Base+0x1D6582C']
]
with out.open('w',newline='',encoding='utf-8') as f:
    w=csv.writer(f); w.writerow(header); w.writerows(rows)
print(out, len(rows))
