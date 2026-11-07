from pathlib import Path
import csv
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

# Load existing lightweight artifacts when present.
functions=[]
for name in ['exe_functions.csv']:
    path=root/name
    if path.exists():
        with path.open('r',encoding='utf-8',newline='') as f:
            for row in csv.DictReader(f):
                try: rva=int(row['rva'],0)
                except: continue
                functions.append({'rva':rva,'va':base+rva,'section':row.get('section',''),'confidence':row.get('confidence',''),'caller_count':int(row.get('caller_count','0') or 0),'callee_count':int(row.get('callee_count','0') or 0)})
func_by_va={item['va']:item for item in functions}

callgraph=[]
path=root/'exe_callgraph.csv'
if path.exists():
    with path.open('r',encoding='utf-8',newline='') as f:
        for row in csv.DictReader(f):
            try: caller=int(row['caller_rva'],0); callee=int(row['callee_rva'],0)
            except: continue
            callgraph.append({'caller_rva':caller,'callee_rva':callee,'call_type':row.get('call_type',''),'direct_indirect':row.get('direct_indirect',''),'confidence':row.get('confidence',''),'evidence':row.get('evidence','')})

mainloop=[]
path=root/'exe_mainloop_candidates.csv'
if path.exists():
    with path.open('r',encoding='utf-8',newline='') as f:
        for row in csv.DictReader(f):
            try: rva=int(row['candidate_rva'],0)
            except: continue
            mainloop.append({'rva':rva,'va':base+rva,'loop_shape':row.get('loop_shape',''),'message_api':row.get('message_api',''),'render_api':row.get('render_api',''),'timer_api':row.get('timer_api',''),'confidence':row.get('confidence',''),'evidence':row.get('evidence','')})

strings=[]
path=root/'exe_strings_refs.csv'
if path.exists():
    with path.open('r',encoding='utf-8',newline='') as f:
        for row in csv.DictReader(f):
            strings.append({'string':row.get('string',''),'rva':row.get('rva',''),'count':row.get('count','0'),'subsystem_candidate':row.get('subsystem_candidate',''),'confidence':row.get('confidence','')})

# Build native runtime graph from static scan + existing callgraph + external boundary.
runtime=[]
seen=set()
for va,ve,nm,pr,rs,ch in secs:
    if nm=='.tvm0' or not rs:
        continue
    raw=data[pr:pr+rs]
    md=Cs(CS_ARCH_X86, CS_MODE_32)
    for ins in md.disasm(raw, base+va):
        mnem=ins.mnemonic; op_str=ins.op_str; rva=ins.address-base
        op=ins.operands[0] if ins.operands else None
        if mnem=='call' and op and op.type==2 and getattr(op.mem,'base',0)==0 and getattr(op.mem,'index',0)==0 and op.mem.disp!=0:
            disp=op.mem.disp & 0xffffffff
            if disp==0xE9DC665:
                edge={'function_rva':hex(rva),'caller_rva':hex(rva),'callee_rva':hex(0xE9DC665),'edge_type':'EXTERNAL_CALL','section':sec_name(ins.address),'global_reads':0,'global_writes':0,'external_dependency':'codoMP_client_shipRetailBase.dll ordinal_1','confidence':'CONFIRMED','evidence':'entry indirect thunk'}
            else:
                edge={'function_rva':hex(rva),'caller_rva':hex(rva),'callee_rva':hex(disp),'edge_type':'INDIRECT_CALL','section':sec_name(ins.address),'global_reads':0,'global_writes':0,'external_dependency':'UNKNOWN','confidence':'UNKNOWN','evidence':'unresolved non-IAT indirect call'}
        elif mnem in ('call','jmp') and op and op.type==1:
            target=op.imm & 0xffffffff
            edge_type='DIRECT_CALL' if mnem=='call' else 'JUMP'
            if base <= target < base+size:
                confidence='CANDIDATE_INTERNAL'
                evidence='absolute target inside EXE image range'
                external='INTERNAL_OR_UNKNOWN'
            else:
                confidence='UNKNOWN'
                evidence='absolute target outside proven EXE import path'
                external='UNKNOWN'
            edge={'function_rva':hex(rva),'caller_rva':hex(rva),'callee_rva':hex(target),'edge_type':edge_type,'section':sec_name(ins.address),'global_reads':0,'global_writes':0,'external_dependency':external,'confidence':confidence,'evidence':evidence}
        else:
            continue
        key=(edge['function_rva'],edge['caller_rva'],edge['callee_rva'],edge['edge_type'])
        if key in seen: continue
        seen.add(key)
        runtime.append(edge)
for edge in callgraph:
    key=(hex(edge['caller_rva']-base),hex(edge['caller_rva']-base),hex(edge['callee_rva']-base),'DIRECT_CALL')
    if key in seen: continue
    seen.add(key)
    runtime.append({'function_rva':hex(edge['caller_rva']-base),'caller_rva':hex(edge['caller_rva']-base),'callee_rva':hex(edge['callee_rva']-base),'edge_type':'DIRECT_CALL','section':func_by_va.get(edge['caller_rva'],{}).get('section',sec_name(edge['caller_rva'])),'global_reads':0,'global_writes':0,'external_dependency':'INTERNAL_OR_UNKNOWN','confidence':edge.get('confidence','UNKNOWN'),'evidence':edge.get('evidence','existing callgraph edge')})

with out_runtime.open('w',newline='',encoding='utf-8') as f:
    w=csv.DictWriter(f, fieldnames=['function_rva','caller_rva','callee_rva','edge_type','section','global_reads','global_writes','external_dependency','confidence','evidence'])
    w.writeheader(); w.writerows(runtime)

# Init clusters from existing high-connectivity candidates and string subsystems.
init_rows=[]
bootstrap_rvas=[0x0E9DC690,0x0E9DC665]
for item in functions:
    init_rows.append({'cluster_id':'CLSTR_BOOTSTRAP','entry_candidate':'0xE5DC690','member_functions':hex(item['rva']),'caller_count':item['caller_count'],'callee_count':item['callee_count'],'section':item['section'],'global_writes':0,'thread_creation':0,'external_calls':1 if item['va']==0x0E9DC665 else 0,'file_operations':0,'network_operations':0,'renderer_operations':0,'confidence':'CANDIDATE','evidence':'plain-text candidate; caller chain incomplete'})
for item in mainloop:
    init_rows.append({'cluster_id':'CLSTR_MAINLOOP_CANDIDATE','entry_candidate':hex(item['rva']),'member_functions':hex(item['rva']),'caller_count':0,'callee_count':0,'section':sec_name(item['va']),'global_writes':0,'thread_creation':0,'external_calls':0,'file_operations':0,'network_operations':0,'renderer_operations':0,'confidence':'CANDIDATE','evidence':'existing main-loop candidate; loop evidence not confirmed'})
for row in strings:
    subs=row.get('subsystem_candidate','')
    if any(k in subs for k in ['FileSystem','Config','Localization','Window/Input','Network','Renderer','Game','Thread','Command']):
        try: rva=int(row['rva'],0)
        except: continue
        init_rows.append({'cluster_id':'CLSTR_STRING_'+subs.replace('/','_').replace(' ','_'),'entry_candidate':hex(rva),'member_functions':hex(rva),'caller_count':0,'callee_count':0,'section':sec_name(base+rva),'global_writes':0,'thread_creation':0,'external_calls':0,'file_operations':1 if 'FileSystem' in subs else 0,'network_operations':1 if 'Network' in subs else 0,'renderer_operations':1 if 'Renderer' in subs else 0,'confidence':'UNKNOWN','evidence':'string inventory only; caller chain unconfirmed'})
with out_init.open('w',newline='',encoding='utf-8') as f:
    w=csv.DictWriter(f, fieldnames=['cluster_id','entry_candidate','member_functions','caller_count','callee_count','section','global_writes','thread_creation','external_calls','file_operations','network_operations','renderer_operations','confidence','evidence'])
    w.writeheader(); w.writerows(init_rows)

# Game init candidates: placeholders from existing candidates + string-based cluster candidates.
game_rows=[]
for item in mainloop:
    game_rows.append({'rva':hex(item['rva']),'va':hex(item['va']),'cluster':'main_loop_candidate','caller_count':0,'callee_count':0,'section':sec_name(item['va']),'confidence':'CANDIDATE','evidence':'existing main-loop candidate; game-init path unconfirmed'})
for row in strings:
    subs=row.get('subsystem_candidate','')
    if any(k in subs for k in ['Game','Renderer','Network','Main Loop']):
        try: rva=int(row['rva'],0)
        except: continue
        game_rows.append({'rva':hex(rva),'va':hex(base+rva),'cluster':subs,'caller_count':0,'callee_count':0,'section':sec_name(base+rva),'confidence':'UNKNOWN','evidence':'string candidate; caller/global dataflow unconfirmed'})
with out_game.open('w',newline='',encoding='utf-8') as f:
    w=csv.DictWriter(f, fieldnames=['rva','va','cluster','caller_count','callee_count','section','confidence','evidence'])
    w.writeheader(); w.writerows(game_rows)

# Main-loop structural candidates: placeholder from existing list plus lightweight back-edge scan.
main_rows=[]
for item in mainloop:
    main_rows.append({'candidate_entry':hex(item['rva']),'back_edge':'UNKNOWN','loop_body':'UNKNOWN','update_candidate':'UNKNOWN','render_candidate':'UNKNOWN','message_candidate':'UNKNOWN','network_tick_candidate':'UNKNOWN','sleep_candidate':'UNKNOWN','global_state_read':'UNKNOWN','global_state_write':'UNKNOWN','confidence':'CANDIDATE','evidence':'existing candidate; no back-edge confirmed in this pass'})
back_edges=[]
for va,ve,nm,pr,rs,ch in secs:
    if nm=='.tvm0' or not rs or not (ch & 0x20000000):
        continue
    raw=data[pr:pr+rs]
    md=Cs(CS_ARCH_X86, CS_MODE_32)
    targets=[]
    for ins in md.disasm(raw, base+va):
        if ins.mnemonic in ('call','jmp') and ins.operands:
            op=ins.operands[0]
            if op.type==1:
                tgt=op.imm & 0xffffffff
                if base <= tgt < base+size:
                    targets.append((ins.address, ins.mnemonic, tgt, ins.bytes.hex(' ')))
    cnt=Counter(t for _,_,t,_ in targets)
    for (addr,mn,tgt,bhex),c in [((a,mn,tgt,bhex),cnt[tgt]) for a,mn,tgt,bhex in targets]:
        if c >= 2 and tgt < addr:
            back_edges.append({'candidate_entry':hex(addr-base),'back_edge':hex(tgt-base),'loop_body':'UNKNOWN','update_candidate':'UNKNOWN','render_candidate':'UNKNOWN','message_candidate':'UNKNOWN','network_tick_candidate':'UNKNOWN','sleep_candidate':'UNKNOWN','global_state_read':'UNKNOWN','global_state_write':'UNKNOWN','confidence':'CANDIDATE','evidence':f'repeated absolute {mn} to earlier VA; not proven loop entry'})
for row in back_edges[:50]:
    main_rows.append(row)
with out_main.open('w',newline='',encoding='utf-8') as f:
    w=csv.DictWriter(f, fieldnames=['candidate_entry','back_edge','loop_body','update_candidate','render_candidate','message_candidate','network_tick_candidate','sleep_candidate','global_state_read','global_state_write','confidence','evidence'])
    w.writeheader(); w.writerows(main_rows)

# Renderer/filesystem/network/thread/stateflow: explicit placeholders because current static evidence is insufficient without proven call sites.
for path,rows,fields in [
    (out_renderer,[{'rva':'UNKNOWN','va':'UNKNOWN','api_or_string':'Present/BeginScene/EndScene/D3D device','caller':'UNKNOWN','callee':'UNKNOWN','section':'UNKNOWN','confidence':'UNKNOWN','evidence':'no confirmed renderer call site in EXE plain-text scan'}], ['rva','va','api_or_string','caller','callee','section','confidence','evidence']),
    (out_fs,[{'rva':'UNKNOWN','va':'UNKNOWN','api_or_string':'CreateFile/ReadFile/FindFirstFile/fastfile/pak/zone','caller':'UNKNOWN','callee':'UNKNOWN','section':'UNKNOWN','confidence':'UNKNOWN','evidence':'string inventory exists; no confirmed filesystem init chain'}], ['rva','va','api_or_string','caller','callee','section','confidence','evidence']),
    (out_net,[{'rva':'0x849413B','va':'0x0849413B','api_or_string':'network candidate','caller':'UNKNOWN','callee':'UNKNOWN','section':sec_name(0x0849413B),'confidence':'UNKNOWN','evidence':'address retained from existing notes; semantics unresolved'}], ['rva','va','api_or_string','caller','callee','section','confidence','evidence']),
    (out_thread,[{'rva':'UNKNOWN','va':'UNKNOWN','api_or_string':'CreateThread/_beginthread/_beginthreadex/NtCreateThreadEx','caller':'UNKNOWN','callee':'UNKNOWN','start_address':'START_ADDRESS_UNKNOWN','section':'UNKNOWN','confidence':'UNKNOWN','evidence':'no proven thread creation site recovered in static scan'}], ['rva','va','api_or_string','caller','callee','start_address','section','confidence','evidence']),
    (out_state,[{'global_address':'UNKNOWN','writer':'UNKNOWN','reader':'UNKNOWN','branch':'UNKNOWN','initial_value':'UNKNOWN','written_value':'UNKNOWN','first_write':'UNKNOWN','first_read':'UNKNOWN','downstream_function':'UNKNOWN','semantic_status':'SEMANTICS_UNRESOLVED','confidence':'UNKNOWN','evidence':'global data attribution not started'}], ['global_address','writer','reader','branch','initial_value','written_value','first_write','first_read','downstream_function','semantic_status','confidence','evidence']),
]:
    with path.open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f, fieldnames=fields); w.writeheader(); w.writerows(rows)

print('runtime',len(runtime))
print('init',len(init_rows))
print('game',len(game_rows))
print('main',len(main_rows))
