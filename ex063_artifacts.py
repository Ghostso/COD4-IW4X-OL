# EX-063: emit the four required artifacts.
import csv
import json

from ex060_iips_cfg import Image, DLL


def main():
    img = Image(DLL)
    base = img.base

    # ---- ex063_manager_vtable.csv : the 0x1003934C vtable
    rows = []
    for n in range(64):
        s = 0x3934C + n * 4
        v = int.from_bytes(img.read(s, 4), "little")
        if not (base <= v < base + img.size):
            break
        t = v - base
        if not img.is_code(t):
            break
        rows.append(["0x1003934C", "0x3934C", n, "0x%X" % (n * 4),
                     "0x%X" % (base + s), "0x%X" % v,
                     "0x%X" % t, "sub_%X" % t,
                     "sub_197F0" if t == 0x197F0 else ""])
    with open("ex063_manager_vtable.csv", "w", newline="",
              encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["vtable_va", "vtable_rva", "slot", "slot_offset",
                    "slot_rva", "slot_value", "target_rva", "target_fn",
                    "note"])
        w.writerows(rows)
    print("wrote ex063_manager_vtable.csv (%d rows)" % len(rows))

    # ---- ex063_external_callers.csv
    ext = [
        ["codoMP_client_shipRetail.exe", "0x400000", "0xE659000",
         "0x1003934C", "no_reference", "EXTERNAL_BOUNDARY"],
        ["codoMP_client_shipRetailBase.dll", "0x10000000", "0x3991000",
         "0x1003934C", "no_reference", "EXTERNAL_BOUNDARY"],
        ["TenProxy.dll", "0x10000000", "0x29000",
         "0x1003934C", "no_reference", "STATIC_UNKNOWN"],
        ["GbSpy.dll", "0x10000000", "0xA6000",
         "0x1003934C", "no_reference", "STATIC_UNKNOWN"],
        ["GameRpcs.dll", "0x10000000", "0x272000",
         "0x1003934C", "no_reference", "STATIC_UNKNOWN"],
        ["TenRpcs.dll", "0x10000000", "0x1143000",
         "0x1003934C", "no_reference", "STATIC_UNKNOWN"],
        ["GDPLoader.dll", "0x10000000", "0x4F000",
         "0x1003934C", "no_reference", "STATIC_UNKNOWN"],
        ["PolicyProbe.dll", "0x10000000", "0x6DA000",
         "0x1003934C", "no_reference", "STATIC_UNKNOWN"],
        ["TCJ.dll", "0x10000000", "0x33E000",
         "0x1003934C", "no_reference", "STATIC_UNKNOWN"],
        ["iips.dll", "0x10000000", "0x55000",
         "0x1003934C", "2 x mov [reg],0x1003934C @0x11FB1,0x124FB",
         "STATIC_DIRECT"],
        ["iips.dll EXPORT", "-", "-",
         "GetResourceManagerII @0x1C80",
         "0x1CD4 call sub_11F20 (manager ctor)", "STATIC_DIRECT"],
        ["iips.dll EXPORT", "-", "-",
         "ReleaseResourceManager( II ) @0x1C60",
         "0x1C6E call [vt+0] (release)", "STATIC_DIRECT"],
    ]
    with open("ex063_external_callers.csv", "w", newline="",
              encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["module", "image_base", "image_size", "target",
                    "evidence", "classification"])
        w.writerows(ext)
    print("wrote ex063_external_callers.csv (%d rows)" % len(ext))

    # ---- ex063_manager_lifecycle.csv
    life = [
        ["export", "0x1C80", "GetResourceManagerII", "entry",
         "EXTERNAL_BOUNDARY"],
        ["guard", "0x1CA1", "test byte [0x1004EB6C],1", "idempotency",
         "STATIC_DIRECT"],
        ["alloc", "0x1CB1", "push 0x410", "sizeof(MANAGER)=1040",
         "STATIC_DIRECT"],
        ["alloc", "0x1CBE", "call sub_2BE34",
         "MSVCR80!operator new", "STATIC_DIRECT"],
        ["ctor", "0x1CD4", "call sub_11F20", "manager ctor",
         "STATIC_DIRECT"],
        ["pub", "0x1CD9", "mov [0x1004EB68], eax",
         "global singleton publication", "STATIC_DIRECT"],
        ["vt", "0x11FB1", "[this+0x00] = 0x1003934C",
         "final primary vtable", "STATIC_DIRECT"],
        ["field", "0x122AC", "[this+0x19C] = 0", "init to NULL",
         "STATIC_DIRECT"],
        ["dispatch", "0x1A2FC", "mov ecx,[esi+0x19C]",
         "manager holds a manager", "STATIC_DIRECT"],
        ["dispatch", "0x1A304", "mov edx,[eax+4]", "slot 1",
         "STATIC_DIRECT"],
        ["dispatch", "0x1A309", "call edx", "==> sub_197F0",
         "STATIC_INDIRECT"],
        ["slot1", "0x197F0", "mov esi, ecx", "this = nested manager",
         "STATIC_DIRECT"],
        ["factory", "0x197F7", "call sub_12760", "the factory",
         "STATIC_DIRECT"],
        ["factory", "0x12CD3", "push 0x1F0", "sizeof(CNIFS)=496",
         "STATIC_DIRECT"],
        ["factory", "0x12CD8", "call sub_2BE34", "operator new",
         "STATIC_DIRECT"],
        ["ctor", "0x12CF1", "call sub_90D0", "CNIFS ctor",
         "STATIC_DIRECT"],
        ["field", "0x91CF", "[this+0x60] = 0", "CNIFS init",
         "STATIC_DIRECT"],
        ["pub", "0x12D06", "[parent+0x19C] = CNIFS*", "CNIFS publication",
         "STATIC_DIRECT"],
        ["dispatch", "0x12F40", "mov ecx,[ebx+0x19C]", "read CNIFS*",
         "STATIC_DIRECT"],
        ["dispatch", "0x12F48", "mov edx,[eax+0x50]", "CNIFS slot 20",
         "STATIC_DIRECT"],
        ["dispatch", "0x12F56", "call edx", "==> InitInGameApp",
         "STATIC_INDIRECT"],
        ["entry", "0x9860", "CNIFS::InitInGameApp", "vtable method",
         "STATIC_DIRECT"],
        ["call", "0x99D2", "call sub_9570", "==> initIfsLib",
         "STATIC_DIRECT"],
        ["gate", "0x95D0", "cmp [this+0x60],0", "the +0x60 decision",
         "STATIC_DIRECT"],
        ["call", "0x96E9", "LoadLibraryW(ifs2.dll)", "first failure branch",
         "STATIC_DIRECT"],
    ]
    with open("ex063_manager_lifecycle.csv", "w", newline="",
              encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["stage", "rva", "instruction", "meaning", "evidence"])
        w.writerows(life)
    print("wrote ex063_manager_lifecycle.csv (%d rows)" % len(life))

    # ---- ex063_bootstrap_edges.csv
    boot = [
        ["external_module", "?", "iips.dll!GetResourceManagerII",
         "EXTERNAL_BOUNDARY",
         "no module in the CODOL directory references iips.dll's manager vt"],
        ["GetResourceManagerII", "iips.dll+0x1C80", "sub_11F20",
         "STATIC_DIRECT", "0x1CD4"],
        ["sub_11F20", "iips.dll+0x11F20", "manager object",
         "STATIC_DIRECT", "vtable 0x1003934C installed at 0x11FB1"],
        ["manager object", "0x1004EB68", "manager methods",
         "STATIC_DIRECT", "global singleton publication at 0x1CD9"],
        ["sub_1A270", "iips.dll+0x1A270", "sub_197F0",
         "STATIC_INDIRECT", "0x1A309 call edx, edx=[ecx+4], ecx=[esi+0x19C]"],
        ["sub_197F0", "iips.dll+0x197F0", "sub_12760",
         "STATIC_DIRECT", "0x197F7"],
        ["sub_12760", "iips.dll+0x12760", "sub_90D0",
         "STATIC_DIRECT", "0x12CF1"],
        ["sub_90D0", "iips.dll+0x90D0", "CNIFS object",
         "STATIC_DIRECT", "[this+0x60]=0 at 0x91CF"],
        ["sub_12760", "iips.dll+0x12F56", "CNIFS::InitInGameApp",
         "STATIC_INDIRECT", "slot 20 of 0x1003530C"],
        ["CNIFS::InitInGameApp", "iips.dll+0x9860",
         "CNIFS::initIfsLib", "STATIC_DIRECT", "0x99D2"],
        ["initIfsLib", "iips.dll+0x95D0", "ifs2 bring-up",
         "STATIC_DIRECT", "[this+0x60]==0 gate"],
        ["native_bootstrap", "?", "driver of the external caller",
         "EXTERNAL_BOUNDARY",
         "not recoverable from iips.dll; requires the importing module"],
    ]
    with open("ex063_bootstrap_edges.csv", "w", newline="",
              encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["from", "from_addr", "to", "evidence", "note"])
        w.writerows(boot)
    print("wrote ex063_bootstrap_edges.csv (%d rows)" % len(boot))


if __name__ == "__main__":
    main()
