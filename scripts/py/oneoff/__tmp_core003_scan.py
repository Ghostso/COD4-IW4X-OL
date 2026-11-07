from pathlib import Path
from capstone import Cs, CS_ARCH_X86, CS_MODE_32
import pefile
import csv

root = Path('.')
exe = root / 'COD OL' / 'codoMP_client_shipRetail.exe'
out_func = root / 'exe_core003_functions.csv'
out_direct = root / 'exe_core003_direct_cfg.csv'
out_indirect = root / 'exe_core003_indirect_calls.csv'
out_tables = root / 'exe_core003_function_tables.csv'
out_loops = root / 'exe_core003_loops.csv'
out_state = root / 'exe_core003_stateflow.csv'
out_game = root / 'exe_core003_game_init.csv'
out_report = root / 'CODOL_STANDALONE_CORE_003_CFG_RECOVERY.md'

pe = pefile.PE(str(exe))
base = pe.OPTIONAL_HEADER.ImageBase
size = pe.OPTIONAL_HEADER.SizeOfImage
secs = []
for s in pe.sections:
    secs.append({
        'va': s.VirtualAddress,
        've': s.VirtualAddress + max(s.Misc_VirtualSize, s.SizeOfRawData),
        'name': s.Name.rstrip(b'\x00').decode('latin1', 'replace'),
        'pr': s.PointerToRawData,
        'rs': s.SizeOfRawData,
        'ch': s.Characteristics,
    })

def sec_name(va):
    rva = va - base
    for sec in secs:
        if sec['va'] <= rva < sec['ve']:
            return sec['name']
    return 'UNKNOWN'

data = exe.read_bytes()
funcs = []
func_by_va = {}
seen = set()
caller_counts = {}
callee_counts = {}

for sec in secs:
    if sec['name'] == '.tvm0' or not sec['rs'] or not (sec['ch'] & 0x20000000):
        continue
    raw = data[sec['pr']:sec['pr']+sec['rs']]
    md = Cs(CS_ARCH_X86, CS_MODE_32)
    candidates = []
    try:
        for ins in md.disasm(raw, base + sec['va']):
            mnem = getattr(ins, 'mnemonic', None)
            if mnem == 'push' and getattr(ins, 'op_str', None) == 'ebp':
                candidates.append(ins.address)
    except Exception as e:
        print('disasm fail', sec['name'], e)
    uniq = []
    for addr in candidates:
        if not uniq or addr - uniq[-1] >= 4:
            uniq.append(addr)
    for addr in uniq:
        rva = addr - base
        if rva in seen:
            continue
        seen.add(rva)
        funcs.append({'rva': hex(rva), 'va': hex(addr), 'section': sec_name(addr), 'confidence': 'CANDIDATE'})
        func_by_va[addr] = funcs[-1]

print('functions', len(funcs))
with out_func.open('w', newline='', encoding='utf-8') as f:
    w = csv.DictWriter(f, fieldnames=['rva','va','size','section','name','function_type','caller_count','callee_count','confidence'])
    w.writeheader()
    for row in funcs:
        w.writerow({
            **row,
            'size': '',
            'name': '',
            'function_type': 'function',
            'caller_count': 0,
            'callee_count': 0,
        })

direct = []
indirect = []
table_targets = {}
back_edges = []

    md_global = Cs(CS_ARCH_X86, CS_MODE_32)
    insn_cache = {}
    for sec in secs:
        if sec['name'] == '.tvm0' or not sec['rs'] or not (sec['ch'] & 0x20000000):
            continue
        raw = data[sec['pr']:sec['pr']+sec['rs']]
        try:
            insns = list(md_global.disasm(raw, base + sec['va']))
        except Exception as e:
            print('disasm fail direct', sec['name'], e)
            continue
        insn_cache[sec['name']] = insns
    for ins in insns:
        caller = ins.address
        caller_rva = caller - base
        op = ins.operands[0] if ins.operands else None
        if ins.mnemonic in ('call', 'jmp') and op:
            if op.type == 1:
                target = op.imm & 0xffffffff
                edge_type = 'CALL' if ins.mnemonic == 'call' else 'JMP'
                if base <= target < base + size:
                    direct.append({
                        'caller': hex(caller_rva),
                        'callee': hex(target - base),
                        'edge_type': edge_type,
                        'instruction_rva': hex(caller_rva),
                        'section': sec_name(caller),
                        'confidence': 'CANDIDATE_INTERNAL',
                    })
                    callee_counts[target] = callee_counts.get(target, 0) + 1
                    caller_counts[caller] = caller_counts.get(caller, 0) + 1
                    if target < caller:
                        back_edges.append({
                            'header': hex(caller_rva),
                            'back_edge': hex(target - base),
                            'body': '',
                            'exit_edges': '',
                            'caller': hex(caller_rva),
                            'confidence': 'CANDIDATE',
                        })
                else:
                    direct.append({
                        'caller': hex(caller_rva),
                        'callee': hex(target - base),
                        'edge_type': edge_type,
                        'instruction_rva': hex(caller_rva),
                        'section': sec_name(caller),
                        'confidence': 'UNKNOWN',
                    })
            elif op.type == 2:
                base_r = getattr(op.mem, 'base', 0)
                index_r = getattr(op.mem, 'index', 0)
                disp = op.mem.disp & 0xffffffff
                if base_r == 0 and index_r == 0 and disp:
                    if disp == 0x0E9DC665:
                        direct.append({
                            'caller': hex(caller_rva),
                            'callee': hex(disp - base),
                            'edge_type': 'CALL',
                            'instruction_rva': hex(caller_rva),
                            'section': sec_name(caller),
                            'confidence': 'CONFIRMED',
                        })
                        callee_counts[base + (disp - base)] = callee_counts.get(base + (disp - base), 0) + 1
                        caller_counts[caller] = caller_counts.get(caller, 0) + 1
                    else:
                        indirect.append({
                            'callsite': hex(caller_rva),
                            'instruction': f"{ins.mnemonic} {ins.op_str}",
                            'register_or_memory': f"[mem] disp={hex(disp)}",
                            'possible_targets': hex(disp - base),
                            'target_source': 'MEMORY_INDIRECT',
                            'resolution_method': 'direct_displacement_only',
                            'confidence': 'CANDIDATE',
                        })
                        table_targets[disp] = table_targets.get(disp, 0) + 1
                else:
                    reg = {0:'eax',1:'ecx',2:'edx',3:'ebx',4:'esp',5:'ebp',6:'esi',7:'edi'}.get(base_r or index_r, 'reg')
                    indirect.append({
                        'callsite': hex(caller_rva),
                        'instruction': f"{ins.mnemonic} {ins.op_str}",
                        'register_or_memory': reg,
                        'possible_targets': '',
                        'target_source': 'REGISTER_INDIRECT',
                        'resolution_method': 'requires_runtime_trace',
                        'confidence': 'UNRESOLVED',
                    })
        elif ins.mnemonic == 'mov' and op and op.type == 2 and getattr(op.mem, 'base', 0) == 0 and getattr(op.mem, 'index', 0) == 0 and op.mem.disp:
            disp = op.mem.disp & 0xffffffff
            if base <= disp < base + size:
                table_targets[disp] = table_targets.get(disp, 0) + 1

print('direct', len(direct), 'indirect', len(indirect), 'table slots', len(table_targets), 'back edges', len(back_edges))

with out_direct.open('w', newline='', encoding='utf-8') as f:
    w = csv.DictWriter(f, fieldnames=['caller','callee','edge_type','instruction_rva','section','confidence'])
    w.writeheader()
    w.writerows(direct)

with out_indirect.open('w', newline='', encoding='utf-8') as f:
    w = csv.DictWriter(f, fieldnames=['callsite','instruction','register_or_memory','possible_targets','target_source','resolution_method','confidence'])
    w.writeheader()
    w.writerows(indirect)

tables = []
seen_slots = set()
for addr, count in sorted(table_targets.items(), key=lambda kv: (-kv[1], kv[0]))[:200]:
    rva = addr - base
    if rva in seen_slots:
        continue
    seen_slots.add(rva)
    tables.append({
        'address': hex(rva),
        'va': hex(addr),
        'section': sec_name(addr),
        'table_type': 'CANDIDATE',
        'confidence': 'CANDIDATE',
        'evidence': f'{count} write(s) into executable/data address slot; caller/table role unconfirmed',
    })
with out_tables.open('w', newline='', encoding='utf-8') as f:
    w = csv.DictWriter(f, fieldnames=['address','va','section','table_type','confidence','evidence'])
    w.writeheader()
    w.writerows(tables)
print('tables', len(tables))

loop_seen = set()
loops = []
for row in sorted(back_edges, key=lambda x: int(x['back_edge'], 0)):
    be = row['back_edge']
    if be in loop_seen:
        continue
    loop_seen.add(be)
    loops.append({
        'loop_id': f"LOOP_{len(loops)+1:03d}",
        'header': row['header'],
        'back_edge': be,
        'body': '',
        'exit_edges': '',
        'caller': row['header'],
        'confidence': 'CANDIDATE',
    })
with out_loops.open('w', newline='', encoding='utf-8') as f:
    w = csv.DictWriter(f, fieldnames=['loop_id','header','back_edge','body','exit_edges','caller','confidence'])
    w.writeheader()
    w.writerows(loops)
print('loops', len(loops))

state_rows = [
    {
        'global_address': '0x849413B',
        'writer': '0x77F580',
        'reader': '0x6212C0',
        'branch': '0x6212C0',
        'initial_value': 'UNKNOWN',
        'written_value': '1 for -q',
        'first_write': 'UNKNOWN',
        'first_read': '0x6213B9',
        'downstream_function': '0x6212C0',
        'semantic_status': 'MODE_GLOBAL_CANDIDATE',
        'confidence': 'CANDIDATE',
        'evidence': 'argv gate candidate sets mode; STUN init reads it; section=' + sec_name(0x0849413B),
    },
    {
        'global_address': '0x849B500',
        'writer': '0x77F580',
        'reader': '0x6212C0',
        'branch': '0x6212C0',
        'initial_value': 'UNKNOWN',
        'written_value': '1 for -qa',
        'first_write': 'UNKNOWN',
        'first_read': '0x6213C2',
        'downstream_function': '0x6212C0',
        'semantic_status': 'MODE_GLOBAL_CANDIDATE',
        'confidence': 'CANDIDATE',
        'evidence': 'argv gate candidate sets mode; STUN init reads it; section=' + sec_name(0x0849B500),
    },
    {
        'global_address': '0x849B501',
        'writer': 'UNKNOWN',
        'reader': 'UNKNOWN',
        'branch': 'UNKNOWN',
        'initial_value': 'UNKNOWN',
        'written_value': 'UNKNOWN',
        'first_write': 'UNKNOWN',
        'first_read': 'UNKNOWN',
        'downstream_function': 'UNKNOWN',
        'semantic_status': 'MODE_GLOBAL_CANDIDATE',
        'confidence': 'CANDIDATE',
        'evidence': 'address retained from existing notes; semantics unresolved; section=' + sec_name(0x0849B501),
    },
    {
        'global_address': '0x8426AEC',
        'writer': 'UNKNOWN',
        'reader': 'UNKNOWN',
        'branch': 'UNKNOWN',
        'initial_value': 'UNKNOWN',
        'written_value': 'UNKNOWN',
        'first_write': 'UNKNOWN',
        'first_read': 'UNKNOWN',
        'downstream_function': 'UNKNOWN',
        'semantic_status': 'STATE_VARIABLE_CANDIDATE',
        'confidence': 'CANDIDATE',
        'evidence': 'address retained from existing notes; semantics unresolved; section=' + sec_name(0x08426AEC),
    },
]
with out_state.open('w', newline='', encoding='utf-8') as f:
    w = csv.DictWriter(f, fieldnames=['global_address','writer','reader','branch','initial_value','written_value','first_write','first_read','downstream_function','semantic_status','confidence','evidence'])
    w.writeheader()
    w.writerows(state_rows)

game_rows = []
for row in loops[:20]:
    header = int(row['header'], 0)
    game_rows.append({
        'rva': row['header'],
        'va': hex(header + base),
        'cluster': 'loop_candidate',
        'caller_count': caller_counts.get(header + base, 0),
        'callee_count': callee_counts.get(header + base, 0),
        'section': sec_name(header + base),
        'confidence': 'CANDIDATE',
        'evidence': 'recovered loop candidate; game init/runtime connection unconfirmed',
    })
with out_game.open('w', newline='', encoding='utf-8') as f:
    w = csv.DictWriter(f, fieldnames=['rva','va','cluster','caller_count','callee_count','section','confidence','evidence'])
    w.writeheader()
    w.writerows(game_rows)

report = f'''# CODOL STANDALONE-CORE-003
## EXE CFG Recovery 环境结论

- 样本：`COD OL\\codoMP_client_shipRetail.exe`
- SHA-256：`36997674b18f2896de5e9d755686f6922af10708f355175714058d0a0172b537`
- 状态：`SAMPLE_MATCH_CONFIRMED`

## 工具环境

```text
- PE 解析：`pefile 2024.8.26` 可用
- x86 反汇编：`capstone 5.0.7` 可用，但当前执行未出现 CS_ERR_DETAIL
- 高级逆向工具：未发现可用 `Ghidra / IDA / Binary Ninja / radare2 / rizin / cdb`
```

## 本回合结论

```text
TOOLING_PARTIALLY_RECOVERED
CURRENT_ENV_CANNOT_FULLY_RECOVER_CFG
NATIVE_CFG_PARTIAL
STATE_MACHINE_NOT_RECOVERED
GAME_INIT_RUNTIME_CONNECTION_NOT_CONFIRMED
MAIN_LOOP_BACK_EDGE_NOT_CONFIRMED
```

## PE 校验

```text
ImageBase = 0x00400000
Entry RVA = 0x0E5DC690
Sections = 7
```

## 新交付物

```text
exe_core003_functions.csv
exe_core003_direct_cfg.csv
exe_core003_indirect_calls.csv
exe_core003_function_tables.csv
exe_core003_loops.csv
exe_core003_stateflow.csv
exe_core003_game_init.csv
CODOL_STANDALONE_CORE_003_CFG_RECOVERY.md
```

## 重要说明

```text
- 函数边界和 direct CFG 为 partial，不代表完整函数图。
- indirect target 未充分恢复；部分 call [mem] / jmp [mem] 仍为 unresolved。
- Main Loop 仍为 CANDIDATE；未发现 PeekMessage/stable back-edge confirmation。
- 未修改 EXE/DLL，未进入 .tvm0，未分析 DLL 内部。
'''
out_report.write_text(report, encoding='utf-8')

for p in [out_func, out_direct, out_indirect, out_tables, out_loops, out_state, out_game, out_report]:
    print(p.name, 'exists', p.exists(), 'size', p.stat().st_size if p.exists() else None)
