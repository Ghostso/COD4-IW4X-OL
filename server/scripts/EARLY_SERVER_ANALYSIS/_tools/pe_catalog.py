# -*- coding: utf-8 -*-
"""EARLY_SERVER_00/01 PE catalog.

For every PE file under a root, emit architecture, ImageBase, entry point,
sections, imports (module + key functions), exports, version resources and
delay imports.  Read-only.

    python pe_catalog.py <root> <out_csv> [--json <out.json>] [--only exe,dll]
"""
import argparse, csv, hashlib, json, os, sys, time
import pefile

KEY_IMPORTS = {
    # networking / protocol
    "ws2_32.dll": ["socket","bind","listen","accept","recv","recvfrom","send","sendto",
                   "WSAStartup","select","getaddrinfo","WSARecv","WSASend","closesocket",
                   "connect","inet_addr","htons","ntohs"],
    "wsock32.dll": ["socket","bind","listen","accept","recv","send","WSAStartup","connect"],
    "wininet.dll": ["InternetOpenA","InternetConnectA","HttpOpenRequestA","HttpSendRequestA","InternetReadFile"],
    "winhttp.dll": ["WinHttpOpen","WinHttpConnect","WinHttpOpenRequest","WinHttpSendRequest"],
    # crypto
    "crypt32.dll": ["CryptEncrypt","CryptDecrypt","CryptGenKey","CryptImportKey","CertOpenStore"],
    "advapi32.dll": ["CryptAcquireContextA","CryptEncrypt","CryptGenRandom","RegOpenKeyExA"],
    "bcrypt.dll": ["BCryptEncrypt","BCryptDecrypt","BCryptGenRandom"],
    "ssleay32.dll": ["SSL_CTX_new","SSL_new","SSL_read","SSL_write"],
    "libeay32.dll": ["RSA_public_encrypt","AES_set_encrypt_key","EVP_EncryptInit"],
    # db / storage
    "sqlite3.dll": ["sqlite3_open","sqlite3_exec","sqlite3_prepare_v2","sqlite3_step"],
    "libmysql.dll": ["mysql_init","mysql_real_connect","mysql_query"],
    "odbc32.dll": ["SQLConnect","SQLDriverConnect","SQLExecDirect"],
    # threads / sync
    "kernel32.dll": ["CreateThread","CreateProcessA","LoadLibraryA","GetProcAddress","CreateFileA",
                     "CreateMutexA","WaitForSingleObject","CreateEventA","VirtualAlloc"],
    # crt
    "msvcr100.dll": [], "msvcr110.dll": [], "msvcr120.dll": [], "msvcrt.dll": [],
    "vcruntime140.dll": [], "msvcp140.dll": [],
}

def pe_info(path):
    info = {"pe": True, "error": ""}
    try:
        pe = pefile.PE(path, fast_load=True)
        pe.parse_data_directories(directories=[
            pefile.DIRECTORY_ENTRY["IMAGE_DIRECTORY_ENTRY_IMPORT"],
            pefile.DIRECTORY_ENTRY["IMAGE_DIRECTORY_ENTRY_EXPORT"],
            pefile.DIRECTORY_ENTRY["IMAGE_DIRECTORY_ENTRY_DELAY_IMPORT"],
            pefile.DIRECTORY_ENTRY["IMAGE_DIRECTORY_ENTRY_RESOURCE"],
        ])
    except Exception as e:
        return {"pe": False, "error": f"{type(e).__name__}: {e}"}

    mach = pe.FILE_HEADER.Machine
    arch = {0x14c: "x86", 0x8664: "x64", 0x1c0: "ARM", 0xaa64: "ARM64"}.get(mach, hex(mach))
    info.update({
        "arch": arch,
        "machine": hex(mach),
        "subsystem": pe.OPTIONAL_HEADER.Subsystem,
        "imagebase": hex(pe.OPTIONAL_HEADER.ImageBase),
        "entrypoint_rva": hex(pe.OPTIONAL_HEADER.AddressOfEntryPoint),
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(pe.FILE_HEADER.TimeDateStamp)),
        "is_dll": bool(pe.FILE_HEADER.Characteristics & 0x2000),
        "is_driver": pe.OPTIONAL_HEADER.Subsystem == 1,
        "linker": f"{pe.OPTIONAL_HEADER.MajorLinkerVersion}.{pe.OPTIONAL_HEADER.MinorLinkerVersion}",
    })

    sections = []
    for s in pe.sections:
        nm = s.Name.rstrip(b"\x00").decode("latin-1", "replace")
        sections.append({"name": nm, "va": hex(s.VirtualAddress),
                         "vsize": s.Misc_VirtualSize, "rawsize": s.SizeOfRawData,
                         "flags": hex(s.Characteristics)})
    info["sections"] = sections

    imps = {}
    for entry in getattr(pe, "DIRECTORY_ENTRY_IMPORT", []) or []:
        dll = (entry.dll or b"").decode("latin-1", "replace")
        fns = []
        for imp in entry.imports:
            nm = imp.name.decode("latin-1", "replace") if imp.name else f"ord{imp.ordinal}"
            fns.append(nm)
        imps[dll] = fns
    info["imports"] = imps

    # key imports only
    key = {}
    for dll, fns in imps.items():
        base = dll.lower()
        interesting = KEY_IMPORTS.get(base)
        if interesting is None:
            interesting = []
        if interesting:
            hit = [f for f in fns if f in interesting]
            if hit:
                key[dll] = hit
        elif base in KEY_IMPORTS:  # CRT - presence only
            key[dll] = ["<present>"]
    info["key_imports"] = key

    exports = []
    exp = getattr(pe, "DIRECTORY_ENTRY_EXPORT", None)
    if exp:
        for e in exp.symbols:
            nm = e.name.decode("latin-1", "replace") if e.name else f"ord{e.ordinal}"
            exports.append(nm)
    info["exports"] = exports[:400]
    info["export_count"] = len(exports)

    # version resource
    ver = {}
    try:
        for fi in getattr(pe, "FileInfo", []) or []:
            if fi.Key == b"StringFileInfo":
                for st in fi.StringTable:
                    for k, v in st.entries.items():
                        ver[k.decode("latin-1", "replace")] = v.decode("latin-1", "replace")
            elif fi.Key == b"VarFileInfo":
                for var in fi.Var:
                    ver["Translation"] = str(var.entry)
    except Exception:
        pass
    info["version"] = ver
    return info

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("root"); ap.add_argument("out_csv")
    ap.add_argument("--json"); ap.add_argument("--only", default="exe,dll,sys,ocx,drv")
    args = ap.parse_args()
    root = os.path.abspath(args.root)
    only = set(x.strip().lower() for x in args.only.split(","))

    targets = []
    for dp, dn, fn in os.walk(root):
        for n in fn:
            ext = os.path.splitext(n)[1].lower().lstrip(".")
            if ext in only:
                targets.append(os.path.join(dp, n))
    targets.sort()

    rows = []
    detail = {}
    for full in targets:
        rel = os.path.relpath(full, root)
        try: size = os.path.getsize(full)
        except OSError: size = -1
        info = pe_info(full)
        d = {"relpath": rel, "size": size, **info}
        detail[rel] = d
        rows.append(d)
        print(f"  {rel}: {info.get('arch','?')} imp={len(info.get('imports',{}))} exp={info.get('export_count','-')} {info.get('error','')}")

    with open(args.out_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["relpath","size","arch","subsystem","imagebase","entrypoint_rva","timestamp",
                    "is_dll","is_driver","linker","sections","import_modules","import_count",
                    "export_count","version_product","version_file","version_company","error"])
        for r in rows:
            v = r.get("version", {})
            imps = r.get("imports", {})
            w.writerow([r["relpath"], r["size"], r.get("arch",""), r.get("subsystem",""),
                        r.get("imagebase",""), r.get("entrypoint_rva",""), r.get("timestamp",""),
                        r.get("is_dll",""), r.get("is_driver",""), r.get("linker",""),
                        ";".join(s["name"] for s in r.get("sections",[])),
                        ";".join(sorted(imps.keys())), sum(len(v2) for v2 in imps.values()),
                        r.get("export_count",""),
                        v.get("ProductName",""), v.get("FileDescription","") or v.get("InternalName",""),
                        v.get("CompanyName",""), r.get("error","")])
    if args.json:
        with open(args.json, "w", encoding="utf-8") as f:
            json.dump(detail, f, indent=1, ensure_ascii=False)
    print(f"PE files: {len(rows)}")

if __name__ == "__main__":
    main()
