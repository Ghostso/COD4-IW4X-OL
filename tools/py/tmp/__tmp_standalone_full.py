from pathlib import Path
import csv, traceback
from collections import Counter
from capstone import Cs, CS_ARCH_X86, CS_MODE_32
import pefile

root = Path('.')
exe = root / 'COD OL' / 'codoMP_client_shipRetail.exe'
out_runtime = root / 'exe_native_runtime_graph.csv'
out_init = root / 'exe_init_clusters.csv'
out_game = root / 'exe_game_init_candidates.csv'
out_main = root / 'exe_mainloop_structural.csv'
out_renderer = root / 'exe_renderer_candidates.csv'
out_fs = root / 'exe_filesystem_candidates.csv'
out_net = root / 'exe_network_candidates.csv'
out_state = root / 'exe_startup_stateflow.csv'
out_thread = root / 'exe_thread_map.csv'
out_report = root / 'CODOL_STANDALONE_CORE_001_EXE_STARTUP_RECONSTRUCTION.md'

def safe_int(v, default=0):
    try: return int(v, 0)
    except: return default

def safe_read_csv(name, required_fields):
    path = root / name
    if not path.exists():
        return []
    with path.open('r', encoding='utf-8', newline='') as f:
        reader = csv.DictReader(f)
        if reader.fieldnames != required_fields:
            return []
        return list(reader)

# PE basics
data = exe.read_bytes()
pe = pefile.PE(data=data, fast_load=True)
base = pe.OPTIONAL_HEADER.ImageBase
size = pe.OPTIONAL_HEADER.SizeOfImage
secs = []
for s in pe.sections:
    secs.append({
        'name': s.Name.rstrip(b'\x00').decode('latin1', 'replace'),
        'va': s.VirtualAddress,
        've': s.VirtualAddress + max(s.Misc_VirtualSize, s.SizeOfRawData),
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

# Load existing lightweight artifacts
functions = []
for row in safe_read_csv('exe_functions.csv', ['rva','va','size_estimate','section','prologue','epilogue','calling_convention','parameter_count','return_value','caller_count','callee_count','string_referenced','indirect_call','dispatcher_like','confidence']):
    rva = safe_int(row.get('rva', 0), 0)
    if not rva:
        continue
    functions.append({
        'rva': rva,
        'va': base + rva,
        'section': row.get('section', ''),
        'confidence': row.get('confidence', ''),
        'caller_count': safe_int(row.get('caller_count', 0), 0),
        'callee_count': safe_int(row.get('callee_count', 0), 0),
    })
func_by_va = {item['va']: item for item in functions}

callgraph = []
for row in safe_read_csv('exe_callgraph.csv', ['caller_rva','callee_rva','call_type','direct_indirect','confidence','evidence']):
    caller = safe_int(row.get('caller_rva', 0), 0)
    callee = safe_int(row.get('callee_rva', 0), 0)
    if not caller or not callee:
        continue
    callgraph.append({
        'caller_rva': caller,
        'callee_rva': callee,
        'call_type': row.get('call_type', ''),
        'direct_indirect': row.get('direct_indirect', ''),
        'confidence': row.get('confidence', ''),
        'evidence': row.get('evidence', ''),
    })

mainloop = []
for row in safe_read_csv('exe_mainloop_candidates.csv', ['candidate_rva','loop_shape','message_api','render_api','timer_api','confidence','evidence']):
    rva = safe_int(row.get('candidate_rva', 0), 0)
    if not rva:
        continue
    mainloop.append({
        'rva': rva,
        'va': base + rva,
        'loop_shape': row.get('loop_shape', ''),
        'message_api': row.get('message_api', ''),
        'render_api': row.get('render_api', ''),
        'timer_api': row.get('timer_api', ''),
        'confidence': row.get('confidence', ''),
        'evidence': row.get('evidence', ''),
    })

strings = []
for row in safe_read_csv('exe_strings_refs.csv', ['string','rva','count','subsystem_candidate','confidence']):
    strings.append({
        'string': row.get('string', ''),
        'rva': row.get('rva', ''),
        'count': safe_int(row.get('count', 0), 0),
        'subsystem_candidate': row.get('subsystem_candidate', ''),
        'confidence': row.get('confidence', ''),
    })

# 1. Native runtime graph
runtime = []
seen = set()

def add_runtime(edge):
    key = (edge['function_rva'], edge['caller_rva'], edge['callee_rva'], edge['edge_type'])
    if key in seen:
        return
    seen.add(key)
    runtime.append(edge)

# Known external boundary
add_runtime({
    'function_rva': '0xE5DC690',
    'caller_rva': '0xE5DC690',
    'callee_rva': '0xE9DC665',
    'edge_type': 'EXTERNAL_CALL',
    'section': sec_name(0x0E9DC690),
    'global_reads': 0,
    'global_writes': 0,
    'external_dependency': 'codoMP_client_shipRetailBase.dll ordinal_1',
    'confidence': 'CONFIRMED',
    'evidence': 'entry indirect thunk to Base+0x1D6582C ordinal 1; static custom binding at 0x0E9DC635; import dir size 0',
})

# Existing callgraph
for edge in callgraph:
    add_runtime({
        'function_rva': hex(edge['caller_rva'] - base),
        'caller_rva': hex(edge['caller_rva'] - base),
        'callee_rva': hex(edge['callee_rva'] - base),
        'edge_type': 'DIRECT_CALL',
        'section': func_by_va.get(edge['caller_rva'], {}).get('section', sec_name(edge['caller_rva'])),
        'global_reads': 0,
        'global_writes': 0,
        'external_dependency': 'INTERNAL_OR_UNKNOWN',
        'confidence': edge.get('confidence', 'UNKNOWN'),
        'evidence': edge.get('evidence', 'existing callgraph edge'),
    })

# Known unresolved non-IAT indirect/absolute edges from prior EXE external scan
for edge in [
    ('0xE5C8033','0xE5C8033','0xCA8004','INDIRECT_CALL','UNKNOWN','unresolved non-IAT indirect call'),
    ('0xE5C804C','0xE5C804C','0xCA8008','INDIRECT_CALL','UNKNOWN','unresolved non-IAT indirect call'),
    ('0x101B','0x101B','0xfff02da6','DIRECT_CALL','UNKNOWN','absolute target outside proven EXE import path'),
    ('0x1035','0x1035','0x2e2200','DIRECT_CALL','UNKNOWN','absolute target outside proven EXE import path'),
    ('0x8A803D','0x8A803D','0x662c5b78','DIRECT_CALL','UNKNOWN','absolute target outside proven EXE import path'),
    ('0x8A824B','0x8A824B','0xf2c7f9b','DIRECT_CALL','UNKNOWN','absolute target outside proven EXE import path'),
    ('0x8A826F','0x8A826F','0xfa0a58e','DIRECT_CALL','UNKNOWN','absolute target outside proven EXE import path'),
    ('0x8A8337','0x8A8337','0x8ece83bd','DIRECT_CALL','UNKNOWN','absolute target outside proven EXE import path'),
    ('0xA16057','0xA16057','0x12e24354','JUMP','UNKNOWN','absolute target outside proven EXE import path'),
    ('0xA160F5','0xA160F5','0xfe1e765','DIRECT_CALL','UNKNOWN','absolute target outside proven EXE import path'),
    ('0xA16154','0xA16154','0xe1619d','JUMP','UNKNOWN','absolute target inside EXE image range'),
    ('0xA1626D','0xA1626D','0x20e1dfae','DIRECT_CALL','UNKNOWN','absolute target outside proven EXE import path'),
    ('0xE5C805F','0xE5C805F','0xf13afc9','DIRECT_CALL','UNKNOWN','absolute target outside proven EXE import path'),
    ('0xE5C80D6','0xE5C80D6','0x17fc9664','DIRECT_CALL','UNKNOWN','absolute target outside proven EXE import path'),
    ('0xE5C9052','0xE5C9052','0xf6ac91df','DIRECT_CALL','UNKNOWN','absolute target outside proven EXE import path'),
]:
    add_runtime({
        'function_rva': edge[0],
        'caller_rva': edge[1],
        'callee_rva': edge[2],
        'edge_type': edge[3],
        'section': sec_name(safe_int(edge[0], 0) + base) if edge[0] not in {'UNKNOWN',''} else 'UNKNOWN',
        'global_reads': 0,
        'global_writes': 0,
        'external_dependency': 'INTERNAL_OR_UNKNOWN' if edge[3] in {'DIRECT_CALL','JUMP'} else 'UNKNOWN',
        'confidence': 'CANDIDATE_INTERNAL' if edge[3]=='JUMP' else 'UNKNOWN',
        'evidence': edge[5],
    })

with out_runtime.open('w', newline='', encoding='utf-8') as f:
    w = csv.DictWriter(f, fieldnames=['function_rva','caller_rva','callee_rva','edge_type','section','global_reads','global_writes','external_dependency','confidence','evidence'])
    w.writeheader()
    w.writerows(runtime)

# 2. Init clusters
init_rows = []
for item in functions:
    init_rows.append({
        'cluster_id': 'CLSTR_BOOTSTRAP',
        'entry_candidate': '0xE5DC690',
        'member_functions': hex(item['rva']),
        'caller_count': item['caller_count'],
        'callee_count': item['callee_count'],
        'section': item['section'] or sec_name(item['va']),
        'global_writes': 0,
        'thread_creation': 0,
        'external_calls': 1 if item['va'] == 0x0E9DC665 else 0,
        'file_operations': 0,
        'network_operations': 0,
        'renderer_operations': 0,
        'confidence': 'CANDIDATE',
        'evidence': 'plain-text candidate; caller chain incomplete',
    })
for item in mainloop:
    init_rows.append({
        'cluster_id': 'CLSTR_MAINLOOP_CANDIDATE',
        'entry_candidate': hex(item['rva']),
        'member_functions': hex(item['rva']),
        'caller_count': 0,
        'callee_count': 0,
        'section': sec_name(item['va']),
        'global_writes': 0,
        'thread_creation': 0,
        'external_calls': 0,
        'file_operations': 0,
        'network_operations': 0,
        'renderer_operations': 0,
        'confidence': 'CANDIDATE',
        'evidence': 'existing main-loop candidate; loop evidence not confirmed',
    })
for row in strings:
    subs = row.get('subsystem_candidate', '')
    if any(k in subs for k in ['FileSystem','Config','Localization','Window/Input','Network','Renderer','Game','Thread','Command']):
        rva = safe_int(row.get('rva', 0), 0)
        if not rva:
            continue
        init_rows.append({
            'cluster_id': 'CLSTR_STRING_' + subs.replace('/','_').replace(' ','_'),
            'entry_candidate': hex(rva),
            'member_functions': hex(rva),
            'caller_count': 0,
            'callee_count': 0,
            'section': sec_name(base + rva),
            'global_writes': 0,
            'thread_creation': 0,
            'external_calls': 0,
            'file_operations': 1 if 'FileSystem' in subs else 0,
            'network_operations': 1 if 'Network' in subs else 0,
            'renderer_operations': 1 if 'Renderer' in subs else 0,
            'confidence': 'UNKNOWN',
            'evidence': 'string inventory only; caller chain unconfirmed',
        })
with out_init.open('w', newline='', encoding='utf-8') as f:
    w = csv.DictWriter(f, fieldnames=['cluster_id','entry_candidate','member_functions','caller_count','callee_count','section','global_writes','thread_creation','external_calls','file_operations','network_operations','renderer_operations','confidence','evidence'])
    w.writeheader()
    w.writerows(init_rows)

# 3. Game init candidates
game_rows = []
for item in mainloop:
    game_rows.append({
        'rva': hex(item['rva']),
        'va': hex(item['va']),
        'cluster': 'main_loop_candidate',
        'caller_count': 0,
        'callee_count': 0,
        'section': sec_name(item['va']),
        'confidence': 'CANDIDATE',
        'evidence': 'existing main-loop candidate; game-init path unconfirmed',
    })
for row in strings:
    subs = row.get('subsystem_candidate', '')
    if any(k in subs for k in ['Game','Renderer','Network','Main Loop']):
        rva = safe_int(row.get('rva', 0), 0)
        if not rva:
            continue
        game_rows.append({
            'rva': hex(rva),
            'va': hex(base + rva),
            'cluster': subs,
            'caller_count': 0,
            'callee_count': 0,
            'section': sec_name(base + rva),
            'confidence': 'UNKNOWN',
            'evidence': 'string candidate; caller/global dataflow unconfirmed',
        })
with out_game.open('w', newline='', encoding='utf-8') as f:
    w = csv.DictWriter(f, fieldnames=['rva','va','cluster','caller_count','callee_count','section','confidence','evidence'])
    w.writeheader()
    w.writerows(game_rows)

# 4. Main-loop structural candidates
main_rows = []
for item in mainloop:
    main_rows.append({
        'candidate_entry': hex(item['rva']),
        'back_edge': 'UNKNOWN',
        'loop_body': 'UNKNOWN',
        'update_candidate': 'UNKNOWN',
        'render_candidate': 'UNKNOWN',
        'message_candidate': 'UNKNOWN',
        'network_tick_candidate': 'UNKNOWN',
        'sleep_candidate': 'UNKNOWN',
        'global_state_read': 'UNKNOWN',
        'global_state_write': 'UNKNOWN',
        'confidence': 'CANDIDATE',
        'evidence': 'existing candidate; no back-edge confirmed in this pass',
    })
# Lightweight back-edge scan with exception guard
back_edges = []
try:
    md = Cs(CS_ARCH_X86, CS_MODE_32)
    for sec in secs:
        if sec['name'] == '.tvm0' or not sec['rs'] or not (sec['ch'] & 0x20000000):
            continue
        raw = data[sec['pr']:sec['pr']+sec['rs']]
        targets = []
        for ins in md.disasm(raw, base + sec['va']):
            if ins.mnemonic in ('call','jmp') and ins.operands:
                op = ins.operands[0]
                if op.type == 1:
                    tgt = op.imm & 0xffffffff
                    if base <= tgt < base + size:
                        targets.append((ins.address, ins.mnemonic, tgt))
        cnt = Counter(t for _,_,t in targets)
        for addr, mn, tgt in targets:
            if cnt[tgt] >= 2 and tgt < addr:
                back_edges.append({
                    'candidate_entry': hex(addr - base),
                    'back_edge': hex(tgt - base),
                    'loop_body': 'UNKNOWN',
                    'update_candidate': 'UNKNOWN',
                    'render_candidate': 'UNKNOWN',
                    'message_candidate': 'UNKNOWN',
                    'network_tick_candidate': 'UNKNOWN',
                    'sleep_candidate': 'UNKNOWN',
                    'global_state_read': 'UNKNOWN',
                    'global_state_write': 'UNKNOWN',
                    'confidence': 'CANDIDATE',
                    'evidence': f'repeated absolute {mn} to earlier VA; not proven loop entry',
                })
except Exception:
    back_edges = []
for row in back_edges[:50]:
    main_rows.append(row)
with out_main.open('w', newline='', encoding='utf-8') as f:
    w = csv.DictWriter(f, fieldnames=['candidate_entry','back_edge','loop_body','update_candidate','render_candidate','message_candidate','network_tick_candidate','sleep_candidate','global_state_read','global_state_write','confidence','evidence'])
    w.writeheader()
    w.writerows(main_rows)

# 5-9. Renderer / Filesystem / Network / Stateflow / Thread
with out_renderer.open('w', newline='', encoding='utf-8') as f:
    w = csv.DictWriter(f, fieldnames=['rva','va','api_or_string','caller','callee','section','confidence','evidence'])
    w.writeheader()
    w.writerow({'rva':'UNKNOWN','va':'UNKNOWN','api_or_string':'Present/BeginScene/EndScene/D3D device','caller':'UNKNOWN','callee':'UNKNOWN','section':'UNKNOWN','confidence':'UNKNOWN','evidence':'no confirmed renderer call site in EXE plain-text scan'})

with out_fs.open('w', newline='', encoding='utf-8') as f:
    w = csv.DictWriter(f, fieldnames=['rva','va','api_or_string','caller','callee','section','confidence','evidence'])
    w.writeheader()
    w.writerow({'rva':'UNKNOWN','va':'UNKNOWN','api_or_string':'CreateFile/ReadFile/FindFirstFile/fastfile/pak/zone','caller':'UNKNOWN','callee':'UNKNOWN','section':'UNKNOWN','confidence':'UNKNOWN','evidence':'string inventory exists; no confirmed filesystem init chain'})

with out_net.open('w', newline='', encoding='utf-8') as f:
    w = csv.DictWriter(f, fieldnames=['rva','va','api_or_string','caller','callee','section','confidence','evidence'])
    w.writeheader()
    w.writerow({'rva':'0x849413B','va':'0x0849413B','api_or_string':'network candidate','caller':'UNKNOWN','callee':'UNKNOWN','section':sec_name(0x0849413B),'confidence':'UNKNOWN','evidence':'address retained from existing notes; semantics unresolved'})

with out_state.open('w', newline='', encoding='utf-8') as f:
    w = csv.DictWriter(f, fieldnames=['global_address','writer','reader','branch','initial_value','written_value','first_write','first_read','downstream_function','semantic_status','confidence','evidence'])
    w.writeheader()
    w.writerow({'global_address':'UNKNOWN','writer':'UNKNOWN','reader':'UNKNOWN','branch':'UNKNOWN','initial_value':'UNKNOWN','written_value':'UNKNOWN','first_write':'UNKNOWN','first_read':'UNKNOWN','downstream_function':'UNKNOWN','semantic_status':'SEMANTICS_UNRESOLVED','confidence':'UNKNOWN','evidence':'global data attribution not started'})

with out_thread.open('w', newline='', encoding='utf-8') as f:
    w = csv.DictWriter(f, fieldnames=['rva','va','api_or_string','caller','callee','start_address','section','confidence','evidence'])
    w.writeheader()
    w.writerow({'rva':'UNKNOWN','va':'UNKNOWN','api_or_string':'CreateThread/_beginthread/_beginthreadex/NtCreateThreadEx','caller':'UNKNOWN','callee':'UNKNOWN','start_address':'START_ADDRESS_UNKNOWN','section':'UNKNOWN','confidence':'UNKNOWN','evidence':'no proven thread creation site recovered in static scan'})

# 10. Final report
report = f'''# CODOL STANDALONE-CORE-001
## EXE Self-Sufficient Game Startup Reconstruction

- 对象：`codoMP_client_shipRetail.exe`
- 方法：STATIC-FIRST
- 禁止：不进入 `.tvm0`、不进入 DLL 内部、不重复旧地址主线

## Executive Summary

- EXE 是否具有独立 native runtime：`UNKNOWN`；当前只确认一个外部入口，未恢复完整 native runtime。
- EXE 是否存在 Game Init：`UNKNOWN`
- EXE 是否存在 Renderer Init：`UNKNOWN`
- EXE 是否存在 Resource Init：`UNKNOWN`
- EXE 是否存在 Network Init：`UNKNOWN`
- EXE 是否存在 Main Loop：`UNKNOWN`
- 目前能否建立 `START -> INIT -> GAME -> LOOP`：`不能`
- 最终分类：`STARTUP_PATH_SPARSE`

## Confirmed

- `EXE Entry 0xE5DC690 -> call [0x0E9DC665] -> codoMP_client_shipRetailBase.dll ordinal_1`
- 证据：入口间接 thunk、custom binding、Base 导出 `Base+0x1D6582C` 为 `ordinal_1`
- 已生成 `exe_native_runtime_graph.csv` 中唯一 `CONFIRMED` 外部边

## Strong Evidence

- 当前无 strong 闭环证据。

## Candidates

- Bootstrap / Main Loop candidates：`0x77F580 / 0x77F8B3 / 0x4FD9B0 / 0x4FCEE0 / 0x808650 / 0x7E98F0 / 0x6212C0`
- Network candidate：`0x849413B`
- Renderer / Filesystem / Thread / Stateflow：当前均为 `UNKNOWN` 候选

## Unresolved

- unresolved indirect/absolute edges：至少 14 条 unresolved/non-IAT edges
- `.tvm0` 边界未进入，仅记为 `TVM0_BOUNDARY`
- global stateflow：无 writer/reader/branch 闭环
- thread map：无 proven thread creation site
- renderer/filesystem/game init/main loop：无 confirmed structure

## Not Analyzed

- Base.dll internals
- IIPS / TenProxy / TCLS / WeGame internals
- .tvm0 internals
- 任何 DLL 内部实现

## EXE Runtime Architecture

```
ENTRY
  -> Base.dll ordinal_1 : CONFIRMED
NATIVE INIT
  -> UNKNOWN
RUNTIME STATE
  -> UNKNOWN
RESOURCE
  -> UNKNOWN
WINDOW
  -> UNKNOWN
RENDERER
  -> UNKNOWN
NETWORK
  -> UNKNOWN
GAME INIT
  -> UNKNOWN
UPDATE
  -> UNKNOWN
RENDER
  -> UNKNOWN
MAIN LOOP
  -> UNKNOWN
```

## Deliverables

- `exe_native_runtime_graph.csv`
- `exe_init_clusters.csv`
- `exe_game_init_candidates.csv`
- `exe_mainloop_structural.csv`
- `exe_renderer_candidates.csv`
- `exe_filesystem_candidates.csv`
- `exe_network_candidates.csv`
- `exe_startup_stateflow.csv`
- `exe_thread_map.csv`

注意：当前多数工件仍为 `CANDIDATE` / `UNKNOWN`，因为现有静态证据不足；未补全不存在的证据。
'''
out_report.write_text(report, encoding='utf-8')

print('generated')
for name in ['exe_native_runtime_graph.csv','exe_init_clusters.csv','exe_game_init_candidates.csv','exe_mainloop_structural.csv','exe_renderer_candidates.csv','exe_filesystem_candidates.csv','exe_network_candidates.csv','exe_startup_stateflow.csv','exe_thread_map.csv','CODOL_STANDALONE_CORE_001_EXE_STARTUP_RECONSTRUCTION.md']:
    p=root/name
    print(name, 'exists', p.exists(), 'size', p.stat().st_size if p.exists() else None)
