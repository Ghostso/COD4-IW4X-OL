from pathlib import Path
import csv
import pefile

root = Path('.')
exe = root / 'COD OL' / 'codoMP_client_shipRetail.exe'
out = root / 'exe_dynamic_loads.csv'
header = ['exe_rva','api','argument_source','dll_name_if_provable','symbol_if_provable','result_usage','confidence','evidence']
rows=[]
data=exe.read_bytes(); pe=pefile.PE(data=data,fast_load=True); base=pe.OPTIONAL_HEADER.ImageBase
terms=[b'LoadLibraryA',b'LoadLibraryW',b'LoadLibraryExA',b'LoadLibraryExW',b'GetProcAddress']
found=False
for term in terms:
    start=0
    count=0
    while True:
        i=data.find(term,start)
        if i<0: break
        found=True
        count+=1
        start=i+1
    print(term.decode('ascii','replace'), count)
print('found_any', found)
