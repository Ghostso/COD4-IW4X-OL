"""Agent 16/17/18 - build LocalRM_v3.dll: a real, minimal ResourceManager provider.

Design is driven ONLY by the machine code of the original iips.dll (Agent
01/02/03/04/06/22).  The RESTORE_LOCALRM_001 C++ sketch was refuted on two
material points and is not used.

What the original code does (all CONFIRMED by disassembly):

  GetResourceManagerII (RVA 0x1C80), __cdecl
      if (!guard) { guard = 1; obj = operator new(0x410); ctor(obj);
                    g_instance = obj; }
      return g_instance

  ReleaseResourceManagerII (RVA 0x1C60), __cdecl, arg1 = this
      if (this) { vt = *this; fn = *vt; fn(this, 1); }   // deleting dtor

  ctor (RVA 0x11F20) writes vptrs at this+0x00, +0x04, +0x20, +0x44
  the vtable installed at this+0x00 has slot[0] == deleting destructor

  deleting destructor (RVA 0x118E0), thiscall(dtor) + stack arg `flags`
      test byte [esp+4], 1      ; scalar-delete flag
      this->vptr = <vtable>     ; re-set vtable
      if (flags & 1) operator delete(this)
      return this
      ret 4                     ; callee pops the 4-byte flag

This build reproduces that contract with the same calling conventions, a real
0x410-byte heap object, a real 48-slot vtable and a real deleting destructor.
The ResourceManager's *internal* behaviour (what the engine does with the
object) is still UNKNOWN and is intentionally not invented here.
"""
import hashlib
import os
import struct

import pefile

from x86asm import Asm

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
ORIG = os.path.join(_ROOT, "COD OL", "IIPS", "iips.dll")
OUT = os.path.join(_ROOT, "LocalRM_v3.dll")

IMAGE_SCN_CNT_CODE = 0x00000020
IMAGE_SCN_CNT_INITIALIZED_DATA = 0x00000040
IMAGE_SCN_MEM_EXECUTE = 0x20000000
IMAGE_SCN_MEM_READ = 0x40000000
IMAGE_SCN_MEM_WRITE = 0x80000000

RM_SIZE = 0x410
VTABLE_SLOTS = 48           # as requested/claimed; also >= what the original fills
ALIGN = 0x1000
IMAGE_BASE = 0x10000000     # taken from the template (validated below)


def align(v, a):
    return (v + a - 1) & ~(a - 1)


def imm32_v(v):
    """Little-endian imm32 helper used for the emitted vptr stores."""
    return struct.pack("<I", v & 0xFFFFFFFF)


def build():
    pe = pefile.PE(ORIG, fast_load=True)
    pe.parse_data_directories(directories=[
        pefile.DIRECTORY_ENTRY["IMAGE_DIRECTORY_ENTRY_IMPORT"]])
    global IMAGE_BASE
    if pe.OPTIONAL_HEADER.ImageBase != IMAGE_BASE:
        raise SystemExit("template ImageBase changed: 0x%X" % pe.OPTIONAL_HEADER.ImageBase)
    orig = open(ORIG, "rb").read()

    orig_sections = [{
        "name": s.Name.rstrip(b"\x00"),
        "vs": s.Misc_VirtualSize,
        "va": s.VirtualAddress,
        "rs": s.SizeOfRawData,
        "rp": s.PointerToRawData,
        "ch": s.Characteristics,
    } for s in pe.sections]

    # IAT slots we are allowed to call (present in the original import table).
    iat = {}
    for entry in pe.DIRECTORY_ENTRY_IMPORT:
        dll = entry.dll.decode("latin-1").lower()
        for imp in entry.imports:
            if imp.name:
                iat[(dll, imp.name.decode("latin-1"))] = imp.address
    need = [("msvcr80.dll", "??2@YAPAXI@Z"),      # operator new(unsigned int)
            ("msvcr80.dll", "??3@YAXPAX@Z")]      # operator delete(void*)
    for k in need:
        if k not in iat:
            raise SystemExit("required import %s not found in template IAT" % (k,))
    NEW = iat[("msvcr80.dll", "??2@YAPAXI@Z")]
    DEL = iat[("msvcr80.dll", "??3@YAXPAX@Z")]

    new_va = align(max(s["va"] + max(s["vs"], s["rs"]) for s in orig_sections), ALIGN)

    # ------------------------------------------------------------------ layout
    # We build one section: .localrm
    #   +0x000  GetResourceManagerII
    #   +0x040  ReleaseResourceManagerII
    #   +0x080  rm_deleting_destructor   (vtable[0])
    #   +0x0C0  rm_stub_ok               (shared stub: returns 1)
    #   +0x0E0  module_init              (lazy init helper)
    #   +0x100  entrypoint (DllMain)
    #   after code: guard dword, instance dword, then the vtable, then padding
    OFF_GET = 0x000
    OFF_REL = 0x040
    OFF_DTOR = 0x080
    OFF_STUB = 0x0C0
    OFF_INIT = 0x0E0
    OFF_ENTRY = 0x180

    # ------------------------------------------------------------------
    # Address convention (this file mixes two spaces, so be explicit):
    #   *_rva  = offset from the image base  (used inside PE structures that
    #            the spec defines as RVAs)
    #   *_va   = absolute virtual address    (used as an immediate operand in
    #            emitted code, and as a pointer value stored in the vtable)
    #
    # The first version of this builder used RVAs where VAs were required in
    # `mov eax, imm32`, which faulted at the first instruction (caught by
    # ProbeVeh: EIP 0x10055005, EAX 0x00055200).
    # ------------------------------------------------------------------
    guard_rva = 0x200
    inst_rva = 0x204
    vtable_rva = 0x210
    names_rva = 0x300

    guard_va = IMAGE_BASE + new_va + guard_rva
    inst_va = IMAGE_BASE + new_va + inst_rva
    vtable_va = IMAGE_BASE + new_va + vtable_rva
    names_va = IMAGE_BASE + new_va + names_rva

    # ---- GetResourceManagerII (__cdecl, no args) ----
    #   mov  eax, guard      ; B8 <guard>
    #   cmp  dword [eax], 0  ; 83 38 00
    #   je   do_init         ; 74 xx
    #   mov  eax, instance   ; B8 <instance>
    #   mov  eax, [eax]      ; 8B 00
    #   ret                  ; C3
    # do_init:
    #   call lazy_init       ; E8 rel32
    #   mov  eax, instance   ; B8 <instance>
    #   mov  eax, [eax]      ; 8B 00
    #   ret                  ; C3
    a = Asm(IMAGE_BASE + new_va + OFF_GET)
    a.mov_eax_imm32(guard_va)
    a.raw(b"\x83\x38\x00")            # cmp dword [eax], 0
    je_site = a.label()
    a.db(0x74, 0x00)                  # JE rel8 -> patched below
    a.mov_eax_imm32(inst_va)
    a.raw(b"\x8B\x00")                # mov eax, [eax]
    a.ret()
    do_init_va = a.label()
    a.b[je_site - a.base + 1] = (do_init_va - (je_site + 2)) & 0xFF
    a.call_rel32_to(IMAGE_BASE + new_va + OFF_INIT)
    a.mov_eax_imm32(inst_va)
    a.raw(b"\x8B\x00")
    a.ret()
    get_code = a.bytes()
    assert len(get_code) <= OFF_REL - OFF_GET, len(get_code)

    # ---- ReleaseResourceManagerII (__cdecl, arg1 = this) ----
    r = Asm(IMAGE_BASE + new_va + OFF_REL)
    r.mov_ecx_ptr_esp(4)            # 8B 4C 24 04   mov ecx, [esp+4]
    r.test_ecx_ecx()                # 85 C9
    r.db(0x74, 0x0B)                # 74 0B         je +0x0B (to ret)
    r.mov_eax_ptr_ecx()             # 8B 01         mov eax, [ecx]
    r.raw(b"\x8B\x10")              # 8B 10         mov edx, [eax]
    r.push_imm32(1)                 # 68 01 00 00 00
    r.raw(b"\xFF\xD2")              # FF D2         call edx
    r.ret()                         # C3
    rel_code = r.bytes()
    assert len(rel_code) <= OFF_DTOR - OFF_REL, len(rel_code)

    # ---- rm_deleting_destructor (thiscall + stack flag) ----
    # mirrors original RVA 0x118E0:
    #   test byte [esp+4], 1 ; this = ecx ; this->vptr = <vt> ;
    #   if (flag&1) operator delete(this) ; return this ; ret 4
    dt = Asm(IMAGE_BASE + new_va + OFF_DTOR)
    # Mirrors the original at RVA 0x118E0: the `mov eax, esi` must sit at the
    # JOIN point after the conditional free, so it runs on BOTH paths.
    # Previously it was emitted inside the taken branch, so the flags==0 path
    # fell through and returned whatever was in eax (EAX held the vtable).
    dt.test_byte_ptr_esp_disp_imm8(4, 1)   # F6 44 24 04 01  test byte [esp+4], 1
    dt.db(0x56)                            # 56               push esi
    dt.raw(b"\x8B\xF1")                    # 8B F1            mov esi, ecx
    dt.mov_ptr_ecx_imm32(vtable_va)        # C7 01 <vt>       mov [ecx], vtable
    je_site = dt.label()
    dt.db(0x74, 0x00)                      # 74 xx            je -> join (patched)
    dt.db(0x56)                            # 56               push esi
    dt.call_abs(DEL)                       # FF 15 <del>      call operator delete
    dt.db(0x59)                            # 59               pop ecx  (cdecl balance)
    join_va = dt.label()
    dt.b[je_site - dt.base + 1] = (join_va - (je_site + 2)) & 0xFF
    dt.raw(b"\x8B\xC6")                    # 8B C6            mov eax, esi  <-- join
    dt.db(0x5E)                            # 5E               pop esi
    dt.ret_n(4)                            # C2 04 00         ret 4
    dtor_code = dt.bytes()
    assert len(dtor_code) <= OFF_STUB - OFF_DTOR, len(dtor_code)

    # ---- shared non-null stub used by the remaining vtable slots ----
    st = Asm(IMAGE_BASE + new_va + OFF_STUB)
    st.mov_eax_imm32(1)             # B8 01 00 00 00
    st.ret()                        # C3
    stub_code = st.bytes()

    # ---- lazy init helper (called by GetResourceManagerII) ----
    # Equivalent to:
    #   void lazy_init(void) {
    #       if (g_guard) return;
    #       RM* o = (RM*)operator new(0x410);   // returns in eax
    #       if (!o) return;
    #       o->vptr0  = abs(&vt[0]);
    #       o->vptr1  = abs(&vt[1]);
    #       o->vptr20 = abs(&vt[20]);
    #       o->vptr44 = abs(&vt[44]);
    #       g_instance = o;
    #       g_guard = 1;
    #   }
    #
    # The first build of this file was wrong twice and Agent 21 caught it:
    #   1. `pop ecx` after `call operator new` destroyed the returned pointer
    #      (operator new is __cdecl, so the caller must clean the pushed size
    #      with `add esp, 4`, and the result must be kept in eax or moved);
    #   2. the vptr immediates were written as RVAs instead of absolute VAs.
    i = Asm(IMAGE_BASE + new_va + OFF_INIT)
    i.mov_eax_imm32(guard_va)
    i.raw(b"\x8B\x00")               # mov eax,[guard]
    i.db(0x85, 0xC0)                 # test eax,eax
    je_skip = i.label()
    i.db(0x75, 0x00)                 # jne -> done   (patched)
    # --- do the allocation ---
    i.push_imm32(RM_SIZE)
    i.call_abs(NEW)
    i.raw(b"\x83\xC4\x04")           # 83 C4 04   add esp, 4  (cdecl cleanup)
    i.raw(b"\x85\xC0")               # test eax,eax
    je_fail = i.label()
    i.db(0x74, 0x00)                 # je -> done    (patched)
    # keep the new pointer: edx = eax
    i.raw(b"\x8B\xD0")               # 8B D0      mov edx, eax
    # initialise the object: vptr at +0, +4, +0x20, +0x44 (as the real ctor does)
    # vtable_va is already absolute, so do NOT add IMAGE_BASE again here.
    i.db(0xC7, 0x02).raw(imm32_v(vtable_va))
    i.db(0xC7, 0x42, 0x04).raw(imm32_v(vtable_va + 4))
    i.db(0xC7, 0x42, 0x20).raw(imm32_v(vtable_va + 0x20))
    i.db(0xC7, 0x42, 0x44).raw(imm32_v(vtable_va + 0x44))
    # store instance, then set guard
    i.mov_eax_imm32(inst_va)
    i.raw(b"\x89\x10")               # 89 10      mov [eax], edx
    i.mov_eax_imm32(guard_va)
    i.raw(b"\xC7\x00")               # C7 00      mov dword [eax], 1
    i.raw(struct.pack("<I", 1))
    done_va = i.label()
    # patch the two conditional jumps to the common epilogue
    i.b[je_skip - i.base + 1] = (done_va - (je_skip + 2)) & 0xFF
    i.b[je_fail - i.base + 1] = (done_va - (je_fail + 2)) & 0xFF
    i.ret()
    init_code = i.bytes()
    assert len(init_code) <= OFF_ENTRY - OFF_INIT, len(init_code)

    # ---- entrypoint: DllMain(stdcall) returning TRUE ----
    e = Asm(IMAGE_BASE + new_va + OFF_ENTRY)
    e.mov_eax_imm32(1)              # B8 01 00 00 00   mov eax, 1
    e.ret_n(0x0C)                   # C2 0C 00         ret 0x0C
    entry_code = e.bytes()

    # ---- assemble the section image ----
    payload = bytearray(b"\xCC" * 0x400)

    def put(off, data):
        payload[off:off + len(data)] = data

    put(OFF_GET, get_code)
    put(OFF_REL, rel_code)
    put(OFF_DTOR, dtor_code)
    put(OFF_STUB, stub_code)
    put(OFF_INIT, init_code)
    put(OFF_ENTRY, entry_code)

    # The mutable state (guard + instance pointer) MUST start as zero.  The
    # rest of the section is 0xCC-filled INT3 padding, which is correct for
    # unreachable code but fatal for data: a 0xCC-filled guard reads as
    # "already initialised", so GetResourceManagerII would skip construction
    # and hand back an uninitialised instance pointer.
    STATE_LO = 0x200
    STATE_HI = 0x20C            # guard(4) + instance(4) + 4 bytes slack
    for i in range(STATE_LO, STATE_HI):
        payload[i] = 0

    # vtable: slot0 = deleting destructor, slot1 = delete (no free),
    # every remaining slot = shared stub (never NULL, matching the original's
    # habit of filling unused slots rather than zeroing them).
    #
    # IMPORTANT: these are absolute virtual addresses, not RVAs.  A vtable entry
    # is dereferenced directly as a code pointer at runtime, so writing an RVA
    # produces an un-callable value.
    vt = bytearray()
    for slot in range(VTABLE_SLOTS):
        target = ((IMAGE_BASE + new_va + OFF_DTOR) if slot == 0
                  else (IMAGE_BASE + new_va + OFF_STUB))
        vt += struct.pack("<I", target)
    vt_off = vtable_rva
    payload[vt_off:vt_off + len(vt)] = vt

    # export names
    n_off = names_rva
    n1 = b"GetResourceManagerII\x00"
    n2 = b"ReleaseResourceManagerII\x00"
    n_dll = b"LocalRM_v3.dll\x00"
    payload[n_off:n_off + len(n_dll)] = n_dll
    off_n1 = n_off + len(n_dll)
    payload[off_n1:off_n1 + len(n1)] = n1
    off_n2 = off_n1 + len(n1)
    payload[off_n2:off_n2 + len(n2)] = n2
    # export arrays
    off_funcs = align(off_n2 + len(n2), 4)
    payload[off_funcs:off_funcs + 8] = struct.pack(
        "<II", new_va + OFF_GET, new_va + OFF_REL)
    off_names = off_funcs + 8
    payload[off_names:off_names + 8] = struct.pack(
        "<II", new_va + off_n1, new_va + off_n2)
    off_ords = off_names + 8
    payload[off_ords:off_ords + 4] = struct.pack("<HH", 0, 1)
    # export directory last
    off_exp = align(off_ords + 4, 16)
    # ------------------------------------------------------------------
    # Address forms inside IMAGE_EXPORT_DIRECTORY (verified against the
    # original iips.dll export directory, which uses RVAs):
    #
    #   Name .................. RVA of the DLL name string
    #   AddressOfFunctions ..... RVA of the EAT (export address table)
    #   AddressOfNames ......... RVA of the name-pointer table
    #   AddressOfNameOrdinals .. RVA of the ordinal-index table
    #   entries inside the EAT . RVA of the exported function
    #   entries inside AddressOfNames . RVA of a name string
    #
    # Everything in this structure is an RVA.  The earlier over-correction
    # wrote VAs here and pefile (correctly) rejected the directory.
    # ------------------------------------------------------------------
    payload[off_exp:off_exp + 40] = struct.pack(
        "<IIHHIIIIIII",
        0, 0, 0, 0,
        new_va + n_off, 1, 2, 2,
        new_va + off_funcs,
        new_va + off_names,
        new_va + off_ords)

    vs = align(off_exp + 40, ALIGN)
    payload = payload[:vs]
    while len(payload) < vs:
        payload.append(0)

    # ------------------------------------------------------------ PE assembly
    sections = []
    for s in orig_sections:
        sec = dict(s)
        sec["raw"] = orig[s["rp"]:s["rp"] + s["rs"]]
        sections.append(sec)
    sections.append({
        "name": b".localrm",
        "va": new_va,
        "vs": vs,
        "rs": vs,
        "rp": new_va,
        "ch": (IMAGE_SCN_CNT_CODE | IMAGE_SCN_CNT_INITIALIZED_DATA
               | IMAGE_SCN_MEM_EXECUTE | IMAGE_SCN_MEM_READ | IMAGE_SCN_MEM_WRITE),
        "raw": bytes(payload),
    })

    nsec = len(sections)
    size_headers = align(0x200 + 4 + 20 + 224 + nsec * 40, ALIGN)
    size_image = align(sections[-1]["va"] + sections[-1]["vs"], ALIGN)

    out = bytearray(b"\x00" * 0x200)
    struct.pack_into("<H", out, 0, 0x5A4D)
    struct.pack_into("<H", out, 2, 0x0090)
    struct.pack_into("<H", out, 4, 0x0003)
    struct.pack_into("<H", out, 8, 0x0004)
    struct.pack_into("<H", out, 0x0C, 0xFFFF)
    struct.pack_into("<H", out, 0x10, 0x00B8)
    struct.pack_into("<H", out, 0x18, 0x0040)
    struct.pack_into("<I", out, 0x3C, 0x200)
    out.extend(b"PE\x00\x00")
    out.extend(struct.pack("<HHIIIHH",
                           0x014C, nsec, pe.FILE_HEADER.TimeDateStamp,
                           0, 0, 224, pe.FILE_HEADER.Characteristics))
    assert len(out) == 0x200 + 4 + 20

    dirs = [(d.VirtualAddress, d.Size) for d in pe.OPTIONAL_HEADER.DATA_DIRECTORY]
    dirs[0] = (new_va + off_exp, 40)
    dirs[8] = (0, 0)

    size_of_code = sum(s["rs"] for s in sections if s["ch"] & IMAGE_SCN_CNT_CODE)
    size_of_idata = sum(s["rs"] for s in sections if s["ch"] & IMAGE_SCN_CNT_INITIALIZED_DATA)

    OVERRIDES = {
        "Magic": 0x010B,
        "MajorLinkerVersion": 6, "MinorLinkerVersion": 0,
        "SizeOfCode": size_of_code,
        "SizeOfInitializedData": size_of_idata,
        "SizeOfUninitializedData": 0,
        "AddressOfEntryPoint": new_va + OFF_ENTRY,
        "BaseOfCode": sections[0]["va"],
        "BaseOfData": sections[1]["va"],
        "ImageBase": pe.OPTIONAL_HEADER.ImageBase,
        "SectionAlignment": ALIGN, "FileAlignment": ALIGN,
        "MajorOperatingSystemVersion": pe.OPTIONAL_HEADER.MajorOperatingSystemVersion,
        "MinorOperatingSystemVersion": pe.OPTIONAL_HEADER.MinorOperatingSystemVersion,
        "MajorImageVersion": 0, "MinorImageVersion": 0,
        "MajorSubsystemVersion": pe.OPTIONAL_HEADER.MajorSubsystemVersion,
        "MinorSubsystemVersion": pe.OPTIONAL_HEADER.MinorSubsystemVersion,
        "Reserved1": 0,
        "SizeOfImage": size_image, "SizeOfHeaders": size_headers, "CheckSum": 0,
        "Subsystem": pe.OPTIONAL_HEADER.Subsystem,
        "DllCharacteristics": pe.OPTIONAL_HEADER.DllCharacteristics,
        "SizeOfStackReserve": pe.OPTIONAL_HEADER.SizeOfStackReserve,
        "SizeOfStackCommit": pe.OPTIONAL_HEADER.SizeOfStackCommit,
        "SizeOfHeapReserve": pe.OPTIONAL_HEADER.SizeOfHeapReserve,
        "SizeOfHeapCommit": pe.OPTIONAL_HEADER.SizeOfHeapCommit,
        "LoaderFlags": 0, "NumberOfRvaAndSizes": 16,
    }
    SHORT = {"Magic", "Subsystem", "DllCharacteristics"}
    oh_buf = bytearray(224)
    oh_ex = pe.OPTIONAL_HEADER
    for name, val in OVERRIDES.items():
        struct.pack_into("<H" if name in SHORT else "<I",
                         oh_buf, oh_ex.get_field_relative_offset(name), val)
    for idx, (rva, sz) in enumerate(dirs[:16]):
        struct.pack_into("<II", oh_buf, 96 + idx * 8, rva, sz)
    out.extend(oh_buf)

    for s in sections:
        blob = struct.pack("<8sIIIIIIHHI",
                           (s["name"] + b"\x00" * 8)[:8],
                           s["vs"], s["va"], s["rs"], s["rp"], 0, 0, 0, 0, s["ch"])
        assert len(blob) == 40
        out.extend(blob)

    assert len(out) <= size_headers
    out.extend(b"\x00" * (size_headers - len(out)))
    for s in sections:
        # gap between sections is normal: original raw offsets are preserved
        # verbatim, so pad up to each section's own PointerToRawData.
        if len(out) < s["rp"]:
            out.extend(b"\x00" * (s["rp"] - len(out)))
        assert len(out) == s["rp"], (s["name"], len(out), s["rp"])
        out.extend(s["raw"])

    with open(OUT, "wb") as f:
        f.write(bytes(out))

    # ------------------------------------------------------------------ report
    print("=" * 78)
    print("AGENT 16/17 - LocalRM_v3.dll built by direct machine-code emission")
    print("=" * 78)
    print("ORIGINAL     %s (%d bytes) sha256 %s"
          % (ORIG, len(orig), hashlib.sha256(orig).hexdigest()))
    print("OUTPUT       %s (%d bytes) sha256 %s"
          % (OUT, len(out), hashlib.sha256(bytes(out)).hexdigest()))
    print()
    print("section      .localrm VA 0x%X  size 0x%X" % (new_va, vs))
    print("SizeOfImage  0x%X   SizeOfHeaders 0x%X   sections %d"
          % (size_image, size_headers, nsec))
    print()
    print("--- emitted code ---")
    print("GetResourceManagerII      RVA 0x%X  %d bytes  %s"
          % (new_va + OFF_GET, len(get_code), get_code.hex()))
    print("ReleaseResourceManagerII  RVA 0x%X  %d bytes  %s"
          % (new_va + OFF_REL, len(rel_code), rel_code.hex()))
    print("deleting destructor       RVA 0x%X  %d bytes  %s"
          % (new_va + OFF_DTOR, len(dtor_code), dtor_code.hex()))
    print("shared stub               RVA 0x%X  %d bytes  %s"
          % (new_va + OFF_STUB, len(stub_code), stub_code.hex()))
    print("lazy init helper          RVA 0x%X  %d bytes  %s"
          % (new_va + 0x0E0, len(init_code), init_code.hex()))
    print("DllMain                   RVA 0x%X  %d bytes  %s"
          % (new_va + OFF_ENTRY, len(entry_code), entry_code.hex()))
    print()
    print("guard      VA 0x%08X" % guard_va)
    print("instance   VA 0x%08X" % inst_va)
    print("vtable     VA 0x%08X (%d slots)" % (vtable_va, VTABLE_SLOTS))
    print("operator new  IAT 0x%08X" % NEW)
    print("operator del  IAT 0x%08X" % DEL)
    print("export dir RVA 0x%X" % (new_va + off_exp))
    for i, (rva, sz) in enumerate(dirs):
        if rva or sz:
            print("   dir[%2d] 0x%08X size 0x%X" % (i, rva, sz))

    pe.close()


if __name__ == "__main__":
    build()
