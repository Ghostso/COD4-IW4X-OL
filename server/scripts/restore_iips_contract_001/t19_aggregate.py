"""RESTORE-IIPS-CONTRACT-001 / Task 15 - aggregate all evidence into the
machine-readable record required by the round.

Produces restore_iips_contract_001/evidence/iips_contract.json.

Evidence levels used strictly:
    CONFIRMED / STRONG_CANDIDATE / CANDIDATE / UNKNOWN / REFUTED /
    NOT_OBSERVED / INSTRUMENTATION_BLOCKED
"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EV = os.path.join(ROOT, "restore_iips_contract_001", "evidence")


def rd(name):
    p = os.path.join(EV, name)
    if not os.path.exists(p):
        return None
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def main():
    t01 = rd("t01_iipsinit_identity.json")
    t02 = rd("t02_window_class_owner.json")
    t03 = rd("t03_getrm_backward.json")
    t04 = rd("t04_disasm_key_sites.json")
    t05 = rd("t05_second_site.json")
    t06 = rd("t06_log_string_table.json")
    t07 = rd("t07_iipsinit_origin.json")
    t09 = rd("t09_init_contract_sites.json")
    t11 = rd("t11_sendmessage_import.json")
    t12 = rd("t12_ab_differential.json")
    t13 = rd("t13_class_owner_and_8189fec.json")
    t14 = rd("t14_8189_relations.json")
    t15 = rd("t15_ffffffff_and_sync.json")
    t16 = rd("t16_pipe_and_sharename.json")
    t17 = rd("t17_named_object_runtime.json")
    t18 = rd("t18_ifs_dll_missing.json")
    t20 = rd("t20_sandbox_ifs.json")
    t21 = rd("t21_is_init_entered.json")
    t22 = rd("t22_token_privilege.json")

    out = {
        "round": "RESTORE-IIPS-CONTRACT-001",
        "scope": "Why IIPS provider initialisation never reaches "
                 "GetResourceManagerII, and where conditions A and B first diverge "
                 "before that point.",
        "evidence_policy": "An empty result is NOT_OBSERVED, never 'never occurs'.",

        "static_findings": {
            "iipsinit_is_not_a_window_class_literal": {
                "level": "CONFIRMED",
                "detail": (
                    "'iipsinit' occurs exactly once in the EXE, as the MSVC "
                    "decorated symbol '?iipsinit' at file offset 0x75B90C, inside a "
                    "run of type descriptors ('.?AVdwRoom@@', '.?AVdwRoomImp@@', "
                    "'.?AVCallsign_...@@'; 1251 '.?AV' occurrences in total). "
                    "Neither iips.dll nor LocalRM_v3.dll contains the literal at "
                    "all (count = 0 in both). It is a SYMBOL name, not a window "
                    "class or title string, and must not be read as an "
                    "initialisation-function name."),
                "evidence": ["t01_iipsinit_identity.json", "t02_window_class_owner.json",
                             "t07_iipsinit_origin.json"],
            },
            "single_use_site_of_the_symbol": {
                "level": "CONFIRMED",
                "detail": "The address of '?iipsinit' is referenced exactly once in "
                          "the EXE, at RVA 0x18F45A (section .tp3). No user32 "
                          "class-registration API name sits within +/-0x400 of it.",
                "evidence": ["t08_iipsinit_use_site.json"],
            },
            "getrm_static_caller": {
                "level": "CONFIRMED",
                "detail": "GetResourceManagerII (RVA 0x1C80) has exactly ONE "
                          "in-image reference: the export-directory entry at "
                          ".rdata 0x41C00. There is no internal caller.",
                "evidence": ["t03_getrm_backward.json"],
            },
            "static_chain_status": {
                "level": "STATIC_CHAIN_BLOCKED_AT_EXTERNAL_BOUNDARY",
                "detail": "Callers of the export live outside iips.dll and reach it "
                          "by name via GetProcAddress (established in "
                          "RESTORE-ENGINE-BRIDGE-003), so no caller chain can be "
                          "followed and none is fabricated.",
            },
            "constructor_call_sites": {
                "level": "CONFIRMED",
                "detail": "The ResourceManager constructor (RVA 0x11F20) has exactly "
                          "two callers: 0x1CD4 inside GetResourceManagerII (lazy "
                          "singleton path, stores the object into the singleton slot "
                          "0x1004EB68) and 0x1024D (a separate function that passes "
                          "the object to 0x4280 with the string "
                          "'[ResourceManager::ResourceManager()][OK]' and does NOT "
                          "touch the singleton slot or the guard).",
                "evidence": ["t03_getrm_backward.json", "t04_disasm_key_sites.json",
                             "t05_second_site.json"],
            },
            "provider_init_contract": {
                "level": "CONFIRMED",
                "detail": "iips.dll's own log-message table documents its "
                          "initialisation contract in the provider's own words "
                          "(327 bracketed messages). The ordered sequence of "
                          "ResourceManagerII::Initialize is recorded below.",
                "sequence": t09["contract_sequence"] if t09 else None,
                "evidence": ["t06_log_string_table.json", "t09_init_contract_sites.json"],
            },
            "readiness_callback": {
                "level": "CONFIRMED",
                "detail": "At RVA 0x17E90 the provider issues a readiness message: "
                          "push 0 (lParam); push 1 (wParam); push 0x506D (Msg); "
                          "push edx (hWnd); call dword [0x10033428]. The IAT slot "
                          "0x10033428 resolves to USER32!PostMessageA -- the log "
                          "string calls it 'SendMessage' but the import table is "
                          "authoritative. Immediate 0x506D appears 5 times in "
                          "iips.dll (0x15671, 0x179E1, 0x17BC7, 0x17C4E, 0x17E8B).",
                "evidence": ["t10_callback_handoff.json", "t11_sendmessage_import.json"],
            },
            "localrm_v3_carries_original_code_but_cannot_execute_it": {
                "level": "CONFIRMED",
                "detail": "LocalRM_v3.dll contains byte-identical copies of the "
                          "original's .text/.rdata (verified at RVA 0x17E86), but "
                          "its only reachable additions are the two .localrm "
                          "exports. The original init path is present but never "
                          "invoked.",
                "evidence": ["t11_sendmessage_import.json"],
            },
        },

        "error_value_8189fec": {
            "displayed_value": {
                "level": "CONFIRMED",
                "detail": "Observed in the condition-A dialog text as "
                          "'初始化IIPS错误：8189fec。'",
            },
            "produced_value": {
                "level": "NOT_OBSERVED",
                "detail": "No literal '8189fec'/'8189FEC' (ASCII or UTF-16) exists "
                          "in the EXE, Base.dll, iips.dll or LocalRM_v3.dll, so the "
                          "value is produced at runtime and formatted to lowercase "
                          "hex with no '0x' prefix (EXE has 33 '%x' and only 3 "
                          "'0x%x').",
            },
            "control_flow_value": {
                "level": "UNKNOWN",
                "detail": "Cannot be shown to gate control flow without reading the "
                          "protected decision point.",
            },
            "semantics": "UNKNOWN",
            "numeric_note": "0x08189FEC as a 32-bit value (the token has 7 hex "
                            "digits); bit 31 is clear, so it is not a negative "
                            "HRESULT-style code.",
            "evidence": ["t13_class_owner_and_8189fec.json"],
        },

        "relation_8189fec_to_8189FFCE": {
            "level": "NOT_EQUATED",
            "detail": (t14["verdict"] if t14 else None),
            "detail_short": "'8189fec' is 7 hex digits; '8189FFCE' is 8. High 16 "
                            "differ (0x0818 vs 0x8189), low 16 differ (0x9FEC vs "
                            "0xFFCE). Neither is a byte literal in any shipped "
                            "binary. Equating them is REFUTED as unsupported.",
            "evidence": ["t14_8189_relations.json"],
        },

        "termination_0xFFFFFFFF": {
            "level": "CANDIDATE",
            "detail": "Condition B self-terminated with exit code 0xFFFFFFFF in 4 of "
                      "5 EB-003 runs (B2/B3/B4/B5) at ~30.5s; B1 predates the "
                      "exit-code observation. The literal 0xFFFFFFFF occurs "
                      "extremely often in all images (EXE 17221, Base.dll 43239, "
                      "iips.dll 9080) so its mere presence is not attribution. Its "
                      "semantics (return value vs ExitProcess argument vs "
                      "thread/HRESULT) are NOT established.",
            "semantics": "UNKNOWN",
            "evidence": ["t15_ffffffff_and_sync.json"],
        },

        "dependency_ifs_dll": {
            "level": "CONFIRMED (necessary, NOT sufficient)",
            "detail": (
                "The provider's contract calls LoadLibrary('IFS.dll') (log string "
                "'[ResourceManagerII::Initialize()][LoadLibrary IFS.dll]' at "
                "0x36318). Empirically, in a 32-bit host with IIPS\\ as CWD and as "
                "the DLL directory: LoadLibraryA('IFS.dll') FAILS with err=126 "
                "(ERROR_MOD_NOT_FOUND), and LoadLibraryA('ifs.dll') also fails. "
                "No file named IFS.dll exists anywhere in the workspace. The file "
                "that does exist, IFS2.dll, exports exactly the three entry points "
                "the provider looks up: CreateIFSLibDll (ord 1), DestoryIFSLibDll "
                "(ord 2), IFSDllVerifyApiCompatable (ord 3). iips.dll never "
                "mentions 'IFS2' (count = 0)."),
            "single_factor_experiment": {
                "level": "CONFIRMED",
                "detail": (
                    "With IFS2.dll exposed as IFS.dll inside an isolated sandbox "
                    "(original install untouched, SHA256 re-verified), "
                    "LoadLibraryA('IFS.dll') SUCCEEDS (base 0x10000000, all three "
                    "entry points resolvable). Yet the run still shows only the "
                    "empty-text iipsinit window: IIPSHostApp.exe is never launched, "
                    "no named objects appear, and the contract does not advance."),
                "evidence": ["t20_sandbox_ifs.json"],
            },
            "note": ("This is a dependency-availability finding, and the single-factor "
                     "experiment shows it is NECESSARY BUT NOT SUFFICIENT. It affects "
                     "BOTH conditions equally, so it is not by itself the A/B "
                     "differentiator."),
            "evidence": ["t18_ifs_dll_missing.json", "t17_named_object_runtime.json",
                         "t20_sandbox_ifs.json"],
        },

        "contract_progress": {
            "level": "CONFIRMED",
            "detail": (
                "Using the provider's own declared side-effect order, the sequence "
                "is: (1) window created, (2) IFS.dll loaded, (3) IIPSHostApp.exe "
                "launched, (4) pipe connect, (5) ShareState objects. Across the runs "
                "observed with a single instrument, step 1 is observed in 3/3 and "
                "steps 2 and 3 in 0/3. The only run where IFS*.dll loads is the "
                "sandbox experiment, and there it loads because the file was placed "
                "in the search path, not because the provider reached that step."),
            "instrumentation_note": (t21["instrumentation_note"] if t21 else None),
            "conclusion": (t21["conclusion"] if t21 else None),
            "evidence": ["t21_is_init_entered.json"],
        },

        "unmet_precondition_candidate": {
            "level": "CANDIDATE",
            "detail": (
                "The interval between step 1 (window created) and step 2 "
                "(LoadLibrary IFS.dll) contains the contract's SetPrivilege / "
                "SE_CREATE_GLOBAL_NAME check, and the later steps need Global\\ "
                "named objects. A plain token query shows SeCreateGlobalPrivilege "
                "is ABSENT from this process token (5 privileges total; only "
                "SeChangeNotifyPrivilege enabled) and the process is not elevated. "
                "If the provider's SetPrivilege step cannot obtain that privilege, "
                "the contract would stop before creating any Global\\ object."),
            "why_candidate_not_confirmed": (
                "This is a property of the OBSERVER's token, not proof that the "
                "target's SetPrivilege step actually failed, and not proof that the "
                "provider stops there. It constrains the interval; it does not "
                "close it."),
            "token_facts": (t22.get("se_create_global") if t22 else None),
            "is_admin": (t22.get("is_admin") if t22 else None),
            "evidence": ["t22_token_privilege.json"],
        },

        "named_object_contract": {
            "level": "CONFIRMED",
            "detail": "Exact names the provider opens/creates, from its .rdata:",
            "objects": [
                "Global\\SharedSpaceName_     (OpenFileMappingA + MapViewOfFile)",
                "Global\\FDTFileMutxtName_    (mutex)",
                "Global\\ReadBitMapInfos_     (file mapping)",
                "Global\\IIPSShareState_MMF_  (share-state MMF)",
                "Global\\IIPSShareState_Mutex_(share-state mutex)",
                "Global\\DownloadingFileInfos_(file mapping)",
                "\\\\.\\Pipe\\                (pipe prefix)",
            ],
            "host_process": "IIPSHostApp.exe  (launched with '/mode iipslaunch')",
            "ifs_library": "IFS.dll (missing; only IFS2.dll present)",
            "imports_present": ("CreateFileA/W, ReadFile x16, WriteFile x2, "
                                "CreateEventA/W, SetEvent, WaitForSingleObject, "
                                "WaitForMultipleObjects, CreateMutexA, "
                                "CreateFileMappingA, OpenFileMappingA, "
                                "MapViewOfFile x2, CreateThread, PostMessageA, "
                                "CreateWindowExA. CreateNamedPipe/ConnectNamedPipe/"
                                "WaitNamedPipe are NOT imported, so the 'pipe "
                                "connect' is performed with CreateFile."),
            "evidence": ["t16_pipe_and_sharename.json", "t15_ffffffff_and_sync.json"],
        },

        "ab_differential": {
            "level": "CONFIRMED",
            "runs": (t12["runs"] if t12 else None),
            "last_common_observable_state": (t12["last_common_observable_state"]
                                             if t12 else None),
            "first_divergence": (t12["first_divergence"] if t12 else None),
            "detail": (
                "Both conditions load iips.dll and BOTH create a window whose "
                "class reads back as 'iipsinit'. The divergence is not the window's "
                "existence but: (a) its TEXT -- 'Environment List Box' in A, empty "
                "in B; and (b) the presence of the #32770 '致命错误' dialog in A "
                "only. A additionally creates 5 windows (MSCTFIME UI, SoPY_Hint, "
                "SoPY_UI, Sogou_TSF_UI, #32770) that B does not; those are IME / "
                "Sogou / Windows subsystems, not provider artefacts."),
            "evidence": ["t12_ab_differential.json"],
        },
    }

    with open(os.path.join(EV, "iips_contract.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)
    print("wrote %s" % os.path.join(EV, "iips_contract.json"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
