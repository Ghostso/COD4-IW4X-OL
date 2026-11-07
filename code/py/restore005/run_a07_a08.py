"""Agent 07 (Windows loadability) + Agent 08 (independent PE validation).

Emits the machine-readable evidence set for the final report.
"""
import hashlib
import json
import os
import struct
import subprocess

ORIG = r"COD OL\IIPS\iips.dll"
FINAL = "LocalRM_v2.dll"
PRIOR = "LocalRM.dll"
PROBE = os.path.join("restore005", "probe32", "out", "Probe32.exe")
OUTDIR = os.path.join("restore005", "evidence")

EXPORTS = ["GetResourceManagerII", "ReleaseResourceManagerII"]


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def loadtest(path, exports=EXPORTS):
    p = subprocess.run([PROBE, path] + exports, capture_output=True, text=True,
                       errors="replace")
    out = {}
    for line in p.stdout.splitlines():
        if "=" in line:
            k, _, v = line.partition("=")
            out[k.strip()] = v.strip()
    return out, p.stdout


def read_headers(path):
    d = open(path, "rb").read()
    coff = struct.unpack_from("<I", d, 0x3C)[0] + 4
    machine, nsec, tds, ptrsym, nsym, szopt, chars = struct.unpack_from("<HHIIIHH", d, coff)
    opt = coff + 20
    g = lambda o: struct.unpack_from("<I", d, opt + o)[0]
    s = lambda o: struct.unpack_from("<H", d, opt + o)[0]
    secs = []
    for i in range(nsec):
        o = opt + szopt + i * 40
        name = d[o:o + 8].rstrip(b"\x00").decode("latin-1")
        vs, va, rs, rp, ptr, ptl, nr, nl, ch = struct.unpack_from("<IIIIIIHHI", d, o + 8)
        secs.append(dict(name=name, vs=vs, va=va, rs=rs, rp=rp, ch=ch))
    dirs = []
    for i in range(16):
        rva, sz = struct.unpack_from("<II", d, opt + 96 + i * 8)
        dirs.append((rva, sz))
    return dict(
        size=len(d), machine=machine, nsec=nsec, szopt=szopt, chars=chars,
        tds=tds, magic=s(0), ep=g(16), baseofcode=g(20), baseofdata=g(24),
        imagebase=g(28), sect_align=g(32), file_align=g(36),
        size_image=g(56), size_headers=g(60), subsystem=s(68), dllchars=s(70),
        nrva=g(92), sections=secs, dirs=dirs, data=d,
    )


def main():
    os.makedirs(OUTDIR, exist_ok=True)
    rep = {}

    print("=" * 78)
    print("AGENT 07 - WINDOWS LOADABILITY TEST (real 32-bit host, WoW64 loader)")
    print("=" * 78)
    host32 = os.path.exists(PROBE)
    print("HOST_32BIT_AVAILABLE = %s (%s)" % (host32, PROBE))
    if not host32:
        print("LOAD_TEST = INSTRUMENTATION_BLOCKED")
        rep["LOAD_TEST"] = "INSTRUMENTATION_BLOCKED"
    else:
        for label, path in (("PRIOR LocalRM.dll", PRIOR), ("FINAL LocalRM_v2.dll", FINAL)):
            info, raw = loadtest(path)
            print()
            print("--- %s ---" % label)
            print(raw.rstrip())
            rep[label] = {
                "path": path,
                "sha256": sha256(path),
                "loadlibrary": info.get("LOADLIBRARY"),
                "last_error": info.get("GETLASTERROR"),
                "getprocaddress": {
                    e: info.get("GETPROCADDRESS[%s]" % e) for e in EXPORTS
                },
            }

    print()
    print("=" * 78)
    print("AGENT 08 - INDEPENDENT PE VALIDATION (final artifact)")
    print("=" * 78)
    h = read_headers(FINAL)
    checks = []
    add = lambda name, ok, detail: checks.append((name, ok, detail))
    d = h["data"]

    add("MZ", d[0:2] == b"MZ", d[0:2].hex())
    add("PE", d[struct.unpack_from("<I", d, 0x3C)[0]:][:4] == b"PE\x00\x00", "PE\\0\\0")
    add("Machine = 0x014C", h["machine"] == 0x014C, hex(h["machine"]))
    add("OptionalHeader.Magic = 0x10B", h["magic"] == 0x10B, hex(h["magic"]))
    add("IMAGE_FILE_DLL set", bool(h["chars"] & 0x2000), hex(h["chars"]))
    add("Subsystem = WINDOWS_CUI/GUI(2)", h["subsystem"] == 2, str(h["subsystem"]))
    add("SizeOfImage >= highest section end",
        h["size_image"] >= max(s["va"] + max(s["vs"], s["rs"]) for s in h["sections"]),
        "0x%X" % h["size_image"])
    add("SizeOfHeaders % FileAlignment == 0",
        h["size_headers"] % h["file_align"] == 0, "0x%X" % h["size_headers"])
    for s in h["sections"]:
        add("%s VA aligned" % s["name"], s["va"] % h["sect_align"] == 0, "0x%X" % s["va"])
        add("%s RawPtr aligned" % s["name"], s["rp"] % h["file_align"] == 0, "0x%X" % s["rp"])
        add("%s raw inside file" % s["name"], s["rp"] + s["rs"] <= h["size"],
            "0x%X+0x%X" % (s["rp"], s["rs"]))
    ep = h["ep"]
    epsec = next((s for s in h["sections"] if s["va"] <= ep < s["va"] + max(s["vs"], s["rs"])), None)
    add("entrypoint inside a section", epsec is not None, "0x%X" % ep)
    add("entrypoint section executable",
        bool(epsec and epsec["ch"] & 0x20000000), epsec["name"] if epsec else "n/a")
    for i, (rva, sz) in enumerate(h["dirs"]):
        if rva:
            add("dir[%d] RVA < SizeOfImage" % i, rva < h["size_image"], "0x%X" % rva)
    sec_rva, sec_sz = h["dirs"][4]
    if sec_rva:
        add("SECURITY/certificate inside SizeOfImage",
            sec_rva + sec_sz <= h["size_image"], "end 0x%X" % (sec_rva + sec_sz))
    add("file size <= SizeOfImage", h["size"] <= h["size_image"],
        "0x%X <= 0x%X" % (h["size"], h["size_image"]))

    n_ok = sum(1 for _, ok, _ in checks if ok)
    for name, ok, detail in checks:
        print("  %-42s %-4s %s" % (name, "OK" if ok else "FAIL", detail))
    print()
    print("checks passed: %d/%d" % (n_ok, len(checks)))

    info = dict(
        file=FINAL,
        sha256=sha256(FINAL),
        size=h["size"],
        machine=hex(h["machine"]),
        magic=hex(h["magic"]),
        address_of_entrypoint=hex(h["ep"]),
        image_base=hex(h["imagebase"]),
        section_alignment=hex(h["sect_align"]),
        file_alignment=hex(h["file_align"]),
        size_of_image=hex(h["size_image"]),
        size_of_headers=hex(h["size_headers"]),
        subsystem=h["subsystem"],
        dll_characteristics=hex(h["dllchars"]),
        number_of_rva_and_sizes=h["nrva"],
        sections=[{k: (hex(v) if isinstance(v, int) else v) for k, v in s.items()}
                  for s in h["sections"]],
        data_directories=[{"index": i, "rva": hex(r), "size": hex(z)}
                          for i, (r, z) in enumerate(h["dirs"]) if r or z],
        original_iips_sha256=sha256(ORIG),
        validation_checks_passed=n_ok,
        validation_checks_total=len(checks),
        loadability=rep,
    )
    with open(os.path.join(OUTDIR, "a08_pe_validation.json"), "w", encoding="utf-8") as f:
        json.dump(info, f, indent=2)
    with open(os.path.join(OUTDIR, "a08_pe_validation.txt"), "w", encoding="utf-8") as f:
        for name, ok, detail in checks:
            f.write("%-42s %-4s %s\n" % (name, "OK" if ok else "FAIL", detail))
        f.write("\nchecks passed: %d/%d\n" % (n_ok, len(checks)))
    print("evidence written to %s" % OUTDIR)


if __name__ == "__main__":
    main()
