#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
engine_dump.py -- read-only runtime dump of the CODOL engine gap.

The EXE ships the 0x994000..0xCA789A region zero-filled on disk; the Base.dll
.tvm0 VM decrypts real x86 code into it at ~5s after launch. Static analysis
of the file therefore cannot see the game logic. This tool attaches nothing
and patches nothing: it only opens the game process with
PROCESS_QUERY_INFORMATION|PROCESS_VM_READ and reads the region a few times
after the VM fill, so the decrypted code can be disassembled offline.

Usage:
    python engine_dump.py <pid> --out <dir> [--seconds 40] [--step 4]

Outputs (inside <dir>):
    engine_<t>s.bin     raw bytes of the engine gap at that sample
    engine_dump.jsonl   one record per sample with per-page non-zero counts
    engine_dump.log     human readable summary
"""

import argparse
import ctypes
import ctypes.wintypes as wt
import hashlib
import json
import os
import struct
import sys
import time

k32 = ctypes.WinDLL('kernel32', use_last_error=True)
advapi32 = ctypes.WinDLL('advapi32', use_last_error=True)

PROCESS_QUERY_INFORMATION = 0x0400
PROCESS_VM_READ = 0x0010
MEM_COMMIT = 0x1000
PAGE_GUARD = 0x100

TOKEN_ADJUST_PRIVILEGES = 0x0020
TOKEN_QUERY = 0x0008
SE_PRIVILEGE_ENABLED = 0x00000002
SE_DEBUG_NAME = 'SeDebugPrivilege'


class LUID(ctypes.Structure):
    _fields_ = [('LowPart', wt.DWORD), ('HighPart', wt.LONG)]


class LUID_AND_ATTRIBUTES(ctypes.Structure):
    _fields_ = [('Luid', LUID), ('Attributes', wt.DWORD)]


class TOKEN_PRIVILEGES(ctypes.Structure):
    _fields_ = [('PrivilegeCount', wt.DWORD),
                ('Privileges', LUID_AND_ATTRIBUTES * 1)]


k32.GetCurrentProcess.restype = wt.HANDLE
advapi32.OpenProcessToken.argtypes = [wt.HANDLE, wt.DWORD,
                                      ctypes.POINTER(wt.HANDLE)]
advapi32.OpenProcessToken.restype = wt.BOOL
advapi32.LookupPrivilegeValueW.argtypes = [wt.LPCWSTR, wt.LPCWSTR,
                                           ctypes.POINTER(LUID)]
advapi32.LookupPrivilegeValueW.restype = wt.BOOL
advapi32.AdjustTokenPrivileges.argtypes = [
    wt.HANDLE, wt.BOOL, ctypes.POINTER(TOKEN_PRIVILEGES), wt.DWORD,
    ctypes.c_void_p, ctypes.POINTER(wt.DWORD)]
advapi32.AdjustTokenPrivileges.restype = wt.BOOL


def enable_debug_privilege():
    """Best effort: enable SeDebugPrivilege in the current elevated token."""
    token = wt.HANDLE()
    if not advapi32.OpenProcessToken(k32.GetCurrentProcess(),
                                     TOKEN_ADJUST_PRIVILEGES | TOKEN_QUERY,
                                     ctypes.byref(token)):
        return False, ctypes.get_last_error()
    luid = LUID()
    if not advapi32.LookupPrivilegeValueW(None, SE_DEBUG_NAME, ctypes.byref(luid)):
        err = ctypes.get_last_error()
        k32.CloseHandle(token)
        return False, err
    tp = TOKEN_PRIVILEGES()
    tp.PrivilegeCount = 1
    tp.Privileges[0].Luid = luid
    tp.Privileges[0].Attributes = SE_PRIVILEGE_ENABLED
    ctypes.set_last_error(0)
    ok = advapi32.AdjustTokenPrivileges(token, False, ctypes.byref(tp),
                                        ctypes.sizeof(tp), None, None)
    err = ctypes.get_last_error()
    k32.CloseHandle(token)
    return bool(ok) and err == 0, err

ENGINE_BASE = 0x00994000
# ICH-020 identified the engine code gap as 0x994000..0xCA789A. Runtime code
# also references the sentinel table at 0xCA8000, strings/data around
# 0xCD8000, and the Scaleform/libcurl/game data that continues toward the
# end of the image. The default capture therefore covers the whole useful
# module window rather than stopping in the middle of the runtime data.
ENGINE_END = 0x00E65000
ENGINE_SIZE = ENGINE_END - ENGINE_BASE
PAGE = 0x1000

EXTRA_WINDOWS = (
    ('sentinel_table', 0x00CA8000, 0x1000),
    ('runtime_strings', 0x00CD0000, 0x10000),
    ('dispatch_table', 0x00E83A00, 0x400),
    ('global_state', 0x00E83C00, 0x1000),
    ('libcurl_data', 0x00D33000, 0x1000),
    ('image_tail', 0x00E50000, 0x10000),
)

# Poll interval used while waiting for the VM to fill the engine gap.
WAIT_STEP = 0.05


class MEMORY_BASIC_INFORMATION(ctypes.Structure):
    _fields_ = [
        ('BaseAddress', ctypes.c_void_p),
        ('AllocationBase', ctypes.c_void_p),
        ('AllocationProtect', wt.DWORD),
        ('RegionSize', ctypes.c_size_t),
        ('State', wt.DWORD),
        ('Protect', wt.DWORD),
        ('Type', wt.DWORD),
    ]


k32.OpenProcess.restype = wt.HANDLE
k32.OpenProcess.argtypes = [wt.DWORD, wt.BOOL, wt.DWORD]
k32.ReadProcessMemory.restype = wt.BOOL
k32.ReadProcessMemory.argtypes = [wt.HANDLE, ctypes.c_void_p, ctypes.c_void_p,
                                  ctypes.c_size_t, ctypes.POINTER(ctypes.c_size_t)]
k32.VirtualQueryEx.restype = ctypes.c_size_t
k32.VirtualQueryEx.argtypes = [wt.HANDLE, ctypes.c_void_p,
                               ctypes.POINTER(MEMORY_BASIC_INFORMATION), ctypes.c_size_t]


def open_pid(pid):
    h = k32.OpenProcess(PROCESS_QUERY_INFORMATION | PROCESS_VM_READ, False, pid)
    if not h:
        raise SystemExit('OpenProcess(%d) failed: %d (need admin?)'
                         % (pid, ctypes.get_last_error()))
    return h


def read_region(h, base, size):
    """Read [base, base+size) in page steps; unreadable pages come back as b''."""
    out = bytearray()
    addr = base
    end = base + size
    while addr < end:
        want = min(PAGE, end - addr)
        buf = ctypes.create_string_buffer(want)
        got = ctypes.c_size_t()
        ok = k32.ReadProcessMemory(h, ctypes.c_void_p(addr), buf, want,
                                   ctypes.byref(got))
        if ok and got.value == want:
            out += buf.raw[:want]
        else:
            out += b'\x00' * want
        addr += want
    return bytes(out)


def read_probe(h, base, size):
    """Return (ok, bytes, last_error) for a single readable chunk."""
    buf = ctypes.create_string_buffer(size)
    got = ctypes.c_size_t()
    ok = bool(k32.ReadProcessMemory(h, ctypes.c_void_p(base), buf, size,
                                     ctypes.byref(got)))
    err = 0 if ok else ctypes.get_last_error()
    return ok, (buf.raw[:got.value] if ok else b''), err


def nonzero_report(data):
    total = len(data)
    nz = 0
    pages_nz = 0
    for off in range(0, total, PAGE):
        chunk = data[off:off + PAGE]
        c = sum(1 for b in chunk if b)
        nz += c
        if c:
            pages_nz += 1
    return {'bytes': total, 'nonzero_bytes': nz, 'nonzero_pages': pages_nz,
            'pages': (total + PAGE - 1) // PAGE}


def protection_map(h, base, size):
    """Return a coarse list of (start, size, state, protect) for the region."""
    rows = []
    addr = base
    end = base + size
    mbi = MEMORY_BASIC_INFORMATION()
    while addr < end:
        got = k32.VirtualQueryEx(h, ctypes.c_void_p(addr), ctypes.byref(mbi),
                                 ctypes.sizeof(mbi))
        if not got:
            break
        b = mbi.BaseAddress or 0
        rows.append((b, mbi.RegionSize, mbi.State, mbi.Protect))
        nxt = b + mbi.RegionSize
        if nxt <= addr:
            break
        addr = nxt
    return rows


def derive_runtime_code_range(sentinel):
    """Sentinel slots point at an ASLR-dependent executable mapping.

    Values in 0x10000000..0x14000000 are the dynamically mapped function
    pointers; derive the page-aligned base/size for that mapping.
    """
    vals = list(struct.unpack_from('<%dI' % (len(sentinel) // 4), sentinel, 0))
    highs = [v for v in vals if 0x10000000 <= v < 0x14000000]
    if not highs:
        return None
    base = min(highs) & ~0xFFF
    end = (max(highs) + 0xFFF) & ~0xFFF
    size = end - base
    if size <= 0 or size > 0x100000:
        return None
    return base, size


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('pid', type=int)
    ap.add_argument('--out', required=True)
    ap.add_argument('--seconds', type=float, default=45.0)
    ap.add_argument('--step', type=float, default=4.0)
    ap.add_argument('--wait-seconds', type=float, default=25.0,
                    help='wait up to this long for the engine gap to become non-zero')
    ap.add_argument('--base', type=lambda s: int(s, 16), default=ENGINE_BASE)
    ap.add_argument('--size', type=lambda s: int(s, 16), default=ENGINE_SIZE)
    args = ap.parse_args()

    os.makedirs(args.out, exist_ok=True)
    jsonl = open(os.path.join(args.out, 'engine_dump.jsonl'), 'w', encoding='utf-8')
    runtime_jsonl = open(os.path.join(args.out, 'runtime_code_samples.jsonl'),
                         'w', encoding='utf-8')
    log = open(os.path.join(args.out, 'engine_dump.log'), 'w', encoding='utf-8')

    def say(line):
        log.write(line + '\n')
        log.flush()
        print(line)

    dbg_ok, dbg_err = enable_debug_privilege()
    print('SeDebugPrivilege=%s err=%d' % (dbg_ok, dbg_err), flush=True)
    h = open_pid(args.pid)
    try:
        prot = protection_map(h, args.base, args.size)
        say('pid=%d base=0x%08X size=0x%X' % (args.pid, args.base, args.size))
        for b, s, st, pr in prot:
            say('  region 0x%08X size 0x%-8X state=0x%X protect=0x%X' % (b, s, st, pr))

        t0 = time.time()
        say('waiting for engine gap to become non-zero (<= %.1fs)...'
            % args.wait_seconds)
        filled = False
        denied_logged = False
        while time.time() - t0 < args.wait_seconds:
            ok, probe, rerr = read_probe(h, args.base, 0x1000)
            if not ok and not denied_logged:
                denied_logged = True
                say('read denied at t=%.2fs err=%d (ACE / protection)'
                    % (time.time() - t0, rerr))
            if ok and any(probe):
                filled = True
                say('engine gap filled at t=%.2fs' % (time.time() - t0))
                break
            time.sleep(WAIT_STEP)
        if not filled:
            say('engine gap never became non-zero within %.1fs' % args.wait_seconds)
        prev = None
        best = None
        best_code_nz = -1
        sample = 0
        while time.time() - t0 < (args.wait_seconds + args.seconds):
            data = read_region(h, args.base, args.size)
            sentinel = read_region(h, 0x00CA8000, 0x1000)
            sentinel_nz = sum(1 for b in sentinel if b)
            target = derive_runtime_code_range(sentinel)
            if target is not None:
                code_base, code_size = target
                code = read_region(h, code_base, code_size)
                code_nz = sum(1 for b in code if b)
                digest = hashlib.sha256(code).hexdigest()
                runtime_jsonl.write(json.dumps({
                    't': round(time.time() - t0, 3),
                    'base': code_base,
                    'size': code_size,
                    'nonzero': code_nz,
                    'sha256': digest,
                }) + '\n')
                runtime_jsonl.flush()
                say('  RUNTIME_RANGE base=0x%08X size=0x%X nonzero=%d sha256=%s'
                    % (code_base, code_size, code_nz, digest[:16]))
                if code_nz > best_code_nz:
                    best_code_nz = code_nz
                    with open(os.path.join(args.out, 'sentinel_table.bin'), 'wb') as fh:
                        fh.write(sentinel)
                    with open(os.path.join(args.out, 'runtime_code.bin'), 'wb') as fh:
                        fh.write(code)
                    with open(os.path.join(args.out, 'runtime_target_range.json'),
                              'w', encoding='utf-8') as fh:
                        json.dump({'base': code_base, 'size': code_size,
                                   'sentinel_nonzero': sentinel_nz,
                                   'runtime_code_nonzero': code_nz,
                                   'sha256': digest,
                                   'protection': protection_map(h, code_base, code_size)},
                                  fh, indent=2)
                    say('  RUNTIME_CODE base=0x%08X size=0x%X nonzero=%d'
                        % (code_base, code_size, code_nz))
            rep = nonzero_report(data)
            rep['t'] = round(time.time() - t0, 3)
            rep['sample'] = sample
            if sample > 1 and rep['nonzero_bytes'] == 0:
                rep['note'] = 'gap released'
                jsonl.write(json.dumps(rep) + '\n')
                jsonl.flush()
                say('gap released (all zero) at t=%.2fs, stopping' % rep['t'])
                break
            jsonl.write(json.dumps(rep) + '\n')
            jsonl.flush()
            say('t=%6.2fs nonzero=%9d/%9d pages=%4d/%4d' %
                (rep['t'], rep['nonzero_bytes'], rep['bytes'],
                 rep['nonzero_pages'], rep['pages']))
            if best is None or rep['nonzero_bytes'] > best[1]:
                best = (sample, rep['nonzero_bytes'], rep['t'], data)
                # Extra regions may be torn down later than the main gap;
                # snapshot them at the same moment the best main sample is read.
                for name, base, size in EXTRA_WINDOWS:
                    extra = read_region(h, base, size)
                    ep = os.path.join(args.out, name + '.bin')
                    with open(ep, 'wb') as fh:
                        fh.write(extra)
                    say('  BEST_EXTRA %-16s base=0x%08X size=0x%X nonzero=%d'
                        % (name, base, size, sum(1 for b in extra if b)))
            if prev is not None and data != prev:
                p = os.path.join(args.out, 'engine_t%06.2fs.bin' % rep['t'])
                with open(p, 'wb') as fh:
                    fh.write(data)
                say('  wrote changed sample -> %s' % os.path.basename(p))
            prev = data
            sample += 1
            time.sleep(args.step)

        if best is not None:
            p = os.path.join(args.out, 'engine_best.bin')
            with open(p, 'wb') as fh:
                fh.write(best[3])
            say('BEST sample=%d nonzero=%d t=%.2fs -> %s'
                % (best[0], best[1], best[2], os.path.basename(p)))
            for name, base, size in EXTRA_WINDOWS:
                ep = os.path.join(args.out, name + '.bin')
                if not os.path.isfile(ep):
                    extra = read_region(h, base, size)
                    with open(ep, 'wb') as fh:
                        fh.write(extra)
                    say('WROTE %-16s base=0x%08X size=0x%X nonzero=%d -> %s'
                        % (name, base, size, sum(1 for b in extra if b),
                           os.path.basename(ep)))
        say('done samples=%d' % sample)
    finally:
        k32.CloseHandle(h)
        jsonl.close()
        runtime_jsonl.close()
        log.close()
    return 0


if __name__ == '__main__':
    sys.exit(main())
