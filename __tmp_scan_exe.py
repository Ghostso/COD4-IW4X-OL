from pathlib import Path
import csv
from capstone import Cs, CS_ARCH_X86, CS_MODE_32
import pefile

root = Path('.')
exe = root / 'COD OL' / 'codoMP_client_shipRetail.exe'
out_dir = root
out_iat = out_dir / 'exe_iat_external.csv'
out_niat = out_dir / 'exe_non_iat_external.csv'
out_all = out_dir / 'exe_external_calls.csv'

KNOWN_IAT = {0xE9DC665: ('codoMP_client_shipRetailBase.dll', 'ordinal_1')}

data = exe.read_bytes()
pe = pefile.PE(data=data, fast_load=True)
base = pe.OPTIONAL_HEADER.ImageBase
size = pe.OPTIONAL_HEADER.SizeOfImage
secs = []
for s in pe.sections:
    secs.append((s.VirtualAddress, s.VirtualAddress + max(s.Misc_VirtualSize, s.SizeOfRawData),
                 s.Name.rstrip(b'\x00').decode('latin1', 'replace'),
                 s.PointerToRawData, s.SizeOfRawData, s.Characteristics))

def sec_name(va):
    rva = va - base
    for va_s, ve_s, nm, *_ in secs:
        if va_s <= rva < ve_s:
            return nm
    return '?'

def resolve_import_target(disp):
    if disp in KNOWN_IAT:
        return KNOWN_IAT[disp]
    return None

header_fields = [
    'exe_rva','instruction_bytes','instruction_type','target','target_module','target_symbol_or_ordinal',
    'edge_type','evidence','confidence','section','notes'
]
all_rows=[]
iat_rows=[]
noniat_rows=[]

md = Cs(CS_ARCH_X86, CS_MODE_32)
for va,ve,nm,rs,pr,ch in [(va,ve,nm,rs,pr,ch) for va,ve,nm,rs,pr,ch in secs if rs]:
    raw = data[pr:pr+rs]
    for ins in md.disasm(raw, base+va):
        mnem = ins.mnemonic
        op_str = ins.op_str
        bytes_ = ins.bytes.hex(' ')
        rva = ins.address - base
        row = {
            'exe_rva': hex(rva),
            'instruction_bytes': bytes_,
            'instruction_type': '',
            'target': '',
            'target_module': '',
            'target_symbol_or_ordinal': '',
            'edge_type': 'INTERNAL_OR_UNKNOWN_INDIRECT',
            'evidence': '',
            'confidence': 'UNKNOWN',
            'section': sec_name(ins.address),
            'notes': ''
        }
        handled = False
        if mnem == 'call' and op_str.startswith('dword ptr ['):
            disp = int(op_str.split('[')[1].split(']')[0], 0) & 0xffffffff
            resolved = resolve_import_target(disp)
            row['instruction_type'] = 'call [disp32]'
            row['target'] = hex(disp)
            if resolved:
                row['target_module'] = resolved[0]
                row['target_symbol_or_ordinal'] = resolved[1]
                row['edge_type'] = 'EXTERNAL_IAT'
                row['evidence'] = 'static import slot / custom binding to Base export'
                row['confidence'] = 'CONFIRMED'
            else:
                row['evidence'] = 'indirect memory call; unresolved non-IAT target'
                row['confidence'] = 'UNKNOWN'
            handled = True
        elif mnem == 'jmp' and op_str.startswith('dword ptr ['):
            disp = int(op_str.split('[')[1].split(']')[0], 0) & 0xffffffff
            row['instruction_type'] = 'jmp [disp32]'
            row['target'] = hex(disp)
            row['evidence'] = 'indirect memory jmp; no resolved external target'
            row['confidence'] = 'UNKNOWN'
            handled = True
        elif mnem in ('call','jmp') and not op_str.startswith('dword ptr ['):
            try:
                target = int(op_str.split()[0], 0) & 0xffffffff
            except Exception:
                target = None
            if target is not None:
                row['instruction_type'] = mnem + ' imm32'
                row['target'] = hex(target)
                if base <= target < base + size:
                    row['edge_type'] = 'INTERNAL_OR_UNKNOWN_ABSOLUTE'
                    row['evidence'] = 'absolute target inside EXE image range'
                    row['confidence'] = 'CANDIDATE_INTERNAL'
                else:
                    row['edge_type'] = 'INTERNAL_OR_UNKNOWN_ABSOLUTE'
                    row['evidence'] = 'absolute target outside proven EXE import path'
                    row['confidence'] = 'UNKNOWN'
                handled = True
        if not handled:
            continue
        all_rows.append(row)
        if row['edge_type'] == 'EXTERNAL_IAT':
            iat_rows.append(row)
        else:
            noniat_rows.append(row)

entry_row = {
    'exe_rva': '0xE5DC690',
    'instruction_bytes': 'ff 15 65 c6 9d 0e',
    'instruction_type': 'call [0x0E9DC665]',
    'target': '0x0E9DC665',
    'target_module': 'codoMP_client_shipRetailBase.dll',
    'target_symbol_or_ordinal': 'ordinal_1',
    'edge_type': 'EXTERNAL_IAT',
    'evidence': 'entry indirect thunk to Base+0x1D6582C ordinal 1; static custom binding at 0x0E9DC635; import directory size 0 but pefile reports this single slot',
    'confidence': 'CONFIRMED',
    'section': '.tp3',
    'notes': 'CONFIRMED_EXTERNAL_BOUNDARY stop here'
}
all_rows.insert(0, entry_row)
iat_rows.insert(0, entry_row)

for path, rows in [(out_all, all_rows), (out_iat, iat_rows), (out_niat, noniat_rows)]:
    with path.open('w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=header_fields)
        w.writeheader()
        w.writerows(rows)
    print(path, len(rows))
