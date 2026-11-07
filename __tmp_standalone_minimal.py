from pathlib import Path
import csv
root=Path('.')
for name,rows,fields in [
    ('exe_native_runtime_graph.csv', [
        {'function_rva':'0xE5DC690','caller_rva':'0xE5DC690','callee_rva':'0xE9DC665','edge_type':'EXTERNAL_CALL','section':'.tp3','global_reads':0,'global_writes':0,'external_dependency':'codoMP_client_shipRetailBase.dll ordinal_1','confidence':'CONFIRMED','evidence':'entry indirect thunk'},
        {'function_rva':'0x101B','caller_rva':'0x101B','callee_rva':'0xfff02da6','edge_type':'DIRECT_CALL','section':'.tp3','global_reads':0,'global_writes':0,'external_dependency':'UNKNOWN','confidence':'UNKNOWN','evidence':'absolute target outside proven EXE import path'},
        {'function_rva':'0xE5C8033','caller_rva':'0xE5C8033','callee_rva':'0xCA8004','edge_type':'INDIRECT_CALL','section':'.tp3','global_reads':0,'global_writes':0,'external_dependency':'UNKNOWN','confidence':'UNKNOWN','evidence':'unresolved non-IAT indirect call'},
    ], ['function_rva','caller_rva','callee_rva','edge_type','section','global_reads','global_writes','external_dependency','confidence','evidence']),
    ('exe_init_clusters.csv', [
        {'cluster_id':'CLSTR_ENTRY','entry_candidate':'0xE5DC690','member_functions':'0xE5DC690;0xE9DC665','caller_count':0,'callee_count':1,'section':'.tp3','global_writes':0,'thread_creation':0,'external_calls':1,'file_operations':0,'network_operations':0,'renderer_operations':0,'confidence':'CONFIRMED','evidence':'confirmed entry thunk and external boundary'},
        {'cluster_id':'CLSTR_BOOTSTRAP_CANDIDATE','entry_candidate':'0x77F580','member_functions':'0x77F580','caller_count':0,'callee_count':0,'section':'UNKNOWN','global_writes':0,'thread_creation':0,'external_calls':0,'file_operations':0,'network_operations':0,'renderer_operations':0,'confidence':'CANDIDATE','evidence':'existing bootstrap candidate; entry-to-game path unconfirmed'},
    ], ['cluster_id','entry_candidate','member_functions','caller_count','callee_count','section','global_writes','thread_creation','external_calls','file_operations','network_operations','renderer_operations','confidence','evidence']),
    ('exe_game_init_candidates.csv', [
        {'rva':'0x77F580','va':'0x0977F580','cluster':'bootstrap candidate','caller_count':0,'callee_count':0,'section':'UNKNOWN','confidence':'CANDIDATE','evidence':'existing candidate; game-init evidence not confirmed'},
    ], ['rva','va','cluster','caller_count','callee_count','section','confidence','evidence']),
    ('exe_mainloop_structural.csv', [
        {'candidate_entry':'0x6212C0','back_edge':'UNKNOWN','loop_body':'UNKNOWN','update_candidate':'UNKNOWN','render_candidate':'UNKNOWN','message_candidate':'UNKNOWN','network_tick_candidate':'UNKNOWN','sleep_candidate':'UNKNOWN','global_state_read':'UNKNOWN','global_state_write':'UNKNOWN','confidence':'CANDIDATE','evidence':'existing candidate; no back-edge recovered in this pass'},
    ], ['candidate_entry','back_edge','loop_body','update_candidate','render_candidate','message_candidate','network_tick_candidate','sleep_candidate','global_state_read','global_state_write','confidence','evidence']),
    ('exe_renderer_candidates.csv', [
        {'rva':'UNKNOWN','va':'UNKNOWN','api_or_string':'Present/BeginScene/EndScene/D3D device','caller':'UNKNOWN','callee':'UNKNOWN','section':'UNKNOWN','confidence':'UNKNOWN','evidence':'no confirmed renderer call site in EXE plain-text scan'},
    ], ['rva','va','api_or_string','caller','callee','section','confidence','evidence']),
    ('exe_filesystem_candidates.csv', [
        {'rva':'UNKNOWN','va':'UNKNOWN','api_or_string':'CreateFile/ReadFile/FindFirstFile/fastfile/pak/zone','caller':'UNKNOWN','callee':'UNKNOWN','section':'UNKNOWN','confidence':'UNKNOWN','evidence':'string inventory exists; no confirmed filesystem init chain'},
    ], ['rva','va','api_or_string','caller','callee','section','confidence','evidence']),
    ('exe_network_candidates.csv', [
        {'rva':'0x849413B','va':'0x0849413B','api_or_string':'network candidate','caller':'UNKNOWN','callee':'UNKNOWN','section':sec_name(0x0849413B) if False else 'UNKNOWN','confidence':'UNKNOWN','evidence':'address retained from existing notes; semantics unresolved'},
    ], ['rva','va','api_or_string','caller','callee','section','confidence','evidence']),
    ('exe_startup_stateflow.csv', [
        {'global_address':'UNKNOWN','writer':'UNKNOWN','reader':'UNKNOWN','branch':'UNKNOWN','initial_value':'UNKNOWN','written_value':'UNKNOWN','first_write':'UNKNOWN','first_read':'UNKNOWN','downstream_function':'UNKNOWN','semantic_status':'SEMANTICS_UNRESOLVED','confidence':'UNKNOWN','evidence':'global data attribution not started'},
    ], ['global_address','writer','reader','branch','initial_value','written_value','first_write','first_read','downstream_function','semantic_status','confidence','evidence']),
    ('exe_thread_map.csv', [
        {'rva':'UNKNOWN','va':'UNKNOWN','api_or_string':'CreateThread/_beginthread/_beginthreadex/NtCreateThreadEx','caller':'UNKNOWN','callee':'UNKNOWN','start_address':'START_ADDRESS_UNKNOWN','section':'UNKNOWN','confidence':'UNKNOWN','evidence':'no proven thread creation site recovered in static scan'},
    ], ['rva','va','api_or_string','caller','callee','start_address','section','confidence','evidence']),
]:
    with (root/name).open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f, fieldnames=fields); w.writeheader(); w.writerows(rows)
        print(name, len(rows))
