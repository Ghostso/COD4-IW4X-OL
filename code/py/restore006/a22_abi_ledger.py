"""Agent 22 - the graded ABI evidence ledger.

Every ResourceManager ABI claim that the project has ever carried is listed
here with the verdict this round reached, and the specific evidence behind it.
Nothing is promoted to CONFIRMED without direct machine-code evidence.
"""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

# claim -> (grade, evidence, source)
LEDGER = [
    # ---------------- CONFIRMED ----------------
    ("RM_OBJECT_SIZE", "0x410", "CONFIRMED",
     "GetResourceManagerII does `push 0x410` before calling the allocator at "
     "RVA 0x1C80", "iips.dll RVA 0x1C80"),
    ("GET_RM_II_CALLING_CONVENTION", "__cdecl", "CONFIRMED",
     "epilogue is plain C3 (caller cleans); no `ret imm16`", "iips.dll RVA 0x1C80"),
    ("RELEASE_RM_II_CALLING_CONVENTION", "__cdecl", "CONFIRMED",
     "epilogue is plain C3; arg read from [esp+4]", "iips.dll RVA 0x1C60"),
    ("GET_RM_II_SINGLETON", "yes", "CONFIRMED",
     "guarded by byte at 0x1004EB6C, instance stored at 0x1004EB68",
     "iips.dll RVA 0x1C80"),
    ("RM_VTABLE_COUNT", "48", "CONFIRMED",
     "vtable installed at [this+0x00] has >=48 populated non-NULL slots; "
     "all point inside .text", "iips.dll RVA 0x1003929C"),
    ("RM_VTABLE_0", "deleting destructor", "CONFIRMED",
     "vtable[0] = RVA 0x118E0: `test byte [esp+4],1 ; ... ; ret 4` - the "
     "classic scalar-deleting-destructor idiom", "iips.dll RVA 0x1003929C"),
    ("RELEASE_CALLS_VTABLE_0", "yes", "CONFIRMED",
     "`mov eax,[ecx] ; mov edx,[eax] ; push 1 ; call edx`", "iips.dll RVA 0x1C60"),
    ("OBJECT_HAS_MULTIPLE_VPTRS", "yes", "CONFIRMED",
     "ctor writes vptrs at +0x00, +0x04, +0x20, +0x44", "iips.dll RVA 0x11F20"),
    ("VTABLE_SLOTS_NOT_NULL", "yes", "CONFIRMED",
     "all 48 slots hold in-image code pointers; unused ones share a common "
     "stub rather than being zeroed", "iips.dll RVA 0x1003929C"),
    ("RELEASE_IS_NULL_SAFE", "yes", "CONFIRMED",
     "`test ecx,ecx ; je` before the vtable call", "iips.dll RVA 0x1C60"),
    ("OBJECT_HEAP_ALLOCATED", "yes", "CONFIRMED",
     "ctor arg comes from MSVCR80 operator new (`??2@YAPAXI@Z`, IAT 0x1003328C)",
     "iips.dll RVA 0x1C80 -> 0x2BE34"),

    # ---------------- CANDIDATE / UNKNOWN ----------------
    ("NESTED_OBJECT_INPLACE_AT_0x70", "n/a", "DEMOTED_TO_UNKNOWN",
     "the ctor writes NO vptr at +0x70; the RESTORE_LOCALRM_001 sketch's "
     "0x70 offset has no machine-code support", "iips.dll RVA 0x11F20"),
    ("RM_OFFSET_3BC", "n/a", "DEMOTED_TO_UNKNOWN",
     "no +0x3BC write appears anywhere in the ctor", "iips.dll RVA 0x11F20"),
    ("NESTED_VTABLE1_COUNT", "n/a", "DEMOTED_TO_UNKNOWN",
     "the sketch's nested-vtable counts were never observed in the binary",
     "RESTORE_LOCALRM_001/LocalRM.cpp"),
    ("NESTED_VTABLE2_COUNT", "n/a", "DEMOTED_TO_UNKNOWN",
     "same as above", "RESTORE_LOCALRM_001/LocalRM.cpp"),
    ("VTABLE_1_IS_INITIALIZE", "n/a", "UNKNOWN",
     "slot 1 in the real vtable holds a shared stub, not an obvious Initialize",
     "iips.dll RVA 0x1003929C"),
    ("VTABLE_2_IS_CHECKSTATE", "n/a", "UNKNOWN",
     "no evidence; slot 2 is the same shared stub", "iips.dll RVA 0x1003929C"),
    ("VTABLE_3_IS_PROCESS", "n/a", "UNKNOWN",
     "no evidence; slot 3 is the same shared stub", "iips.dll RVA 0x1003929C"),
    ("DESTRUCTOR_OWNERSHIP", "n/a", "UNKNOWN",
     "the original never clears the singleton slot on release, so ownership "
     "and re-acquire semantics are undefined at this evidence level",
     "iips.dll RVA 0x1C60"),
    ("RESOURCE_MANAGER_SEMANTICS", "n/a", "UNKNOWN",
     "what the engine does with the 0x410 object is not established",
     "out of scope for a loader/ABI round"),
    ("THREAD_SAFETY", "n/a", "UNKNOWN",
     "the guard is a plain read-modify-write with no lock or interlocked op",
     "iips.dll RVA 0x1C80"),

    # ---------------- REFUTED ----------------
    ("GET_RM_II_STDCALL", "n/a", "REFUTED",
     "RESTORE_LOCALRM_001 declared `__stdcall`; the machine code ends in a "
     "plain C3 ret, so it is __cdecl", "iips.dll RVA 0x1C80"),
    ("RELEASE_RM_II_STDCALL", "n/a", "REFUTED",
     "RESTORE_LOCALRM_001 declared `__stdcall`; machine code ends in plain C3",
     "iips.dll RVA 0x1C60"),
    ("SINGLE_VPTR_OBJECT", "n/a", "REFUTED",
     "the object carries four distinct vptr fields, not one",
     "iips.dll RVA 0x11F20"),
]


def main():
    print("=" * 100)
    print("AGENT 22 - GRADED ABI EVIDENCE LEDGER")
    print("=" * 100)
    print("%-34s %-14s %-22s" % ("claim", "value", "verdict"))
    print("-" * 100)
    for claim, value, grade, ev, src in LEDGER:
        print("%-34s %-14s %-22s" % (claim, value, grade))
    print()
    for g in ("CONFIRMED", "CANDIDATE", "DEMOTED_TO_UNKNOWN", "UNKNOWN", "REFUTED"):
        items = [c for c, _, gr, _, _ in LEDGER if gr == g]
        if items:
            print("%-20s (%d): %s" % (g, len(items), ", ".join(items)))
    print()
    print("=" * 100)
    print("EVIDENCE DETAIL")
    print("=" * 100)
    for claim, value, grade, ev, src in LEDGER:
        print("[%s] %s" % (grade, claim))
        print("    value  : %s" % value)
        print("    source : %s" % src)
        print("    why    : %s" % ev)
        print()

    out = {
        "round": "RESTORE-LOCALRM-006",
        "summary": {
            g: sum(1 for _, _, gr, _, _ in LEDGER if gr == g)
            for g in ("CONFIRMED", "CANDIDATE", "DEMOTED_TO_UNKNOWN", "UNKNOWN", "REFUTED")
        },
        "entries": [
            {"claim": c, "value": v, "verdict": g, "evidence": e, "source": s}
            for c, v, g, e, s in LEDGER
        ],
    }
    p = os.path.join(HERE, "evidence", "a22_abi_ledger.json")
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)
    print("ledger written to %s" % p)


if __name__ == "__main__":
    main()
