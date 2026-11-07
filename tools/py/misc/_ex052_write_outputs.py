import csv
from pathlib import Path
import sys
sys.stdout.reconfigure(encoding='utf-8')
root = Path(r'D:\BaiduNetdiskDownload\使命召唤OL')

report_path = root / 'CODOL_EX052_IIPS_MINIMAL_ENVIRONMENT_MATRIX.md'
report_path.write_text(report_path.read_text(encoding='utf-8') + '\n', encoding='utf-8')

env_rows = [
    ['experiment_id','change','baseline','expected_question','module_timeline','iips_loaded','ifs2_loaded','iipshostapp_loaded','iipsinit_seen','fatal_window','fatal_text','exit_code','runtime_seconds','new_execution_node','evidence_level'],
    ['EXP052_BASELINE_Q','none','baseline normal -q from 工具\\EX035_DIR','Does normal -q change beyond NODE-B','TenRpcs->GameRpcs->tcj->policyprobe->TenProxy->GbSpy->iips.dll; no IFS2/HostApp observed','YES','NO','NO','YES','YES','WIN_IIPS_INIT_ERROR / 8189FEC','non-zero','~same','NONE','observer-confirmed baseline'],
    ['EXP052_IFS2_VISIBLE','copy IFS2.dll and IIPSHostApp.exe+ini beside codoMP_client_shipRetail.exe','baseline working dir + original layout without sibling IFS2/HostApp','Does making IFS2 visible beside EXE change IIPS state beyond text variation?','same pre-IIPS chain; monitor for new DLL/process/window/thread','expected','expected','expected','expected','expected','expected','expected','expected','IFS2_OR_HOSTAPP_APPEARANCE','experiment-ready'],
    ['EXP052_WORKDIR_GAME','working directory = COD OL','baseline working dir = 工具\\EX035_DIR','Does game-root CWD change IIPS initialization path?','same module chain observation set','expected','expected','expected','expected','expected','expected','expected','expected','CWD_DELTA_NEW_NODE','experiment-ready'],
    ['EXP052_IIPS_COPY_LAYOUT','place full IIPS directory copy beside EXE while keeping baseline CWD','baseline IIPS path under COD OL\\IIPS only','Does a sibling IIPS directory layout reach a different IIPS load path?','same observers','expected','expected','expected','expected','expected','expected','expected','expected','LAYOUT_NEW_NODE','experiment-ready'],
    ['EXP052_HOSTAPP_LAYOUT','copy only IIPSHostApp.exe+IIPSHostApp.ini to candidate HostApp path','baseline without explicit HostApp path beside EXE','Does explicit HostApp layout change init branch?','same observers','expected','expected','expected','expected','expected','expected','expected','expected','HOSTAPP_NEW_NODE','experiment-ready'],
    ['EXP052_INI_RESPOOL_VARIANT','IIPSHostApp.ini ReservedSize=1073741824','baseline IIPSHostApp.ini ReservedSize=0','Does ReservedSize change change runtime path or timing?','same observers','expected','expected','expected','expected','expected','expected','expected','expected','RESPOOL_NEW_NODE','experiment-ready'],
]
(root / 'ex052_environment_matrix.csv').write_text(''.join([','.join(map(str, row)) + '\n' for row in env_rows]), encoding='utf-8')

path_rows = [
    ['component','path_contract','evidence','load_attempt_required','observable_runtime_signal','notes'],
    ['IFS2.dll','UTF-16 ifs2.dll passed to LoadLibraryW from initIfsLib path builder','iips.dll static disassembly at 0x10009570..0x100097BE; LoadLibraryW call 0x100096E9; GetProcAddress CreateIFSLibDll 0x1000977C; CreateIFSLibDll call 0x100097A5','YES','IFS2.dll in module snapshot; runtime prolongation with new thread/window','path builder full concatenation not fully reconstructed'],
    ['IFS2/ directory','subdirectory referenced by IIPS path builder strings','rdata contains IFS2/; exact prefix/current-dir/module-dir composition unresolved','YES','same as IFS2.dll','not enough evidence for fixed-path-only contract'],
    ['IIPSHostApp.exe','UTF-16 IIPSHostApp.exe from HostApp launch branch','6 occurrences at 0x10033F78/0x10033F9B/0x10033FD6/0x10034012/0x10034048/0x1003406A; ShellExecuteExW candidate 0x10015CD1','YES','IIPSHostApp.exe process; new window; runtime prolongation','ini path less visible in text scan; utf-16/runtime composition possible'],
    ['IIPSHostApp.ini','ini read by GetPrivateProfileIntW("[ResPool]","ReservedSize") at 0x10009A8B','IIPSHostApp.ini disk presence confirmed; EX-051 md documents static candidate; exact runtime path unresolved','IF HostApp branch reached','file-read activity; new window/tray activity','no plaintext .ini hit in .text; likely runtime/utf-16 composition'],
    ['ResPool ReservedSize','default 0x40000000; overridden by IIPSHostApp.ini','0x10009A8B GetPrivateProfileIntW; IIPSHostApp.ini contains ReservedSize=0','depends on HostApp branch','runtime timing or HostApp behavior change','effect on fatal path unconfirmed'],
]
(root / 'ex052_ifs2_path_analysis.csv').write_text(''.join([','.join(map(str, row)) + '\n' for row in path_rows]), encoding='utf-8')

flow_rows = [
    ['function_va','caller','callee_or_event','branch','return_handling','evidence_level','notes'],
    ['0x10009860','CNIFS caller via vtable/this -> 0x10009A35','CNIFS::initIfsLib at 0x10009570','0x100099D2 call; 0x100099D7 test al,al; 0x100099D9 jne success','failure path returns false from InitInGameApp and skips post-init steps','L2 confirmed','InitInGameApp checks initIfsLib return'],
    ['0x10009A2B','post-initIfsLib success path','[ecx+0x2C] vfunc with arg 1','0x10009A33 call edx','success-only branch observed','L2 confirmed','post-IFS success path exists only if initIfsLib returned nonzero'],
    ['0x10009570','CNIFS::initIfsLib','privilege helper at 0x100051F0','non-fatal branch to IFS/HostApp init','local error state stored in [ebp+0xCC]','L2 confirmed','QoS failure logged but not fatal here'],
    ['0x10009570','CNIFS::initIfsLib','LoadLibraryW path builder','0x100096E9 call','NULL handle -> failure branch at 0x100096F4','L2 confirmed','path string source/concatenation not fully reconstructed'],
    ['0x100096F4','LoadLibraryW failure branch','error-store helper 0x10004310','0x1000970C push error id; 0x10009711 call helper','sets init state=1 and returns false','L2 confirmed','distinct from CreateIFSLibDll branches'],
    ['0x10009770','initIfsLib success continuation','GetProcAddress for CreateIFSLibDll','0x1000977C call esi','NULL -> error string 0x10034974; state=2','L2 confirmed'],
    ['0x100097A5','after CreateIFSLibDll resolution','CreateIFSLibDll call','0x100097A5 call eax','zero EAX -> error string 0x100349B4; state=1','L2 confirmed'],
    ['0x100097CC','after CreateIFSLibDll call','GetProcAddress DestoryIFSLibDll','0x100097CC call esi','NULL -> error string 0x100349F8; state=3','L2 confirmed'],
    ['0x10009818','both failure and success cleanup','cleanup + return','0x10009831 mov al,1 on success; 0x10009769 xor al,al on failure','return value in AL','L2 confirmed'],
]
(root / 'ex052_init_state_flow.csv').write_text(''.join([','.join(map(str, row)) + '\n' for row in flow_rows]), encoding='utf-8')
print('wrote', report_path, 'lines', len(report_path.read_text(encoding='utf-8').splitlines()))
for name in ['ex052_environment_matrix.csv','ex052_ifs2_path_analysis.csv','ex052_init_state_flow.csv']:
    p = root / name
    print('wrote', p, 'lines', len(p.read_text(encoding='utf-8').splitlines()))
