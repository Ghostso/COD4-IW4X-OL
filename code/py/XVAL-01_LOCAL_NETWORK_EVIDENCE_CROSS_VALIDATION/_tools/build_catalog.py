# -*- coding: utf-8 -*-
"""XVAL-01 provenance catalog builder. Read-only: hashes listed artefacts, writes a CSV.
No target client/server is executed; no injection; no memory reads."""
import csv, hashlib, os, subprocess, sys, datetime

ROOT = r"D:\BaiduNetdiskDownload\使命召唤OL"
DL   = r"D:\BaiduNetdiskDownload"

# (Material_ID, absolute path, Provenance_Class, Source_Version, Protocol_Modules, Citation, Notes)
CATALOG = [
 # ---- frozen binary samples ----
 ("BIN-C-2697", rf"{DL}\CODOL.NET\Game\CODOL_2.6.9.7\codoMP_client_shipRetail.exe", "PRIMARY-BINARY", "CODOL 2.6.9.7 client (packed)", "transport/session/gamestate/configstring/snapshot consumers", "atlas 00_SAMPLE_MATRIX §2; E14 01 §1", "Target client; TenProtect-wrapped"),
 ("BIN-C-2697-REC", rf"{DL}\CODOL.NET\Game\CODOL_2.6.9.7\CODOL_2697_Launcher\runtime\game\aplib-recovered\codol2697-static-candidate.bin", "PRIMARY-BINARY (recovered)", "2.6.9.7 aplib static recovery", "same as BIN-C-2697 (.text byte-identical)", "E06 08_VERDICT Q2; E14 01 §1", "Static aplib recovery, NOT a runtime dump"),
 ("BIN-S-2697", rf"{DL}\CODOL.NET\Game\CODOL_2.6.9.7\CODOL_2697_Launcher\runtime\game\server2697\native\bin2697\codol_dedrun.exe", "PRIMARY-BINARY", "2697 native dedicated server", "reliable/gamestate/configstring/snapshot writers; netchan", "atlas 00_SAMPLE_MATRIX §5; 2697_SA 04", "Protocol oracle (writer side)"),
 ("BIN-C-1113", rf"{DL}\CODOL.NET\Game\CODOL_1.1.1.13\CODOL_Client\codoMP_client_shipRetail.exe", "PRIMARY-BINARY", "CODOL 1.1.1.13 client", "legacy wire opcodes", "atlas 00_SAMPLE_MATRIX §2", "Legacy client (20,918,752 B)"),
 ("BIN-S-1113", rf"{DL}\CODOL.NET\Game\CODOL_1.1.1.13\CODOL_Server\dedicated\bin\codol_dedrun.exe", "PRIMARY-BINARY", "1113 dedicated server", "legacy wire + netchan", "atlas 00_SAMPLE_MATRIX §5", "GCC 2.47 build"),
 ("BIN-S-OLD", rf"{DL}\CODOL-AlphaBuild_By_Antia(20261006)\CODOL-AlphaBuild By Antia\CODOL_Server\dedicated\bin\codol_dedrun.exe", "PRIMARY-BINARY", "OLD (CODOL-AlphaBuild)", "legacy wire + netchan", "atlas 00_SAMPLE_MATRIX §5", "Pairs with OLD source"),
 ("BIN-C-3333", rf"{DL}\codoMP_client_shipRetail.exe", "PRIMARY-BINARY", "CODOL 3.3.3.3 QA client", "ol-mod target", "atlas 00_SAMPLE_MATRIX §2.2", "NOT interchange with 2.6.9.7"),
 # ---- primary source ----
 ("SRC-OLD-WIRE", rf"{DL}\CODOL-AlphaBuild_By_Antia(20261006)\CODOL-AlphaBuild By Antia\CODOL_Server\dedicated\src\codol\net\codol_wire.h", "PRIMARY-SOURCE", "CoD4x fork (IW4OL)", "netchan constants, XOR, fragmentation", "2697_SA 04 §0", "CODOL_PROTOCOL=187, FRAGMENT_SIZE=1162, MAX_FRAGMENTS=128"),
 ("SRC-OLD-NETCHAN", rf"{DL}\CODOL-AlphaBuild_By_Antia(20261006)\CODOL-AlphaBuild By Antia\CODOL_Server\dedicated\src\codol\net\codol_netchan.c", "PRIMARY-SOURCE", "CoD4x fork (IW4OL)", "netchan process/handshake", "atlas 04 §4.1", "CODOL_NetchanProcess"),
 ("SRC-OLD-NETWORK", rf"{DL}\CODOL-AlphaBuild_By_Antia(20261006)\CODOL-AlphaBuild By Antia\CODOL_Server\dedicated\src\codol\net\codol_network.c", "PRIMARY-SOURCE", "CoD4x fork (IW4OL)", "CODOL_NetworkReceive, NAT/INIT/COOKIE/DATA", "atlas 06 §2", "24,170 B"),
 ("SRC-OLD-HANDSHAKE", rf"{DL}\CODOL-AlphaBuild_By_Antia(20261006)\CODOL-AlphaBuild By Antia\CODOL_Server\dedicated\src\codol\net\codol_handshake.c", "PRIMARY-SOURCE", "CoD4x fork (IW4OL)", "bdDTLS-ish handshake", "atlas 04 §5.1", "3,199 B; COOKIE_ECHO 189 B"),
 ("SRC-OLD-CRYPTO", rf"{DL}\CODOL-AlphaBuild_By_Antia(20261006)\CODOL-AlphaBuild By Antia\CODOL_Server\dedicated\src\codol\net\codol_crypto.c", "PRIMARY-SOURCE", "CoD4x fork (IW4OL)", "record layer encrypt/decrypt", "atlas 04 §5.2", "4,662 B"),
 ("SRC-OLD-ECDH", rf"{DL}\CODOL-AlphaBuild_By_Antia(20261006)\CODOL-AlphaBuild By Antia\CODOL_Server\dedicated\src\codol\net\codol_ecdh.c", "PRIMARY-SOURCE", "CoD4x fork (IW4OL)", "P-224 ECDH", "atlas 04 §5.1", "3,751 B"),
 ("SRC-OLD-CONNECT", rf"{DL}\CODOL-AlphaBuild_By_Antia(20261006)\CODOL-AlphaBuild By Antia\CODOL_Server\dedicated\src\codol\net\codol_connect.c", "PRIMARY-SOURCE", "CoD4x fork (IW4OL)", "connectResponse protocol string", "atlas 06 §4", "protocol conflict 187 vs 1"),
 # ---- current task / cross-validation synthesis (SELF, this task) ----
 ("SYN-ATLAS", rf"{ROOT}\14_SERVER_KNOWLEDGE_ATLAS_001", "SECONDARY-ANALYSIS", "2026-10-12", "all", "self", "Knowledge atlas; treat as synthesis, cite its own primary evidence"),
 ("SYN-2697SA", rf"{ROOT}\CODOL_2697_SERVER_STATIC_ANALYSIS_20261011", "SECONDARY-ANALYSIS", "2026-10-11", "server writers", "self", "Server static analysis"),
 ("EV-E06", rf"{ROOT}\E06_TVM0_STATIC_DECODE_001", "SECONDARY-ANALYSIS", "E-06", "recovery/binary decode", "self", "aplib decode + callgraph completeness"),
 ("EV-E08", rf"{ROOT}\E08_CONFIGSTRING_BODY_001", "SECONDARY-ANALYSIS", "E-08", "configstring body", "self", "Superseded in parts by E-09/E-14"),
 ("EV-E09", rf"{ROOT}\E09_CONFIGSTRING_BLOCKERS_001", "SECONDARY-ANALYSIS", "E-09", "configstring client consumer", "self", "count1=16b ruling; 0xA2660 PROVEN"),
 ("EV-E10", rf"{ROOT}\E10_CONFIGSTRING_DISPATCH_001", "SECONDARY-ANALYSIS", "E-10", "opcode dispatch", "self", "Superceded opcode-layer claims by E-11"),
 ("EV-E11", rf"{ROOT}\E11_GAMESTATE_SUBFRAME_001", "SECONDARY-ANALYSIS", "E-11", "gamestate subframe", "self", "Top=0x350170; subframe=0x354100"),
 ("EV-E12", rf"{ROOT}\E12_REALTIME_GAMESTATE_CONSUMER_001", "SECONDARY-ANALYSIS", "E-12", "realtime consumer", "self", "Ring buffer; demo attribution"),
 ("EV-E13", rf"{ROOT}\E13_RECV_RINGBUFFER_TRACE_001", "SECONDARY-ANALYSIS", "E-13", "recv trace", "self", "REFUTED recv->ringbuffer"),
 ("EV-E14", rf"{ROOT}\E14_CROSS_PROJECT_PROTOCOL_AND_NETWORK_001", "SECONDARY-ANALYSIS", "E-14", "opensource vs CODOL", "self", "A2=11b resolution; lineage"),
 ("EV-E15", rf"{ROOT}\E15_TLS_PLAINTEXT_TO_APPLICATION_001", "SECONDARY-ANALYSIS", "E-15", "TLS/plaintext", "self", "TLS=update module; REFUTED plaintext"),
 ("EV-E16", rf"{ROOT}\E16_SOCKET_EVENT_GAME_SESSION_ATTRIBUTION_001", "SECONDARY-ANALYSIS", "E-16", "socket event", "self", "0x1B0430=ICMP, 0x78772D=tool"),
 ("EV-E17", rf"{ROOT}\E17_RECV_ENTRYPOINT_ATTRIBUTION_001", "SECONDARY-ANALYSIS", "E-17", "recv attribution", "self", "Q-register 122"),
 ("EV-E18", rf"{ROOT}\E18_SOCKET_VTABLE_CONSTRUCTOR_AND_INDIRECT_DISPATCH_001", "SECONDARY-ANALYSIS", "E-18", "vtable/libcurl", "self", "Q-register 142; libcurl attribution"),
 ("EV-E19", rf"{ROOT}\E19_DEMONWARE_SESSION_OBJECT_DATAFLOW_001", "SECONDARY-ANALYSIS", "E-19", "demonware session", "self", "0x6ABBC0 frame reader PROVEN; game binding BLOCKED"),
 # ---- runtime / capture evidence ----
 ("RT-GOLDEN-LOBBY", rf"{DL}\使命召唤OL\GOLDEN-LOBBY-001", "RUNTIME-EVIDENCE", "2026-10-05", "lobby only", "atlas 09 RT-06", "Only first-hand in-lobby run"),
 ("RT-COMBAT-NET", rf"{ROOT}\_combat_next011", "RUNTIME-EVIDENCE (L2/platform)", "2026-10-10", "platform booking (service 21/5, 6/14)", "self", "44 frames, HMAC-verified; NOT in-game battle"),
 ("RT-DEV-BOOKING", rf"{ROOT}\DEV-BOOKING\runtime_net_001", "RUNTIME-EVIDENCE (L2/platform)", "runtime", "booking/net platform", "atlas 09", "Third-party lobby capture"),
 ("RT-DEV-BOOKING-CH", rf"{ROOT}\DEV-BOOKING\runtime_net_ch003", "RUNTIME-EVIDENCE (L2/platform)", "runtime", "booking/net platform", "atlas 09", "Third-party lobby capture"),
 ("RT-PLAINTEXT-FF", rf"{ROOT}\_PLAINTEXT_PROJECT", "PRIMARY-BINARY (assets)", "2026-10-02", "FF zone AES layer (not session)", "self", "AES-192-CTR L1 solved; L2 open"),
 # ---- open-source references ----
 ("OSS-COD4X", rf"{ROOT}\DEV-BOOKING\_lineage021\CoD4x_Server", "OPEN-SOURCE-REF", "CoD4x master ddd65fce", "netchan/msg/huffman/sv_*", "E14 01 §2", "AGPL server; external reference"),
 ("OSS-IW4X-A", rf"{ROOT}\DEV-BOOKING\_lineage021\iw4x-client", "OPEN-SOURCE-REF", "iw4x-client d1b175da", "client netchan/network", "E14 01 §2", "No dedicated server source"),
 ("OSS-OLMOD", rf"{ROOT}\_e1_regression\ol-mod-olfinal", "OPEN-SOURCE-REF", "ol-mod-olfinal 2a75bdd8", "own net_dtls_cod/net_chan_mp", "E14 01 §3", "Targets 3.3.3.3; not based on IW4x"),
]

def sha256(path, limit=256*1024*1024):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            b = f.read(1024*1024)
            if not b: break
            h.update(b)
    return h.hexdigest()

def dir_stat(path):
    n=0; tot=0
    for dp,_,fs in os.walk(path):
        for fn in fs:
            n+=1
            try: tot+=os.path.getsize(os.path.join(dp,fn))
            except OSError: pass
    return n, tot

def git_head(path):
    try:
        r = subprocess.run(["git","-C",path,"rev-parse","HEAD"],capture_output=True,text=True,timeout=20)
        if r.returncode==0: return r.stdout.strip()
    except Exception: pass
    return ""

rows=[]
for mid, path, cls, ver, mods, cite, notes in CATALOG:
    exists = os.path.isfile(path) or os.path.isdir(path)
    if not exists:
        rows.append(dict(Material_ID=mid,Path=path,File_Type="MISSING",Size_Bytes="",SHA256="",Modified_UTC="",
                         Provenance_Class=cls,Source_Version=ver,Protocol_Modules=mods,Citation_Location=cite,
                         Notes=notes+" | PATH NOT FOUND AT XVAL-01 TIME"))
        continue
    if os.path.isdir(path):
        n,tot = dir_stat(path); head = git_head(path)
        rows.append(dict(Material_ID=mid,Path=path,File_Type=f"dir ({n} files)",Size_Bytes=tot,
                         SHA256=(("git:"+head) if head else "N/A (directory)"),Modified_UTC="",
                         Provenance_Class=cls,Source_Version=ver,Protocol_Modules=mods,Citation_Location=cite,Notes=notes))
    else:
        sz=os.path.getsize(path)
        dig= sha256(path) if sz<=256*1024*1024 else "skipped(size)"
        mt=datetime.datetime.utcfromtimestamp(os.path.getmtime(path)).strftime("%Y-%m-%dT%H:%M:%SZ")
        rows.append(dict(Material_ID=mid,Path=path,File_Type=os.path.splitext(path)[1] or "file",Size_Bytes=sz,
                         SHA256=dig,Modified_UTC=mt,Provenance_Class=cls,Source_Version=ver,
                         Protocol_Modules=mods,Citation_Location=cite,Notes=notes))

OUT = rf"{ROOT}\XVAL-01_LOCAL_NETWORK_EVIDENCE_CROSS_VALIDATION\XVAL01_SOURCE_PROVENANCE.csv"
cols=["Material_ID","Path","File_Type","Size_Bytes","SHA256","Modified_UTC","Provenance_Class","Source_Version","Protocol_Modules","Citation_Location","Notes"]
with open(OUT,"w",newline="",encoding="utf-8-sig") as f:
    w=csv.DictWriter(f,fieldnames=cols); w.writeheader()
    for r in rows: w.writerow(r)
print("wrote",OUT,"rows",len(rows))
for r in rows:
    print(f"  {r['Material_ID']:<18} {r['Provenance_Class']:<34} {str(r['SHA256'])[:16]:<16} {r['File_Type']}")
