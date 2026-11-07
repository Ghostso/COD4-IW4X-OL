"""RESTORE-IIPS-CONTRACT-001 / Task 06 - locate the ResourceManagerII::Initialize sites.

Task 04 recovered iips.dll's own log table, which spells out the provider's
initialisation contract in the provider's own words:

    ResourceManagerII::Initialize()
      begin
      getkey
      GetModulePath(mainModuleDir)
      SetPrivilege / SE_CREATE_GLOBAL_NAME
      IIPSWndMsgProcessor::Initialize   <- creates a window
      GetMainModulePath(configFilePath)
      LoadLibrary IFS.dll               <- external dependency
      NifsInitError
      IIPSSTATE_START_REPAIR_IFSFILE
      OpenHostShareInfo
      LaunchIIPSHostApp                 <- launches a child process
      m_iipsClient connect              <- PIPE
      "pipe connect succeed(start other action of init)"
    InitializeWorkAfterClientConnected()
      m_iipsShareState.Open()
      LoadFileList
      m_resUseRec.Load()
      check m_sharedSpaces
      "ResourceManagerII::Initialize() succeed"
      SendMessage(m_hCallbackHWnd, ...)  <- CALLBACK HANDOFF TO ENGINE

This script locates the code that references these message strings and the
callback HWND member, so the contract is tied to actual instruction sites.
"""
import json
import os
import struct
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GAME = os.path.join(ROOT, "COD OL")
OUT = os.path.join(ROOT, "restore_iips_contract_001", "evidence")
IIPS = os.path.join(GAME, "IIPS", "iips.dll")


def load(path):
    d = open(path, "rb").read()
    pe = struct.unpack_from("<I", d, 0x3C)[0]
    nsec = struct.unpack_from("<H", d, pe + 6)[0]
    ib = struct.unpack_from("<I", d, pe + 24 + 28)[0]
    so = pe + 24 + 224
    secs = []
    for i in range(nsec):
        o = so + i * 40
        name = d[o:o + 8].rstrip(b"\0").decode("latin1")
        vs, va, rs, rp = struct.unpack_from("<IIII", d, o + 8)
        secs.append({"name": name, "va": va, "vsize": vs, "raw": rp, "rsize": rs})
    return d, pe, ib, secs


def o2r(secs, off):
    for s in secs:
        if s["raw"] <= off < s["raw"] + s["rsize"]:
            return s["va"] + (off - s["raw"])
    return None


def r2o(secs, rva):
    for s in secs:
        if s["va"] <= rva < s["va"] + max(s["vsize"], s["rsize"]):
            off = s["raw"] + (rva - s["va"])
            if 0 <= off < s["raw"] + s["rsize"]:
                return off
    return None


def main():
    os.makedirs(OUT, exist_ok=True)
    d, pe, ib, secs = load(IIPS)
    rep = {"image_base": "0x%X" % ib, "sites": {}}
    print("=== Task 06: ResourceManagerII::Initialize contract sites ===")
    print("  iips.dll image base = 0x%08X" % ib)
    print()

    # Each string's address, and who references it.
    msg_strings = [
        "ResourceManagerII::ResourceManagerII()][OK",
        "ResourceManagerII::Initialize()][begin",
        "ResourceManagerII::Initialize()][LoadLibrary IFS.dll",
        "ResourceManagerII::Initialize()][LaunchIIPSHostApp start",
        "ResourceManagerII::Initialize()][m_iipsClient connect",
        "pipe connect succeed(start other action of init)",
        "ResourceManagerII::InitializeWorkAfterClientConnected()][m_iipsShareState open",
        "ResourceManagerII::InitializeWorkAfterClientConnected()][LoadFileList",
        "ResourceManagerII::InitializeWorkAfterClientConnected()][ResourceManagerII::Initialize() succeed",
        "ResourceManagerII::InitializeWorkAfterClientConnected()][SendMessage][m_hCallbackHWnd",
        "IIPSWndMsgProcessor::Initialize()][Initialize",
    ]
    for s in msg_strings:
        b = s.encode("latin1")
        # the full string in the table is prefixed with '['; find the bracketed form
        full = b"[" + b
        off = d.find(full)
        if off < 0:
            off = d.find(b)
        if off < 0:
            rep["sites"][s] = {"found": False}
            print("  NOT FOUND: %s" % s)
            continue
        rva = o2r(secs, off)
        va = ib + rva if rva is not None else None
        # find code references to that VA
        refs = []
        if va is not None:
            needle = struct.pack("<I", va)
            p = 0
            while True:
                i = d.find(needle, p)
                if i < 0:
                    break
                rr = o2r(secs, i)
                if rr is not None:
                    refs.append("0x%X" % rr)
                p = i + 1
        rep["sites"][s] = {"off": "0x%X" % off, "rva": "0x%X" % rva,
                           "va": "0x%X" % va, "code_refs": refs}
        print("  %-62s VA 0x%08X refs=%d %s"
              % (s[-60:], va, len(refs), ", ".join(refs[:5])))

    # m_hCallbackHWnd is a member; find the SendMessage(callback) site shape:
    # 'push imm32(msg) ; push [obj+off] ; call [SendMessageA]'
    print()
    print("  SendMessage / PostMessage imports in iips.dll:")
    for api in (b"SendMessageA", b"SendMessageW", b"PostMessageA", b"PostMessageW",
                b"RegisterClassExA", b"CreateWindowExA", b"CreateWindowExW"):
        c = d.count(api)
        if c:
            print("     %-16s %d" % (api.decode(), c))

    rep["contract_sequence"] = [
        "ResourceManagerII::ResourceManagerII() -> OK",
        "ResourceManagerII::Initialize() begin",
        "SetPrivilege / SE_CREATE_GLOBAL_NAME",
        "IIPSWndMsgProcessor::Initialize (window creation)",
        "LoadLibrary(IFS.dll)",
        "LaunchIIPSHostApp",
        "m_iipsClient connect (named pipe)",
        "InitializeWorkAfterClientConnected: ShareState.Open, LoadFileList, resUseRec.Load",
        "ResourceManagerII::Initialize() succeed",
        "SendMessage(m_hCallbackHWnd, ...)   <-- callback handoff to the Engine",
    ]
    print()
    print("  CONTRACT SEQUENCE (from the provider's own log table):")
    for i, s in enumerate(rep["contract_sequence"], 1):
        print("     %2d. %s" % (i, s))

    with open(os.path.join(OUT, "t09_init_contract_sites.json"), "w", encoding="utf-8") as f:
        json.dump(rep, f, indent=2)
    print()
    print("wrote %s" % os.path.join(OUT, "t09_init_contract_sites.json"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
