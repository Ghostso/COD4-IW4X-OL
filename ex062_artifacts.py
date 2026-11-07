# EX-062: emit the required CSV/JSON artifacts.
import csv
import json

from ex060_iips_cfg import Image, DLL


def main():
    img = Image(DLL)
    base = img.base

    rows = []

    def walk(va, label):
        rva = va - base
        for i in range(0, 0x100):
            s = rva + i * 4
            raw = img.read(s, 4)
            if len(raw) < 4:
                break
            v = int.from_bytes(raw, "little")
            if not (base <= v < base + img.size):
                break
            t = v - base
            if not img.is_code(t):
                break
            rows.append([label, "0x%X" % va, "0x%X" % rva, i,
                         "0x%X" % (i * 4), "0x%X" % s, "0x%X" % v,
                         "0x%X" % t, "0x%X" % (base + t)])

    walk(0x1003530C, "CNIFS_PRIMARY")
    walk(0x10035204, "CNIFS_VT2")
    walk(0x100352EC, "CNIFS_VT3")
    walk(0x100353E8, "CNIFS_VT4")
    walk(0x10035408, "CNIFS_VT5_subsidiary")
    walk(0x10035418, "CNIFS_VT6_subsidiary")
    walk(0x100351F8, "CNIFS_VT7_subsidiary")
    walk(0x1003934C, "MANAGER_VT_3934C")

    with open("ex062_vtable.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["vtable_label", "vtable_va", "vtable_rva", "slot",
                    "slot_offset", "slot_rva", "slot_value", "target_rva",
                    "target_va"])
        w.writerows(rows)
    print("wrote ex062_vtable.csv (%d rows)" % len(rows))

    edges = [
        ["call", "0x12CD8", "alloc", "operator new (sub_2BE34)",
         "STATIC_DIRECT", "push 0x1F0 literal size 496"],
        ["alloc", "EAX", "arg", "0x12CF0 push eax",
         "STATIC_DIRECT", "saved at 0x12CE0 mov [esp+0x24],eax"],
        ["call", "0x12CF1", "ctor", "sub_90D0", "STATIC_DIRECT",
         "CNIFS constructor, this=arg1, ret 4"],
        ["ctor", "0x91CF", "field", "[this+0x60] = 0", "STATIC_DIRECT",
         "ebx=0 from xor ebx,ebx at 0x90FF"],
        ["ctor", "0x9134", "vtable", "[this+0x0] = 0x1003530C",
         "STATIC_DIRECT", "FINAL primary vtable (2nd of 2 writes)"],
        ["ctor", "0x91FF", "return", "EAX = this", "STATIC_DIRECT",
         "mov eax, ebp"],
        ["return", "EAX", "capture", "0x12CF6 mov edi, eax",
         "STATIC_DIRECT", ""],
        ["capture", "EDI", "publication", "0x12D06 mov [esi+0x19C], edi",
         "STATIC_DIRECT", "ESI = parent object from 0x12CBD"],
        ["publication", "[parent+0x19C]", "retrieval",
         "0x12F40 mov ecx, [ebx+0x19C]", "STATIC_DIRECT",
         "same RVA 0x19C, no intervening write on this path"],
        ["retrieval", "ECX", "vtable_fetch", "0x12F46 mov eax, [ecx]",
         "STATIC_DIRECT", "loads CNIFS primary vtable 0x1003530C"],
        ["vtable_fetch", "[vtable+0x50]", "slot_fetch",
         "0x12F48 mov edx, [eax+0x50]", "STATIC_DIRECT",
         "slot 20 = 0x10009860"],
        ["slot_fetch", "EDX", "dispatch", "0x12F56 call edx",
         "STATIC_INDIRECT", "ECX preserved = CNIFS this (verified)"],
        ["dispatch", "0x9860", "entry", "CNIFS::InitInGameApp",
         "STATIC_DIRECT", "ECX == this; 0x989B mov ebp, ecx"],
        ["entry", "0x99D2", "call", "sub_9570 CNIFS::initIfsLib",
         "STATIC_DIRECT", "push ebp as arg1"],
        ["initIfsLib", "0x95D0", "gate", "[this+0x60] == 0 ?",
         "STATIC_DIRECT", "jne 0x9818 if non-zero"],
        ["gate", "0x9818", "exit", "AL = 1 (short-circuit)",
         "STATIC_REACHABLE", "no LoadLibraryW"],
        ["gate", "0x96E9", "call", "LoadLibraryW(iipsdir/ifs2.dll)",
         "STATIC_DIRECT", "IAT 0x10033010"],
        ["initIfsLib", "0x977C", "call", "GetProcAddress(CreateIFSLibDll)",
         "STATIC_INDIRECT", "esi = IAT 0x10033014"],
        ["initIfsLib", "0x97A5", "call", "CreateIFSLibDll()",
         "STATIC_INDIRECT", "eax = [this+0x58]"],
        ["initIfsLib", "0x97A9", "field", "[this+0x60] = EAX",
         "STATIC_DIRECT", "the only non-zero writer"],
        ["initIfsLib", "0x97CC", "call", "GetProcAddress(DestoryIFSLibDll)",
         "STATIC_INDIRECT", ""],
        ["dtor", "0x92D6", "call", "[this+0x5C](&[this+0x60])",
         "STATIC_INDIRECT", "DestoryIFSLibDll teardown"],
        ["dtor", "0x92E2", "call", "KERNEL32!FreeLibrary([this+0x54])",
         "STATIC_DIRECT", ""],
    ]
    with open("ex062_lifecycle_edges.csv", "w", newline="",
              encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["src_kind", "src", "dst_kind", "dst", "evidence", "note"])
        w.writerows(edges)
    print("wrote ex062_lifecycle_edges.csv (%d rows)" % len(edges))

    chain = [
        ["allocation", "0x12CD8", "sub_2BE34", "EAX", "fresh 0x1F0 block",
         "STATIC_DIRECT"],
        ["ctor_arg", "0x12CF0", "sub_90D0", "stack arg1", "EAX pushed",
         "STATIC_DIRECT"],
        ["ctor_this", "0x90F4", "sub_90D0", "EBP", "[esp+0x24]",
         "STATIC_DIRECT"],
        ["ctor_ret", "0x91FF", "sub_90D0", "EAX", "mov eax, ebp",
         "STATIC_DIRECT"],
        ["capture", "0x12CF6", "sub_12760", "EDI", "mov edi, eax",
         "STATIC_DIRECT"],
        ["publish", "0x12D06", "sub_12760", "[ESI+0x19C]",
         "mov [esi+0x19C],edi", "STATIC_DIRECT"],
        ["retrieve", "0x12F40", "sub_12760", "ECX", "mov ecx,[ebx+0x19C]",
         "STATIC_DIRECT"],
        ["vtable", "0x12F46", "sub_12760", "EAX", "mov eax,[ecx]",
         "STATIC_DIRECT"],
        ["slot", "0x12F48", "sub_12760", "EDX", "mov edx,[eax+0x50]",
         "STATIC_DIRECT"],
        ["dispatch", "0x12F56", "sub_12760", "call edx", "ECX = this",
         "STATIC_INDIRECT"],
        ["entry", "0x9860", "CNIFS::InitInGameApp", "ECX", "-",
         "STATIC_DIRECT"],
        ["entry_this", "0x989B", "CNIFS::InitInGameApp", "EBP",
         "mov ebp,ecx", "STATIC_DIRECT"],
        ["arg_to_initIfsLib", "0x99D1", "CNIFS::InitInGameApp", "push ebp",
         "arg1 = this", "STATIC_DIRECT"],
        ["initIfsLib_this", "0x95A5", "CNIFS::initIfsLib", "EBP",
         "[esp+0xA0] = arg1", "STATIC_DIRECT"],
        ["gate", "0x95D0", "CNIFS::initIfsLib", "cmp [ebp+0x60], 0",
         "the +0x60 decision", "STATIC_DIRECT"],
        ["write60", "0x97A9", "CNIFS::initIfsLib", "[EBP+0x60]",
         "mov [ebp+0x60],eax", "STATIC_DIRECT"],
        ["consume60", "0x9A2B", "CNIFS::InitInGameApp", "ECX",
         "mov ecx,[ebp+0x60]", "STATIC_DIRECT"],
    ]
    with open("ex062_this_chain.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["stage", "rva", "function", "register_slot",
                    "instruction", "evidence"])
        w.writerows(chain)
    print("wrote ex062_this_chain.csv (%d rows)" % len(chain))

    cmap = {
        "0x9860_CNIFS_InitInGameApp": {
            "immediate_callers": 0,
            "function_pointer_occurrences": 1,
            "occurrence": {
                "rva": "0x3535C",
                "section": ".rdata",
                "belongs_to": "CNIFS primary vtable 0x1003530C",
                "slot": 20,
                "slot_offset": "0x50",
            },
            "dispatch_site": {
                "function": "sub_12760",
                "rva": "0x12F56",
                "form": "call edx (indirect)",
                "chain": "mov ecx,[ebx+0x19C] ; mov eax,[ecx] ; "
                         "mov edx,[eax+0x50] ; call edx",
            },
            "classification": "vtable method (slot 20 of 0x1003530C)",
        },
        "0x197F0_sub_197F0": {
            "immediate_callers": 0,
            "function_pointer_occurrences": 1,
            "occurrence": {
                "rva": "0x39350",
                "section": ".rdata",
                "belongs_to": "manager vtable 0x1003934C",
                "slot": 1,
                "slot_offset": "0x04",
            },
            "calls": {"0x197F7": "sub_12760 (the factory)"},
            "calls_InitInGameApp_directly": False,
            "classification": "vtable method (slot 1 of 0x1003934C); "
                              "initialiser entry that invokes the factory",
        },
        "0x90D0_CNIFS_ctor": {
            "immediate_callers": 1,
            "caller": {"function": "sub_12760", "rva": "0x12CF1"},
            "classification": "constructor",
        },
        "0x9240_CNIFS_dtor": {
            "note": "reached via vtable 0x1003530C slot 19 / 0x9220 thunk",
            "classification": "destructor",
        },
    }
    with open("ex062_caller_map.json", "w") as f:
        json.dump(cmap, f, indent=1)
    print("wrote ex062_caller_map.json")


if __name__ == "__main__":
    main()
