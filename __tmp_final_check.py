from pathlib import Path
import csv
root=Path('.')
files = {
    'exe_external_calls.csv': ['exe_rva','instruction_bytes','instruction_type','target','target_module','target_symbol_or_ordinal','edge_type','evidence','confidence','section','notes'],
    'exe_iat_external.csv': ['exe_rva','instruction_bytes','instruction_type','target','target_module','target_symbol_or_ordinal','edge_type','evidence','confidence','section','notes'],
    'exe_non_iat_external.csv': ['exe_rva','instruction_bytes','instruction_type','target','target_module','target_symbol_or_ordinal','edge_type','evidence','confidence','section','notes'],
    'exe_dynamic_loads.csv': ['exe_rva','api','argument_source','dll_name_if_provable','symbol_if_provable','result_usage','confidence','evidence'],
    'exe_external_symbols.csv': ['exe_rva','instruction_type','target','target_module','target_symbol_or_ordinal','edge_type','confidence','evidence'],
    'exe_external_boundary_graph.csv': ['source','target_type','target','symbol_or_ordinal','confidence','notes'],
}
for name, headers in files.items():
    p=root/name
    with p.open('r',encoding='utf-8',newline='') as f:
        reader=csv.DictReader(f)
        assert list(reader.fieldnames)==headers, (name, reader.fieldnames, headers)
        rows=list(reader)
    print(name, len(rows))
