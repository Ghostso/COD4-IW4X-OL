import datetime
import hashlib
import os
import re
import struct
from collections import defaultdict, Counter

import pefile


ROOT = r"D:\BaiduNetdiskDownload\使命召唤OL"
OUT = os.path.join(
    ROOT, "CODOLServer", "_static_reports",
    "02_RUNTIME_DLL_EXE_DEPENDENCY_GRAPH.txt")

PRIMARY_ROOTS = [
    os.path.join(ROOT, "COD OL"),
    os.path.join(ROOT, "run_codol_001", "sandbox_ifs1_20260923"),
]
TOOL_ROOT = os.path.join(ROOT, "\u5de5\u5177")

INCLUDE_TOOL_BASENAMES = {
    "codoMP_client_shipRetail.exe", "codoMP_client_shipRetailBase.dll",
    "iips.dll", "IIPSHost.dll", "IIPSHostApp.exe", "IFS.dll", "IFS2.dll",
    "TCLSClient.dll", "tpsvcBase.dll", "TPSvc.exe", "Client.exe",
    "ClientBase.dll", "TenProxy.dll", "TNProxy.dll", "TenioDL.dll",
    "TenioDL.exe", "TenRpcs.dll", "GameRpcs.dll",
    "GameDataPlatformServer.dll", "GDPLoader.dll", "GDPImpl.dll",
    "GDPCODOTrail.dll", "ace-ats32.dll", "ACE-DRV32.dll",
    "tersafe.dll", "TerSafe.dll", "BugTrace.dll", "PolicyProbe.dll",
    "TCJ.dll", "TenSLX.dll", "tvsd.dll", "VSDDrvDll.dll",
    "TP3Helper.exe", "TGPMiniDown.1367.2.1.5.8204.cod.exe",
    "TenSp.dll", "TenBase.dll", "TenFact.dll", "ScriptManager.dll",
    "TenTPF.dll", "TpfAdapter.dll", "VFS.dll", "VVer.dll", "June.dll",
    "MemoryAlloctor.dll", "TPApp.dll", "TPDownload.dll",
    "TASLoginBase.dll", "TASLogin.exe", "TasBridge.dll", "SecureCheck.dll",
    "TQMCenter.exe", "TGOC.exe", "TSMCore.dll", "TSMPlus.dll",
    "TGuard.exe", "TGuardBase.dll", "TGuardSvc.exe", "BugReport.dll",
    "BugTrack.dll", "SecureCheck.dll", "TASJIT.dll", "TenHotFix.dll",
    "TPHelperBase.dll", "TPHelper.exe", "TPWeb.exe", "TPFCustom.dll",
    "iigw_client_api.dll", "ProtocalHandler.dll", "QQPCDetector.dll",
    "QQPCfix.dll", "QmTCLSPatch.dll", "QmTCLSPlugin.dll", "QMCommon.dll",
    "QMNetworkMgr.dll", "QMIpc.dll", "TCLS.dll", "DirInfo3_3.dll",
    "Dir.dll", "Install.dll", "Update.exe", "Assistant.exe",
    "BackgroundDownloader.exe", "TenioDL_core.dll", "TenioTPF.dll",
    "xRender.dll", "Packet.dll", "wpcap.dll",
}

EXCLUDE_PATH_PARTS = {
    "directx", "locales", "microsoft.vc90.crt", "apps", "docs",
    "windbg_x86", "players", "logs", "timeLog".lower(), "tenproxylog",
    "vodcache", "snapshot", "music", "patchs",
}

NETWORK_API_RE = re.compile(
    r"^(?:WSA|WS2|socket$|connect$|bind$|listen$|accept$|send$|recv$|"
    r"getaddrinfo$|gethostby|inet_|select$|closesocket$|ioctlsocket$|"
    r"Internet|WinHttp|Http|Https|URL|Dns|DnsQuery|GetAddrInfo|"
    r"WSAAsync|WSAGetLastError|WSASetLastError|WSACleanup|WSAStartup)",
    re.I)

PROCESS_API_RE = re.compile(
    r"^(?:CreateProcess|ShellExecute|WinExec|LoadLibrary|GetProcAddress|"
    r"VirtualAlloc|VirtualProtect|WriteProcessMemory|ReadProcessMemory|"
    r"CreateRemoteThread|OpenProcess|Nt|Zw|CreateService|OpenSCManager|"
    r"RegOpen|RegSet|RegQuery|RegCreate|CreateMutex|CreateEvent|"
    r"CreateFileMapping|MapViewOfFile|CreateNamedPipe|DeviceIoControl)",
    re.I)

CRYPTO_API_RE = re.compile(
    r"(?:Crypt|Cipher|Aes|Rijndael|RSA|RC4|MD5|SHA|HMAC|Base64|X509|"
    r"SSL|TLS|Cert|RtlGenRandom|BCrypt|CAPI)",
    re.I)

URL_RE = re.compile(
    r"(?i)(?:https?|udp|tcp|ws|wss|ftp|file)://[^\s\"'<>]{3,240}")
DOMAIN_RE = re.compile(
    r"(?i)\b(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+"
    r"(?:com|cn|net|org|qq\.com|tencent|tencent\.com|iips\.qq\.com)"
    r"(?::\d{1,5})?\b")
IPV4_RE = re.compile(
    r"\b(?:25[0-5]|2[0-4]\d|1?\d?\d)"
    r"(?:\.(?:25[0-5]|2[0-4]\d|1?\d?\d)){3}(?::\d{1,5})?\b")
PORTISH_RE = re.compile(
    r"(?i)(?:port|listen|bind|server|host|addr|address|qos|proxy|"
    r"http|https|udp|tcp)[^\r\n\x00]{0,36}?(?::|is\s+|=|\s)(\d{2,5})\b|"
    r"\b\d{1,3}(?:\.\d{1,3}){3}:(\d{2,5})\b")

SUSPICIOUS_RE = re.compile(
    r"(?i)(?:anti.?cheat|ace|sguard|driver|kernel|inject|hook|cheat|"
    r"debugger|IsDebuggerPresent|NtQueryInformationProcess|"
    r"process.?scan|module.?scan|integrity|tamper|signature|"
    r"service|registry|\\\\\\.\\|DeviceIoControl|driver|\.sys\b|"
    r"CreateProcess|LoadLibrary|GetProcAddress|VirtualProtect|"
    r"password|token|license|auth|login|replay|packet|encrypt|decrypt)")

KNOWN_MODULE_RE = re.compile(
    r"(?i)(?<![a-z0-9_])[a-z0-9_.-]{2,80}\.(?:dll|exe|sys)")

CERT_URL_RE = re.compile(
    r"(?i)(?:digicert|symcb|symcd|symauth|verisign|thawte|globalsign|"
    r"usertrust|comodo|entrust|godaddy|sectigo|letsencrypt|quovadis|"
    r"microsoft\.com/pki|windows\.net|w3\.org|curl\.haxx\.se|"
    r"openssl\.org|ibsensoftware\.com|winimage\.com)")

NOISE_URL_RE = re.compile(r"(?i)^(?:file://|http://%s|https://%s)")

SCHEME_RE = re.compile(
    r"(?i)\b(?:https?|udp|tcp|ws|wss|ftp)://[^\s\"'<>]{3,240}")

KEY_API_ALLOW = re.compile(
    r"^(?:connect|send|recv|sendto|recvfrom|bind|listen|accept|socket|"
    r"closesocket|select|WSARecv|WSASend|GetAddrInfo|getaddrinfo|"
    r"gethostbyname|gethostbyaddr|Internet|WinHttp|Http|URLDownload|"
    r"Crypt|BCrypt|Cert|SSL|TLS|LoadLibrary|GetProcAddress|CreateProcess|"
    r"OpenProcess|CreateRemoteThread|VirtualAlloc|VirtualProtect|"
    r"WriteProcessMemory|ReadProcessMemory|DeviceIoControl|CreateFile|"
    r"CreateMutex|CreateEvent|CreateFileMapping|MapViewOfFile|"
    r"RegOpen|RegSet|RegQuery|RegCreate|OpenSCManager|CreateService|"
    r"GetTickCount|QueryPerformanceCounter|CreateThread|WaitForSingleObject)",
    re.I)

TEXT_SUFFIXES = (".dll", ".exe", ".sys")


def norm_text(value):
    return re.sub(r"[^a-z0-9]", "", value.lower())


def unicode_escape(text):
    return "".join(ch if ord(ch) < 128 else "\\u%04x" % ord(ch) for ch in text)


CN = {
    "title": "\u8fd0\u884c\u94fe DLL/EXE \u9759\u6001\u4f9d\u8d56\u56fe\u62a5\u544a",
    "generated": "\u751f\u6210\u65f6\u95f4",
    "scope": "\u626b\u63cf\u8303\u56f4",
    "method": "\u65b9\u6cd5\u4e0e\u8fb9\u754c",
    "coverage": "\u8986\u76d6\u4e0e\u53bb\u91cd",
    "summary": "\u6784\u4ef6\u6c47\u603b",
    "components": "\u9010\u7ec4\u4ef6\u8bb0\u5f55",
    "path": "\u6743\u5a01\u8def\u5f84",
    "copies": "\u5176\u4ed6\u526f\u672c",
    "basic": "PE \u57fa\u672c\u4fe1\u606f",
    "sd": "\u5b57\u8282/SHA-256",
    "version": "\u7248\u672c\u8d44\u6e90",
    "imports": "\u5bfc\u5165\u8fb9",
    "exports": "\u5bfc\u51fa\u8fb9",
    "deps": "\u4f9d\u8d56\u8fb9",
    "strings": "\u53ef\u7591/\u7f51\u7edc/\u52a0\u5bc6\u5b57\u7b26\u4e32",
    "boundary": "\u8c03\u7528\u8fb9\u754c",
    "conclusion": "\u7ed3\u8bba",
}


def should_include(path):
    low = path.lower()
    parts = set(p.lower() for p in low.split(os.sep))
    if path.lower().endswith(".bak") or low.endswith(".bh"):
        return False
    name = os.path.basename(path)
    if ROOT.lower() in low:
        rel = os.path.relpath(path, ROOT).lower()
    else:
        rel = low
    if "\\appdata\\" in rel:
        return False
    if "\\tqm\\" in rel:
        return True
    if "\\tenio" in rel or "\\tenprotect" in rel or "\\tguard" in rel:
        return True
    if "\\iips\\" in rel:
        return True
    if "\\tcls\\" in rel:
        return True
    if any(part in parts for part in EXCLUDE_PATH_PARTS):
        return False
    if "\\cross\\apps\\" in rel or "\\cross\\locales\\" in rel:
        return False
    if os.path.dirname(path).lower() == os.path.join(ROOT, "COD OL").lower():
        return True
    if os.path.dirname(path).lower() == os.path.join(
            ROOT, "run_codol_001", "sandbox_ifs1_20260923").lower():
        return True
    if name.lower() in INCLUDE_TOOL_BASENAMES:
        return True
    return False


def iter_primary_paths():
    for base in PRIMARY_ROOTS:
        for dp, dns, fns in os.walk(base):
            dns[:] = [d for d in dns if not d.lower().startswith(".claude")]
            for fn in fns:
                if not fn.lower().endswith((".dll", ".exe")):
                    continue
                p = os.path.join(dp, fn)
                if should_include(p):
                    yield p


def iter_tool_paths():
    if not os.path.isdir(TOOL_ROOT):
        return
    for dp, dns, fns in os.walk(TOOL_ROOT):
        dns[:] = [d for d in dns if d.lower() != "windbg_x86"]
        for fn in fns:
            if fn.lower() in INCLUDE_TOOL_BASENAMES:
                yield os.path.join(dp, fn)


def file_sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            chunk = f.read(1024 * 1024)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest().upper()


def string_hits(data):
    hits = defaultdict(set)
    ascii_strings = [
        m.group(0).decode("ascii", "ignore")
        for m in re.finditer(rb"[\x20-\x7e]{4,240}", data)
    ]
    utf16_strings = [
        bytes(m.group(0)).decode("utf-16le", "ignore")
        for m in re.finditer(rb"(?:[\x20-\x7e]\x00){4,240}", data)
    ]
    for s in ascii_strings + utf16_strings:
        s = s.replace("\x00", "").strip()
        if not s or len(s) > 260:
            continue
        is_cert_noise = bool(CERT_URL_RE.search(s))
        has_scheme = bool(SCHEME_RE.search(s))
        if has_scheme:
            bucket = "cert_url" if is_cert_noise else "url"
            if not NOISE_URL_RE.match(s.strip()):
                hits[bucket].add(s[:240])
        if not is_cert_noise:
            dm = DOMAIN_RE.search(s)
            if dm:
                hits["domain"].add(dm.group(0)[:240])
            ip = IPV4_RE.search(s)
            if ip:
                hits["ip"].add(ip.group(0)[:240])
            pm = PORTISH_RE.search(s)
            if pm:
                hits["port"].add(s[:240])
        if CRYPTO_API_RE.search(s):
            hits["crypto"].add(s[:240])
        if SUSPICIOUS_RE.search(s):
            hits["suspicious"].add(s[:240])
        for mm in KNOWN_MODULE_RE.finditer(s):
            token = mm.group(0)
            if token.lower().endswith(TEXT_SUFFIXES):
                hits["module"].add(token[:160])
    return hits


def get_file_info(pe):
    result = {}
    try:
        for file_info_list in getattr(pe, "FileInfo", []):
            for file_info in file_info_list:
                if file_info.Key == b"StringFileInfo":
                    for st in file_info.StringTable:
                        for k, v in st.entries.items():
                            key = k.decode("utf-8", "replace")
                            val = v.decode("utf-8", "replace")
                            result[key] = val
                elif file_info.Key == b"VarFileInfo":
                    for var in file_info.Var:
                        if var.Key == b"Translation":
                            result["Translation"] = var.entry
    except Exception as exc:
        result["ParseError"] = repr(exc)
    wanted = [
        "CompanyName", "FileDescription", "FileVersion", "InternalName",
        "LegalCopyright", "OriginalFilename", "ProductName",
        "ProductVersion", "Translation",
    ]
    return {k: result[k] for k in wanted if k in result}


def get_imports(pe):
    rows = []
    key = []
    for entry in getattr(pe, "DIRECTORY_ENTRY_IMPORT", []):
        dll = entry.dll.decode("utf-8", "replace")
        names = []
        for imp in entry.imports:
            if imp.name:
                n = imp.name.decode("utf-8", "replace")
            else:
                n = "ordinal_%d" % imp.ordinal
            names.append(n)
            if KEY_API_ALLOW.match(n):
                key.append((dll, n))
        rows.append((dll, names))
    return rows, key


def get_exports(pe):
    rows = []
    exp = getattr(pe, "DIRECTORY_ENTRY_EXPORT", None)
    if not exp:
        return rows
    for sym in exp.symbols:
        name = sym.name.decode("utf-8", "replace") if sym.name else None
        fwd = (
            sym.forwarder.decode("utf-8", "replace")
            if getattr(sym, "forwarder", None) else None)
        rows.append((sym.ordinal, name, fwd, sym.address))
    return rows


def ts_text(ts):
    try:
        return datetime.datetime.utcfromtimestamp(ts).strftime(
            "%Y-%m-%d %H:%M:%S UTC")
    except Exception:
        return "invalid"


def is_64(machine):
    return machine in (0x8664, 0xAA64)


def format_list(items, limit, joiner=", "):
    items = list(items)
    if len(items) <= limit:
        return joiner.join(items) if items else "(none)"
    return joiner.join(items[:limit]) + (
        " ... <%d more>" % (len(items) - limit))


def local_dynamic_modules(hits, basenames):
    out = []
    for s in hits.get("module", []):
        base = os.path.basename(s.replace("/", "\\"))
        if base.lower() in basenames:
            out.append(base)
    return sorted(set(out), key=str.lower)


def main():
    primary = sorted(set(os.path.abspath(p) for p in iter_primary_paths()))
    tools = sorted(set(os.path.abspath(p) for p in iter_tool_paths()))
    all_paths = primary + tools

    groups = {}
    for p in all_paths:
        try:
            sha = file_sha256(p)
        except Exception as exc:
            sha = "IO_ERROR:" + repr(exc)
        groups.setdefault(sha, []).append(p)

    basenames = set(os.path.basename(p).lower() for p in all_paths)
    components = []
    skipped = []
    for sha, paths in groups.items():
        paths = sorted(paths, key=lambda p: (
            "\\run_codol_001\\sandbox_ifs1_20260923\\" not in p,
            "\\COD OL\\" not in p,
            len(p), p.lower()))
        canonical = paths[0]
        try:
            data = open(canonical, "rb").read()
            pe = pefile.PE(data=data, fast_load=True)
            pe.parse_data_directories(directories=[
                pefile.DIRECTORY_ENTRY["IMAGE_DIRECTORY_ENTRY_IMPORT"],
                pefile.DIRECTORY_ENTRY["IMAGE_DIRECTORY_ENTRY_EXPORT"],
                pefile.DIRECTORY_ENTRY["IMAGE_DIRECTORY_ENTRY_RESOURCE"],
                pefile.DIRECTORY_ENTRY["IMAGE_DIRECTORY_ENTRY_SECURITY"],
            ])
            imports, key_imports = get_imports(pe)
            exports = get_exports(pe)
            version = get_file_info(pe)
            hits = string_hits(data)
            sec_dir = pe.OPTIONAL_HEADER.DATA_DIRECTORY[4]
            components.append({
                "sha": sha,
                "paths": paths,
                "canonical": canonical,
                "size": len(data),
                "machine": pe.FILE_HEADER.Machine,
                "magic": pe.OPTIONAL_HEADER.Magic,
                "subsystem": pe.OPTIONAL_HEADER.Subsystem,
                "dllchars": pe.OPTIONAL_HEADER.DllCharacteristics,
                "timestamp": ts_text(pe.FILE_HEADER.TimeDateStamp),
                "imagebase": pe.OPTIONAL_HEADER.ImageBase,
                "entry": pe.OPTIONAL_HEADER.AddressOfEntryPoint,
                "sections": len(pe.sections),
                "signed": bool(sec_dir.VirtualAddress and sec_dir.Size),
                "signature_size": sec_dir.Size,
                "imports": imports,
                "key_imports": key_imports,
                "exports": exports,
                "version": version,
                "hits": hits,
            })
        except Exception as exc:
            skipped.append((canonical, repr(exc)))

    by_base = defaultdict(list)
    for c in components:
        by_base[os.path.basename(c["canonical"]).lower()].append(c)
    import_edges = defaultdict(set)
    for c in components:
        source_base = os.path.basename(c["canonical"]).lower()
        import_edges[source_base].add(source_base)
        for dll, _ in c["imports"]:
            d = dll.lower()
            if d in by_base:
                import_edges[source_base].update(
                    os.path.basename(x["canonical"]).lower() for x in by_base[d])
    callers = defaultdict(set)
    for source, targets in import_edges.items():
        for target in targets:
            callers[target].add(source)

    lines = []
    add = lines.append
    add("=" * 112)
    add(CN["title"])
    add("=" * 112)
    add("%s: %s" % (
        CN["generated"], datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    add("Report path: %s" % OUT)
    add("")
    add("[%s]" % CN["scope"])
    add("Primary static roots:")
    for p in PRIMARY_ROOTS:
        add("  - %s" % p)
    add("Tool comparison root: %s" % TOOL_ROOT)
    add("Package roots:")
    add("  - %s" % os.path.join(ROOT, "COD OL", "IIPS"))
    add("  - %s" % os.path.join(ROOT, "COD OL", "TCLS"))
    add("  - %s" % os.path.join(ROOT, "COD OL", "TCLS", "TenProtect"))
    add("  - %s" % os.path.join(ROOT, "COD OL", "TGuard"))
    add("  - %s" % os.path.join(ROOT, "COD OL", "tqm"))
    add("  - %s" % os.path.join(
        ROOT, "run_codol_001", "sandbox_ifs1_20260923", "IIPS"))
    add("  - %s" % os.path.join(
        ROOT, "run_codol_001", "sandbox_ifs1_20260923", "TGuard"))
    add("Excluded as unrelated runtime surface:")
    add("  - DirectX redistributables, browser apps/localizations, "
        "developer debugger toolchains, logs, data-only packages")
    add("")
    add("[%s]" % CN["method"])
    add("- Static PE parsing only. No process launch, service control, "
        "network/DNS/firewall/route/netsh mutation, or source modification.")
    add("- SHA-256 is the component identity key. Byte-identical copies "
        "are collapsed and every observed path is listed.")
    add("- Imports are the declared import table. Module strings only "
        "provide dynamic-load candidates; they are not proof of execution.")
    add("- Exports define callable replacement boundaries. String hits are "
        "evidence candidates and may include false positives.")
    add("- Port extraction requires URL/IP/port-like context; it is not a "
        "protocol schema and does not prove a live listener.")
    add("")
    add("[%s]" % CN["coverage"])
    add("Primary candidate paths: %d" % len(primary))
    add("Tool comparison paths: %d" % len(tools))
    add("Unique SHA-256 components: %d" % len(components))
    add("Unparsed PE candidates: %d" % len(skipped))
    for p, err in skipped:
        add("  - %s | %s" % (p, err))
    add("")
    add("[%s]" % CN["summary"])
    add("%-46s %-8s %-8s %-7s %-5s %-5s %s" % (
        "component", "bits", "kind", "size", "imp", "exp", "sha256"))
    for c in sorted(components, key=lambda x: os.path.basename(
            x["canonical"]).lower()):
        add("%-46s %-8d %-8s %-7d %-5d %-5d %s" % (
            os.path.basename(c["canonical"]),
            64 if is_64(c["machine"]) else 32,
            "DLL" if os.path.splitext(c["canonical"])[1].lower() == ".dll"
            else "EXE",
            c["size"], len(c["imports"]), len(c["exports"]), c["sha"]))
    add("")
    add("[%s]" % CN["components"])

    for idx, c in enumerate(sorted(
            components, key=lambda x: os.path.basename(
                x["canonical"]).lower()), 1):
        base = os.path.basename(c["canonical"])
        add("")
        add("-" * 112)
        add("COMPONENT %03d: %s" % (idx, base))
        add("-" * 112)
        add("[%s]" % CN["path"])
        add("  %s" % c["canonical"])
        add("[%s]" % CN["copies"])
        for p in c["paths"]:
            if p != c["canonical"]:
                add("  %s" % p)
        add("[%s]" % CN["basic"])
        add("  machine=0x%04X | bits=%d | magic=0x%04X | subsystem=%d | "
            "sections=%d" % (
                c["machine"], 64 if is_64(c["machine"]) else 32,
                c["magic"], c["subsystem"], c["sections"]))
        add("  timestamp=%s | imagebase=0x%X | entry_rva=0x%X | "
            "dllchars=0x%04X | authenticode=%s size=%d" % (
                c["timestamp"], c["imagebase"], c["entry"],
                c["dllchars"], c["signed"], c["signature_size"]))
        add("[%s]" % CN["sd"])
        add("  bytes=%d | SHA-256=%s" % (c["size"], c["sha"]))
        add("[%s]" % CN["version"])
        if c["version"]:
            for k in sorted(c["version"]):
                add("  %s=%s" % (k, c["version"][k]))
        else:
            add("  (none)")
        add("[%s]" % CN["imports"])
        if c["imports"]:
            for dll, names in c["imports"]:
                add("  %-28s APIs=%d | %s" % (
                    dll, len(names), format_list(names, 12)))
        else:
            add("  (none)")
        if c["key_imports"]:
            add("  boundary APIs:")
            for dll, name in c["key_imports"][:80]:
                add("    %s!%s" % (dll, name))
            if len(c["key_imports"]) > 80:
                add("    ... <%d more>" % (len(c["key_imports"]) - 80))
        add("[%s]" % CN["exports"])
        if c["exports"]:
            for ordinal, name, forwarder, address in c["exports"][:180]:
                label = name if name else "(ordinal)"
                extra = " -> %s" % forwarder if forwarder else ""
                add("  %4d 0x%08X %s%s" % (
                    ordinal, address, label, extra))
            if len(c["exports"]) > 180:
                add("  ... <%d more>" % (len(c["exports"]) - 180))
        else:
            add("  (none)")
        deps = sorted(set(dll for dll, _ in c["imports"]), key=str.lower)
        dynamic = local_dynamic_modules(
            c["hits"], set(x.lower() for x in basenames))
        add("[%s]" % CN["deps"])
        add("  declared: %s" % format_list(deps, 40))
        add("  local dynamic candidates: %s" % format_list(dynamic, 40))
        source_base = base.lower()
        incoming = sorted(callers.get(source_base, set()))
        add("  incoming local import callers: %s" % format_list(incoming, 40))
        add("[%s]" % CN["strings"])
        for kind in (
                "url", "domain", "ip", "port", "crypto", "module",
                "suspicious", "cert_url"):
            if kind == "cert_url":
                vals = sorted(c["hits"].get(kind, []), key=lambda s: (
                    len(s), s.lower()))
                add("  cert_url (authenticode CA/CRL noise, %d distinct):"
                    % len(vals))
                continue
            vals = sorted(c["hits"].get(kind, []), key=lambda s: (
                len(s), s.lower()))
            if vals:
                add("  %s (%d):" % (kind, len(vals)))
                for s in vals[:35]:
                    add("    %s" % s)
                if len(vals) > 35:
                    add("    ... <%d more>" % (len(vals) - 35))
        add("[%s]" % CN["boundary"])
        add("  replacement surface: exports=%d, import modules=%d, "
            "incoming local callers=%d" % (
                len(c["exports"]), len(c["imports"]), len(incoming)))
        add("[%s]" % CN["conclusion"])
        add("  Static role evidence is contained in the declared import "
            "edges, exported symbols, dynamic module strings, and network/"
            "crypto/process strings above. Treat unresolved strings as "
            "candidates until independently verified.")

    add("")
    add("=" * 112)
    add("END OF REPORT")
    add("=" * 112)

    with open(OUT, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines) + "\n")
    print("WROTE", OUT)
    print("components", len(components), "skipped", len(skipped),
          "primary", len(primary), "tool", len(tools))


if __name__ == "__main__":
    main()
