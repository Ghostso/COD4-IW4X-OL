# EX-065: emit the required artifacts.
import csv


def main():
    entry = [
        ["tcls_core.exe", "0xB2A18", "PE entry stub",
         "call sub_B310D ; jmp 0x4B2847", "STATIC_CONFIRMED"],
        ["tcls_core.exe", "0xB310D", "security-cookie init",
         "mov ecx,[0x5A60A4] ...", "STATIC_CONFIRMED"],
        ["tcls_core.exe", "0xB2847", "__scrt_common_main_seh",
         "push 0x14 / push 0x5A0A78 / call sub_B2CD0", "STATIC_CONFIRMED"],
        ["tcls_core.exe", "0xB218E", "invoke_main wrapper",
         "call sub_B2D2B ; call sub_D74F7", "STATIC_CONFIRMED"],
        ["tcls_core.exe", "0xD74F7", "main dispatch",
         "call sub_D909C ; call sub_D96DF ; call sub_D9217",
         "STATIC_CONFIRMED"],
        ["tcls_core.exe", "0x5EA87", "TCLSHostApp method",
         "callers 0x567E6 0x59167 ...", "STATIC_CONFIRMED"],
        ["tcls_core.exe", "0x5EA87", "ctor call of the handler table",
         "0x5EB8B call sub_89EEE", "STATIC_CONFIRMED"],
        ["tcls_core.exe", "0x5F4A3", "second protocol method",
         "0x5F5E5 call sub_8A082", "STATIC_CONFIRMED"],
        ["tcls_core.exe", "0x8D2A2", "the CreateIIPSRepair caller",
         "push 0x56A4B0 / LoadLibraryW / GetProcAddress",
         "STATIC_CONFIRMED"],
    ]
    with open("ex065_tcls_entry.csv", "w", newline="",
              encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["module", "rva", "role", "instruction_or_note",
                    "evidence"])
        w.writerows(entry)
    print("wrote ex065_tcls_entry.csv (%d rows)" % len(entry))

    repair = [
        ["IIPSLaunchRestore.dll", "export", "CreateIIPSRepair", "0x11590",
         "STATIC_CONFIRMED", "caller tcls_core.exe 0x8D38A"],
        ["IIPSLaunchRestore.dll", "export", "RealeaseIIPSRepair", "0x11600",
         "STATIC_CONFIRMED", "caller tcls_core.exe 0x8D527"],
        ["tcls_core.exe", "0x8D353", "LoadLibraryW",
         "IAT 0x556058", "STATIC_CONFIRMED",
         "argument built at 0x8D2E1 (runtime path)"],
        ["tcls_core.exe", "0x8D382", "push \"CreateIIPSRepair\"",
         "VA 0x56A4B0", "STATIC_CONFIRMED", ""],
        ["tcls_core.exe", "0x8D38A", "GetProcAddress",
         "IAT 0x556044", "STATIC_CONFIRMED", ""],
        ["tcls_core.exe", "0x8D39F", "call [ebp-0x30]",
         "resolved CreateIIPSRepair", "STATIC_CONFIRMED",
         "result stored to [obj+0x526C]"],
        ["tcls_core.exe", "0x8D2A2", "function entry",
         "2 direct callers", "STATIC_CONFIRMED",
         "0x8DA49 (sub_8D9ED state 0x18/0x11), 0x8DE3C (sub_8DBEB cmd 0x63)"],
        ["tcls_core.exe", "0x16A4E4", ".rdata handler table entry",
         "-> sub_8DBEB", "STATIC_CONFIRMED",
         "table 0x16A4DC registered by sub_89EEE"],
        ["tcls_core.exe", "0x89F4C", "table registration",
         "mov [eax],0x56A4DC ; [eax+4]=0x56A524 ; [eax+8]=0x56A538",
         "STATIC_CONFIRMED", "ctor sub_89EEE"],
    ]
    with open("ex065_createiipsrepair.csv", "w", newline="",
              encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["module", "rva_or_export", "role", "target",
                    "evidence", "note"])
        w.writerows(repair)
    print("wrote ex065_createiipsrepair.csv (%d rows)" % len(repair))

    ipc = [
        ["tcls_core.exe", "0x798E", "sprintf",
         '"%s%lu" + "TCLS_SHAREDMEMEMORY" + pid -> "TCLS_SHAREDMEMEMORY<pid>"',
         "STATIC_CONFIRMED"],
        ["tcls_core.exe", "0x40B9", "sprintf",
         '"%s%lu" + "TCLS_SHAREDMEMEMORY" + pid', "STATIC_CONFIRMED"],
        ["tcls_core.exe", "0x407D", "sprintf",
         '"%s%llu" + "RAIL_TCLS_SHARED" + id', "STATIC_CONFIRMED"],
        ["tcls_core.exe", "0xC629", "sprintf",
         '"%s%s" + "TCLS_CORE_SHARE_MEMORY_" + suffix', "STATIC_CONFIRMED"],
        ["tcls_core.exe", "0xC77F", "sprintf",
         '"%s%s" + "TCLS_CORE_MUTEX_" + suffix', "STATIC_CONFIRMED"],
        ["tcls_core.exe", "0x18F57", "sprintf",
         '"TCLS_CORE_WND_%u"', "STATIC_CONFIRMED"],
        ["tcls_core.exe", "0x157B24", "TCLS_EXIT_EVENT",
         "exit event name", "STATIC_CONFIRMED"],
        ["tcls_core.exe", "0x1636B0", "TCLS_SHAREDMEMEMORY"
         " + NETBAR_LAUNCHGAMESHAREDMEM", "netbar launch shared mem",
         "STATIC_CONFIRMED"],
        ["TenProxy.dll", "0x20F70", "TCLS_SHAREDMEMEMORY",
         "base name only", "STATIC_CONFIRMED"],
        ["TenProxy.dll", "0x20E42",
         '"OpenFileMapping TCLS_SHAREDMEMEMORY+%d"', "%d=GetCurrentProcessId",
         "STATIC_CONFIRMED"],
        ["TenProxy.dll", "0x218...", "TCLS_GMAE_EXIT", "window message",
         "STATIC_CONFIRMED"],
        ["TenProxy.dll", "0x21E...", "TCLS_TENPROXY_RESULT",
         "window message", "STATIC_CONFIRMED"],
        ["TCLS.dll", "0x3C3268", "TCLS_SHAREDMEMEMORY", "shell memory",
         "STATIC_CONFIRMED"],
        ["TCLS.dll", "0x3C37C6", "[Clauncher::GetRealGamePID]",
         "reads RealGamePID=%d from the mapping", "STATIC_CONFIRMED"],
        ["TCLS.dll", "0x3C24F4", "TCLS_SHELLMEMORY_", "shell shared mem",
         "STATIC_CONFIRMED"],
        ["TCLS.dll", "0x3C2DF0", "TCLS_TASMEMORY_", "TAS shared mem",
         "STATIC_CONFIRMED"],
        ["TCLS.dll", "0x3C29CC", "TCLS_NETBARMACHINE_", "netbar machine",
         "STATIC_CONFIRMED"],
        ["ClientBase.dll", "0x1D3C8C", "TCLS_SHAREDMEMEMORY.%.s%.d",
         "TAS side", "STATIC_CONFIRMED"],
        ["tpsvcBase.dll", "0x1D368C", "TCLS_SHAREDMEMEMORY.%.s%.d",
         "TAS side", "STATIC_CONFIRMED"],
        ["codoMP_client_shipRetailBase.dll", "0x88F108",
         "TCLS_SHAREDMEMEMORY", "CODOL game side", "STATIC_CONFIRMED"],
    ]
    with open("ex065_tcls_ipc.csv", "w", newline="",
              encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["module", "rva", "role", "detail", "evidence"])
        w.writerows(ipc)
    print("wrote ex065_tcls_ipc.csv (%d rows)" % len(ipc))

    callers = [
        ["tcls_core.exe", "0x8D9ED", "0x8DA49", "sub_8D2A2",
         "state ([this+0x30]==0x18 or 0x11) -> call",
         "STATIC_CONFIRMED"],
        ["tcls_core.exe", "0x8DBEB", "0x8DE3C", "sub_8D2A2",
         "command ([this+0x30]==0x63 && [this+0x34]==0) -> call",
         "STATIC_CONFIRMED"],
        ["tcls_core.exe", "sub_8DBEB", "0x16A4E4", "handler table entry",
         ".rdata table 0x16A4DC, slot 1", "STATIC_CONFIRMED"],
        ["tcls_core.exe", "sub_89EEE", "0x89F4C", "table registration",
         "ctor writes 0x56A4DC/0x56A524/0x56A538", "STATIC_CONFIRMED"],
        ["tcls_core.exe", "sub_5EA87", "0x5EB8B", "call sub_89EEE",
         "TCLSHostApp protocol method", "STATIC_CONFIRMED"],
        ["tcls_core.exe", "sub_5EA87", "0x5EE3D", "call sub_89EEE",
         "second call site", "STATIC_CONFIRMED"],
        ["tcls_core.exe", "sub_5EA87", "0x5F30A", "call sub_89EEE",
         "third call site", "STATIC_CONFIRMED"],
        ["tcls_core.exe", "sub_5F4A3", "0x5F5E5", "call sub_8A082",
         "second protocol method", "STATIC_CONFIRMED"],
        ["tcls_core.exe", "sub_5EA87", "external", "-",
         "9+ direct callers in the TCLSHostApp message layer",
         "STATIC_REACHABLE"],
    ]
    with open("ex065_tcls_callers.csv", "w", newline="",
              encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["module", "function", "rva", "target", "note",
                    "evidence"])
        w.writerows(callers)
    print("wrote ex065_tcls_callers.csv (%d rows)" % len(callers))

    host = [
        ["WeGame TCLS launcher (TGP / Netbar)", "host process",
         "UIShellRes\\DMLQ1\\TCLS / QSPEED / QQXJ", "STATIC_BOUNDARY",
         "launcher writes the per-game TCLSPath/TCLSClientFileName"],
        ["tcls_core.exe", "0xB2A18", "PE entry", "STATIC_CONFIRMED",
         "subsystems 2 (GUI)"],
        ["tcls_core.exe", "TLS", "callbacks table VA 0x55659C",
         "STATIC_CONFIRMED", "table is EMPTY (0 callbacks)"],
        ["tcls_core.exe", "0x5EA87", "TCLSHostApp:: protocol methods",
         "STATIC_CONFIRMED", "LaunchGame / FixGame / CancelFix / ShowZoneUI"],
        ["tcls_core.exe", "LaunchGameByTGP",
         '"<exe>" -q %u', "STATIC_CONFIRMED",
         "the -q launch form (matches EX-035)"],
        ["tcls_core.exe", "LaunchGameByNetbar", '"<exe>" %s',
         "STATIC_CONFIRMED", "netbar variant"],
        ["codoMP_client_shipRetail.exe", "-q", "launched BY tcls_core",
         "STATIC_REACHABLE", "reverse direction NOT in the game binary"],
    ]
    with open("ex065_host_process_edges.csv", "w", newline="",
              encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["node", "rva_or_kind", "edge", "evidence", "note"])
        w.writerows(host)
    print("wrote ex065_host_process_edges.csv (%d rows)" % len(host))

    boot = [
        ["codoMP_client_shipRetail.exe", "native bootstrap 0x77F580 ...",
         "no import / call / pointer to tcls_core",
         "STATIC_BOUNDARY", "EX-064 result, reconfirmed"],
        ["codoMP_client_shipRetailBase.dll", "TCLS_SHAREDMEMEMORY +"
         " tcls_core.exe strings", "shares the protocol NAME only",
         "STATIC_BOUNDARY", "no CALL / pointer to tcls_core"],
        ["tcls_core.exe", "LoadLibraryW IIPSLaunchRestore.dll 0x8D353",
         "-> CreateIIPSRepair 0x8D39F", "STATIC_CONFIRMED", ""],
        ["IIPSLaunchRestore.dll", "LoadLibraryW iips.dll 0x3C48",
         "-> GetResourceManagerII 0x3C99", "STATIC_CONFIRMED", ""],
        ["iips.dll", "manager -> slot 1 -> sub_197F0 -> sub_12760",
         "-> CNIFS::InitInGameApp 0x9860", "STATIC_CONFIRMED", ""],
        ["tcls_core.exe", "TCLS_SHAREDMEMEMORY<pid>",
         "shares context with the game via named shared memory",
         "STATIC_CONFIRMED",
         "the actual native<->TCLS link is a NAMED OBJECT PROTOCOL,"
         " not a CALL"],
        ["TenProxy log 2020", "OpenFileMapping TCLS_SHAREDMEMEMORY+4540"
         " Success!", "historical runtime confirmation",
         "HISTORICAL_DYNAMIC", "module-level + API-name level only"],
    ]
    with open("ex065_bootstrap_boundary.csv", "w", newline="",
              encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["node", "edge_or_artifact", "relation", "evidence",
                    "note"])
        w.writerows(boot)
    print("wrote ex065_bootstrap_boundary.csv (%d rows)" % len(boot))

    loader = [
        ["tcls_core.exe", "0x8D353", "LoadLibraryW", "0x556058",
         "IIPSLaunchRestore.dll", "STATIC_CONFIRMED"],
        ["tcls_core.exe", "0x8D38A", "GetProcAddress", "0x556044",
         "CreateIIPSRepair", "STATIC_CONFIRMED"],
        ["tcls_core.exe", "0x8D527", "GetProcAddress", "0x556044",
         "RealeaseIIPSRepair", "STATIC_CONFIRMED"],
        ["IIPSLaunchRestore.dll", "0x3C48", "LoadLibraryW", "0x1006C038",
         "iips.dll", "STATIC_CONFIRMED"],
        ["IIPSLaunchRestore.dll", "0x3C8F", "GetProcAddress", "0x1006C044",
         "GetResourceManagerII", "STATIC_CONFIRMED"],
        ["IIPSLaunchRestore.dll", "0x3608", "GetProcAddress", "0x1006C044",
         "ReleaseResourceManagerII", "STATIC_CONFIRMED"],
        ["IIPSLaunchRestore.dll", "0x5CD4", "GetProcAddress", "0x1006C044",
         "ReleaseResourceManagerII", "STATIC_CONFIRMED"],
    ]
    with open("ex065_loader_edges.csv", "w", newline="",
              encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["module", "rva", "api", "iat", "symbol", "evidence"])
        w.writerows(loader)
    print("wrote ex065_loader_edges.csv (%d rows)" % len(loader))


if __name__ == "__main__":
    main()
