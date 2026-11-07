import csv
rows=list(csv.DictReader(open('scripts/_out/ca8000_semantic_refs.csv')))
want={'0x00ca853c','0x00ca8540','0x00ca8548','0x00ca8550','0x00ca84c8','0x00ca8000'}
for r in rows:
    if r['slot'].lower() in want:
        print(r['caller_rva'],r['slot'],r['mnemonic'],r['op_str'],r['bytes'],r['effect'])
