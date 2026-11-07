# EX-064: emit the four required artifacts.
import csv
import json


def main():
    # ---- ex064_import_map.csv : already produced by ex064_import_map.py,
    #      but re-emit a summary-focused version with the key rows.
    rows = [
        ["DEFINITION", "iips.dll", "self", "GetResourceManagerII",
         "0x1C80", "", "", "", "STATIC_DIRECT"],
        ["DEFINITION", "iips.dll", "self", "GetResourceManager",
         "0x1BC0", "", "", "", "STATIC_DIRECT"],
        ["DEFINITION", "iips.dll", "self", "ReleaseResourceManagerII",
         "0x1C60", "", "", "", "STATIC_DIRECT"],
        ["DEFINITION", "iips.dll", "self", "ReleaseResourceManager",
         "0x1C60", "", "", "", "STATIC_DIRECT"],
        ["IMPORT", "ALL", "-", "GetResourceManagerII", "", "", "", "",
         "NOT_IMPORTED_BY_ANY_MODULE"],
        ["DYNAMIC_RESOLVE", "IIPSLaunchRestore.dll", "iips.dll (runtime)",
         "GetResourceManagerII", "", "", "", "", "STATIC_DIRECT"],
        ["DYNAMIC_RESOLVE", "IIPSLaunchRestore.dll", "iips.dll (runtime)",
         "ReleaseResourceManagerII", "", "", "", "", "STATIC_DIRECT"],
        ["DYNAMIC_RESOLVE", "tcls_core.exe", "IIPSLaunchRestore.dll (runtime)",
         "CreateIIPSRepair", "", "", "", "", "STATIC_DIRECT"],
        ["DYNAMIC_RESOLVE", "tcls_core.exe", "IIPSLaunchRestore.dll (runtime)",
         "RealeaseIIPSRepair", "", "", "", "", "STATIC_DIRECT"],
        ["STRING", "codoMP_client_shipRetail.exe", "-",
         "GetResourceManagerII", "", "VA 0xDC9294", "", "",
         "packed .tp3 data"],
        ["STRING", "codoMP_client_shipRetail.exe", "-",
         "ReleaseResourceManagerII", "", "VA 0xDC92AC", "", "",
         "packed .tp3 data"],
        ["IMPORTS_IIPS", "tools/EX035_DIR/IIPS/IIPSHost.dll",
         "iips_policymsg.dll", "", "", "", "", "",
         "companion DLL, not the manager"],
    ]
    with open("ex064_import_map.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["kind", "module", "import_dll", "symbol", "iat_rva",
                    "iat_va", "delay_iat", "thunk_rva", "evidence"])
        w.writerows(rows)
    print("wrote ex064_import_map.csv (%d rows)" % len(rows))

    # ---- ex064_getres_callers.csv
    callers = [
        ["IIPSLaunchRestore.dll", "sub_3AF0 (CallBackThread::StartLauchRestore)",
         "0x3C48", "IAT 0x1006C038", "KERNEL32!LoadLibraryW",
         "loads iips.dll (runtime-built path)", "STATIC_DIRECT"],
        ["IIPSLaunchRestore.dll", "sub_3AF0 (CallBackThread::StartLauchRestore)",
         "0x3C89", "IAT 0x1006C044", "KERNEL32!GetProcAddress",
         'push "GetResourceManagerII"', "STATIC_DIRECT"],
        ["IIPSLaunchRestore.dll", "sub_3AF0 (CallBackThread::StartLauchRestore)",
         "0x3C8F", "0x1006C044", "GetProcAddress",
         "call solves the export pointer", "STATIC_DIRECT"],
        ["IIPSLaunchRestore.dll", "sub_3AF0 (CallBackThread::StartLauchRestore)",
         "0x3C99", "EAX (resolved)", "GetResourceManagerII",
         "*** THE EXTERNAL CALL ***", "STATIC_INDIRECT"],
        ["IIPSLaunchRestore.dll", "sub_3AF0 (CallBackThread::StartLauchRestore)",
         "0x3CA1", "[esi+0xA8]", "store manager*",
         "manager pointer cached in the object", "STATIC_DIRECT"],
        ["IIPSLaunchRestore.dll", "sub_7430 (second site)",
         "0x744F", "IAT 0x1006C044", 'push "GetResourceManagerII"',
         "duplicate resolution site", "STATIC_DIRECT"],
        ["IIPSLaunchRestore.dll", "sub_7430 (second site)",
         "0x7455", "0x1006C044", "GetProcAddress",
         "call solves the export pointer", "STATIC_DIRECT"],
        ["IIPSLaunchRestore.dll", "sub_7430 (second site)",
         "0x745F", "EAX (resolved)", "GetResourceManagerII",
         "*** THE EXTERNAL CALL ***", "STATIC_INDIRECT"],
        ["IIPSLaunchRestore.dll", "sub_3600",
         "0x3608", "IAT 0x1006C044", 'push "ReleaseResourceManagerII"',
         "release path", "STATIC_DIRECT"],
        ["IIPSLaunchRestore.dll", "sub_8190-ish (DoRestoreSuccess)",
         "0x5CD4", "IAT 0x1006C044", 'push "ReleaseResourceManagerII"',
         "release path (worker thread)", "STATIC_DIRECT"],
        ["tcls_core.exe", "sub_8D2A2",
         "0x8D353", "IAT 0x556058", "KERNEL32!LoadLibraryW",
         "loads IIPSLaunchRestore.dll (runtime-built path)", "STATIC_DIRECT"],
        ["tcls_core.exe", "sub_8D2A2",
         "0x8D382", "IAT 0x556044", 'push "CreateIIPSRepair"',
         "GetProcAddress argument", "STATIC_DIRECT"],
        ["tcls_core.exe", "sub_8D2A2",
         "0x8D38A", "0x556044", "GetProcAddress",
         "call solves the export pointer", "STATIC_DIRECT"],
        ["tcls_core.exe", "sub_8D2A2",
         "0x8D39F", "EAX (resolved)", "CreateIIPSRepair",
         "*** THE TCLS EXTERNAL CALL ***", "STATIC_INDIRECT"],
    ]
    with open("ex064_getres_callers.csv", "w", newline="",
              encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["module", "function", "rva", "iat_or_source", "callee",
                    "note", "evidence"])
        w.writerows(callers)
    print("wrote ex064_getres_callers.csv (%d rows)" % len(callers))

    # ---- ex064_manager_consumers.csv
    cons = [
        ["IIPSLaunchRestore.dll", "0x3C99", "EAX = manager*",
         "return of GetResourceManagerII", "STATIC_INDIRECT"],
        ["IIPSLaunchRestore.dll", "0x3CA1", "[esi+0xA8] = manager*",
         "stored into CallBackThread object", "STATIC_DIRECT"],
        ["IIPSLaunchRestore.dll", "0x3CB0", "edx = [eax]",
         "manager vtable", "STATIC_DIRECT"],
        ["IIPSLaunchRestore.dll", "0x3CB2", "edx = [edx+0x68]",
         "MANAGER SLOT 26 (offset 0x68)", "STATIC_DIRECT"],
        ["IIPSLaunchRestore.dll", "0x3CB8", "call edx",
         "invoke manager slot 26", "STATIC_INDIRECT"],
        ["IIPSLaunchRestore.dll", "0x3CD4", "ecx = [esi+0xA8]",
         "reload manager*", "STATIC_DIRECT"],
        ["IIPSLaunchRestore.dll", "0x3CDC", "edx = [eax+4]",
         "MANAGER SLOT 1 (offset 0x04)", "STATIC_DIRECT"],
        ["IIPSLaunchRestore.dll", "0x3CE4", "call edx",
         "invoke manager slot 1", "STATIC_INDIRECT"],
        ["IIPSLaunchRestore.dll", "0x7478", "edx = [edx+0x68]",
         "slot 26 again (second site)", "STATIC_DIRECT"],
        ["IIPSLaunchRestore.dll", "0x747E", "call edx",
         "invoke manager slot 26", "STATIC_INDIRECT"],
        ["IIPSLaunchRestore.dll", "0x7488", "edx = [eax+4]",
         "MANAGER SLOT 1 again (second site)", "STATIC_DIRECT"],
        ["IIPSLaunchRestore.dll", "0x7490", "call edx",
         "invoke manager slot 1", "STATIC_INDIRECT"],
        ["IIPSLaunchRestore.dll", "0x5CC0-0x5CE5", "[esi+0xAC] + slot",
         "ReleaseResourceManagerII(manager)", "STATIC_DIRECT"],
        ["iips.dll", "0x1A254C", "[esi+0x19C] -> slot 1",
         "internal manager->manager dispatch -> sub_197F0",
         "STATIC_INDIRECT"],
    ]
    with open("ex064_manager_consumers.csv", "w", newline="",
              encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["module", "rva", "instruction_effect", "meaning",
                    "evidence"])
        w.writerows(cons)
    print("wrote ex064_manager_consumers.csv (%d rows)" % len(cons))

    # ---- ex064_bootstrap_edges.csv
    edges = [
        ["tcls_core.exe", "sub_8D2A2", "0x8D353", "LoadLibraryW (runtime path)",
         "loaded module name built at runtime", "STATIC_DIRECT"],
        ["IIPSLaunchRestore.dll", "export CreateIIPSRepair", "0x11590",
         "entry into the restore object", "STATIC_DIRECT"],
        ["IIPSLaunchRestore.dll", "sub_3AF0", "0x3C48",
         "LoadLibraryW(iips.dll)", "LoadLibraryW at IAT 0x1006C038",
         "STATIC_DIRECT"],
        ["IIPSLaunchRestore.dll", "sub_3AF0", "0x3C8F",
         "GetProcAddress(h, \"GetResourceManagerII\")",
         "string at VA 0x1006F43C", "STATIC_DIRECT"],
        ["IIPSLaunchRestore.dll", "sub_3AF0", "0x3C99",
         "call GetResourceManagerII()", "resolved through EAX",
         "STATIC_INDIRECT"],
        ["iips.dll", "GetResourceManagerII", "0x1C80",
         "manager* via operator new(0x410) + sub_11F20",
         "EX-063 STATIC_DIRECT", "STATIC_DIRECT"],
        ["iips.dll", "manager singleton", "0x1004EB68",
         "published to global", "EX-063 STATIC_DIRECT", "STATIC_DIRECT"],
        ["IIPSLaunchRestore.dll", "0x3CB2", "slot 26 (+0x68)",
         "manager slot 26 consumed", "NOT the slot-5 chain",
         "STATIC_DIRECT"],
        ["IIPSLaunchRestore.dll", "0x3CDC", "slot 1 (+0x04)",
         "manager slot 1 consumed", "on the same manager*",
         "STATIC_DIRECT"],
        ["iips.dll", "sub_1A270", "0x1A309", "manager slot 1 = sub_197F0",
         "dispatched on [mgr+0x19C], not on the returned manager",
         "STATIC_INDIRECT"],
        ["n/a", "?", "?", "unknown caller of tcls_core.exe entry",
         "WeGame/TCLS launcher boundary", "EXTERNAL_BOUNDARY"],
    ]
    with open("ex064_bootstrap_edges.csv", "w", newline="",
              encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["module", "function", "rva", "edge", "note", "evidence"])
        w.writerows(edges)
    print("wrote ex064_bootstrap_edges.csv (%d rows)" % len(edges))

    # ---- ex064_dynamic_getproc.csv (extra)
    gpa = [
        ["IIPSLaunchRestore.dll", "0x3C89", "iips.dll (hMod from 0x3C48)",
         "GetResourceManagerII", "EAX", "0x3C99", "STATIC_DIRECT"],
        ["IIPSLaunchRestore.dll", "0x744F", "iips.dll (hMod in [edi+0xAC])",
         "GetResourceManagerII", "EAX", "0x745F", "STATIC_DIRECT"],
        ["IIPSLaunchRestore.dll", "0x3608", "iips.dll (hMod in EDX arg)",
         "ReleaseResourceManagerII", "EAX", "0x3619", "STATIC_DIRECT"],
        ["IIPSLaunchRestore.dll", "0x5CD4", "iips.dll (hMod in [esi+0xAC])",
         "ReleaseResourceManagerII", "EAX", "0x5CE5", "STATIC_DIRECT"],
        ["tcls_core.exe", "0x8D382", "IIPSLaunchRestore.dll (hMod [ebp-0x48])",
         "CreateIIPSRepair", "[ebp-0x30]", "0x8D39F", "STATIC_DIRECT"],
        ["tcls_core.exe", "0x8D51F", "IIPSLaunchRestore.dll (hMod [ebp-0x20])",
         "RealeaseIIPSRepair", "[ebp-0x18]", "0x8D53F", "STATIC_DIRECT"],
    ]
    with open("ex064_dynamic_getproc.csv", "w", newline="",
              encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["module", "site_rva", "dll_source", "symbol",
                    "fnptr_storage", "call_site", "evidence"])
        w.writerows(gpa)
    print("wrote ex064_dynamic_getproc.csv (%d rows)" % len(gpa))

    # ---- ex064_iips_acquisition.csv (extra)
    acq = [
        ["tcls_core.exe", "0x8D353", "LoadLibraryW", "runtime-built path",
         "-> IIPSLaunchRestore.dll", "STATIC_DIRECT",
         "IIPS_LOAD_LaunchRestore = STATIC_CONFIRMED"],
        ["IIPSLaunchRestore.dll", "0x3C48", "LoadLibraryW",
         "runtime-built path ([esi+0x50..])", "-> iips.dll",
         "STATIC_DIRECT", "IIPS_LOAD_iips = STATIC_CONFIRMED"],
        ["IIPSLaunchRestore.dll", "0x3C8F", "GetProcAddress",
         "hMod = [esi+0xAC] (from 0x3C48)", "-> GetResourceManagerII",
         "STATIC_DIRECT", "GETRESOURCE_RESOLUTION = STATIC_CONFIRMED"],
        ["tcls_core.exe", "0x8D38A", "GetProcAddress",
         "hMod = [ebp-0x48] (from 0x8D353)", "-> CreateIIPSRepair",
         "STATIC_DIRECT", "REPAIR_RESOLUTION = STATIC_CONFIRMED"],
    ]
    with open("ex064_iips_acquisition.csv", "w", newline="",
              encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["module", "rva", "api", "argument", "result",
                    "evidence", "classification"])
        w.writerows(acq)
    print("wrote ex064_iips_acquisition.csv (%d rows)" % len(acq))


if __name__ == "__main__":
    main()
