#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Early-handle AES key-schedule hunt for the 8081 QoS channel.

Flow (no injection, no Frida):
  1. CreateProcess(game, CREATE_SUSPENDED)
  2. OpenProcess(ALL_ACCESS) BEFORE ACE arms -> handle survives
  3. Redirect the TQoS host strings to 127.0.0.1 in-place (equal length)
  4. Start local listeners (8000 + 8081, plus the usual port set)
  5. Resume; keep late-patching during the patch window
  6. As soon as a real 8081 datagram arrives, scan process memory for
     16/24/32-byte AES keys, validating each with the captured ciphertexts
  7. Report any key that decrypts ALL captured 8081 first blocks to the
     wire magic 'ur'/'us'

Writes nothing into the target other than the equal-length host placeholders
that the existing mainline harness already uses.
"""

import argparse
import ctypes
import ctypes.wintypes as wt
import json
import os
import socket
import struct
import sys
import threading
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))

import suspend_host_redirect as S  # noqa: E402  (reuse verified helpers)
import aes_schedule_hunt as AS  # noqa: E402

from cryptography.hazmat.primitives.ciphers import (  # noqa: E402
    Cipher, algorithms, modes)

k32 = S.k32


def aes_ecb_dec(key, block):
    d = Cipher(algorithms.AES(key), modes.ECB()).decryptor()
    return d.update(block) + d.finalize()


MAGICS = (b'ur', b'us', b'ru', b'su')


def scan_for_key(h, packets, out, log, time_limit=600.0):
    """Scan committed memory; return list of candidate keys."""
    firsts = [p[:16] for p in packets]
    candidates = []
    skip_ranges = module_skip_ranges(h)
    log('ACE/985 module ranges skipped: %s' % skip_ranges)
    t0 = time.time()
    n_regions = 0
    n_bytes = 0
    for base, size in S.regions(h):
        if any(base < e and base + size > s for s, e in skip_ranges):
            continue
        if time.time() - t0 > time_limit:
            log('time limit hit during key scan')
            break
        n_regions += 1
        off = 0
        while off < size:
            want = min(0x100000, size - off)
            data = S.read_some(h, base + off, want)
            if data:
                n_bytes += len(data)
                n = len(data)
                for ksize in (16, 24, 32):
                    for o2 in range(0, n - ksize + 1, 4):
                        key = bytes(data[o2:o2 + ksize])
                        if key == bytes(ksize) or len(set(key)) < 4:
                            continue
                        try:
                            pt = aes_ecb_dec(key, firsts[0])
                        except Exception:
                            continue
                        if pt[:2] not in MAGICS:
                            continue
                        hits = 0
                        det = []
                        for i, ct in enumerate(firsts):
                            try:
                                q = aes_ecb_dec(key, ct)
                            except Exception:
                                break
                            if q[:2] in MAGICS:
                                hits += 1
                                det.append({'pkt': i, 'pt': q.hex()})
                        candidates.append({
                            'va': base + off + o2, 'bits': ksize * 8,
                            'key': key.hex(), 'pt_first': pt.hex(),
                            'confirmed': hits, 'n_packets': len(firsts),
                            'details': det[:9]})
                        if hits == len(firsts):
                            log('*** FULL MATCH key=%s va=0x%08X bits=%d'
                                % (key.hex(), base + off + o2, ksize * 8))
            off += want
        if n_regions % 300 == 0:
            log('scan regions=%d bytes=%d cand=%d t=%.0fs'
                % (n_regions, n_bytes, len(candidates), time.time() - t0))
    log('key scan done regions=%d bytes=%d cand=%d'
        % (n_regions, n_bytes, len(candidates)))
    return candidates


def module_skip_ranges(h):
    """Return [(start,end)] for ACE/985-protected modules (hard constraint)."""
    TH32CS_SNAPMODULE = 0x00000008
    TH32CS_SNAPMODULE32 = 0x00000010

    class MODULEENTRY32W(ctypes.Structure):
        _fields_ = [
            ('dwSize', wt.DWORD), ('th32ModuleID', wt.DWORD),
            ('th32ProcessID', wt.DWORD), ('GlblcntUsage', wt.DWORD),
            ('ProccntUsage', wt.DWORD), ('modBaseAddr', ctypes.c_void_p),
            ('modBaseSize', wt.DWORD), ('hModule', ctypes.c_void_p),
            ('szModule', wt.WCHAR * 256),
            ('szExePath', wt.WCHAR * 260)]

    k32.GetProcessId.restype = wt.DWORD
    k32.GetProcessId.argtypes = [wt.HANDLE]
    k32.CreateToolhelp32Snapshot.restype = wt.HANDLE
    k32.CreateToolhelp32Snapshot.argtypes = [wt.DWORD, wt.DWORD]
    k32.Module32FirstW.argtypes = [wt.HANDLE,
                                   ctypes.POINTER(MODULEENTRY32W)]
    k32.Module32NextW.argtypes = [wt.HANDLE,
                                  ctypes.POINTER(MODULEENTRY32W)]
    pid = k32.GetProcessId(h)
    snap = k32.CreateToolhelp32Snapshot(
        TH32CS_SNAPMODULE | TH32CS_SNAPMODULE32, pid)
    out = []
    if not snap or snap == -1:
        return out
    me = MODULEENTRY32W()
    me.dwSize = ctypes.sizeof(me)
    ok = k32.Module32FirstW(snap, ctypes.byref(me))
    while ok:
        name = me.szModule.lower()
        if any(t in name for t in ('ace', '985')):
            b = int(me.modBaseAddr or 0)
            out.append((b, b + int(me.modBaseSize)))
        ok = k32.Module32NextW(snap, ctypes.byref(me))
    k32.CloseHandle(snap)
    return out


def schedule_hunt_thread(h, out, log, time_limit):
    """Run the schedule hunter on the pre-arm handle (survives ACE)."""
    log('schedule-hunt thread started')
    found = []
    sbox_hits = []
    t0 = time.time()
    n_regions = 0
    n_bytes = 0
    for base, size in S.regions(h):
        if time.time() - t0 > time_limit:
            log('schedule-hunt time limit')
            break
        n_regions += 1
        off = 0
        while off < size:
            want = min(0x100000, size - off)
            data = S.read_some(h, base + off, want)
            if data:
                n_bytes += len(data)
                if len(sbox_hits) < 8 and AS.INV_SBOX in data:
                    i = data.find(AS.INV_SBOX)
                    sbox_hits.append(base + off + i)
                    log('AES INV SBOX at 0x%08X' % (base + off + i))
                AS.scan_chunk(data, base + off, found, log)
            off += want
        if n_regions % 200 == 0:
            log('schedule-hunt regions=%d bytes=%d schedules=%d t=%.0fs'
                % (n_regions, n_bytes, len(found), time.time() - t0))
    with open(os.path.join(out, 'aes_schedules.jsonl'), 'w',
              encoding='utf-8') as fh:
        for f in found:
            fh.write(json.dumps(f, ensure_ascii=False) + '\n')
    with open(os.path.join(out, 'aes_sbox_hits.json'), 'w',
              encoding='utf-8') as fh:
        json.dump(sbox_hits, fh, indent=2)
    log('schedule-hunt done regions=%d bytes=%d schedules=%d sbox=%d'
        % (n_regions, n_bytes, len(found), len(sbox_hits)))


def main():
    default_root = os.path.dirname(os.path.dirname(HERE))  # project root
    default_game = os.path.join(default_root, 'run_codol_001',
                                'sandbox_ifs1_20260923')
    ap = argparse.ArgumentParser()
    ap.add_argument('--exe',
                    default=os.path.join(default_game,
                                         'codoMP_client_shipRetail.exe'))
    ap.add_argument('--cwd', default=default_game)
    ap.add_argument('--out', required=True)
    ap.add_argument('--seconds', type=float, default=180.0)
    ap.add_argument('--patch-seconds', type=float, default=45.0)
    ap.add_argument('--wait-8081', type=float, default=150.0)
    ap.add_argument('--scan-limit', type=float, default=600.0)
    ap.add_argument('--no-redirect', action='store_true')
    ap.add_argument('--reply-variant', type=int, default=5,
                    help='TQoS 8000 response variant; 5 = ConndIP+GameSvrList')
    ap.add_argument('--advertise-port', type=int, default=8000)
    args = ap.parse_args()

    os.makedirs(args.out, exist_ok=True)
    logf = open(os.path.join(args.out, 'aes_key_early.log'), 'w',
                encoding='utf-8')

    def log(msg):
        logf.write(msg + '\n')
        logf.flush()
        print(msg, flush=True)

    ok, err = S.enable_debug()
    log('SeDebugPrivilege=%s err=%d' % (ok, err))

    si = S.STARTUPINFOW()
    si.cb = ctypes.sizeof(si)
    pi = S.PROCESS_INFORMATION()
    cmd = '"%s" -q --disable-gpu --disable-gpu-compositing' % args.exe
    buf = ctypes.create_unicode_buffer(cmd)
    if not k32.CreateProcessW(args.exe, buf, None, None, True,
                              S.CREATE_SUSPENDED, None, args.cwd,
                              ctypes.byref(si), ctypes.byref(pi)):
        raise SystemExit('CreateProcess failed: %d' % ctypes.get_last_error())
    pid = pi.dwProcessId
    log('created suspended pid=%d' % pid)

    h = k32.OpenProcess(S.PROCESS_ALL_ACCESS, False, pid)
    log('pre-arm OpenProcess(ALL_ACCESS) -> %s err=%d'
        % (h, ctypes.get_last_error()))
    if not h:
        k32.ResumeThread(pi.hThread)
        raise SystemExit('cannot get handle')

    stop_evt = threading.Event()
    listener_trace, _ = S.start_listeners(
        args.out, stop_evt, args.reply_variant, 'echo', args.advertise_port)
    log('listeners started tcp=%s udp=%s' % (S.TCP_PORTS, S.UDP_PORTS))

    if not args.no_redirect:
        found = {}
        for base, size in S.regions(h):
            off = 0
            while off < size:
                want = min(0x100000, size - off)
                data = S.read_some(h, base + off, want)
                if data:
                    for src, dst in S.REDIRECTS.items():
                        start = 0
                        while True:
                            i = data.find(src, start)
                            if i < 0:
                                break
                            found.setdefault(src.decode(), []).append(
                                base + off + i)
                            S.write_bytes(h, base + off + i, dst)
                            start = i + 1
                off += want
        log('redirect targets: %s' % {k: len(v) for k, v in found.items()})

    k32.ResumeThread(pi.hThread)
    log('resumed')

    # Keep a non-daemon reference so the interpreter waits for the schedule
    # hunt even if the 8081 wait loop ends first.
    threading.Thread(target=schedule_hunt_thread,
                     args=(h, args.out, log, args.scan_limit),
                     daemon=False).start()

    # read the capture file to learn when real 8081 packets arrive
    cap = os.path.join(args.out, 'local_listeners.jsonl')
    t0 = time.time()
    packets = []
    next_patch = 0.0
    late = dict()
    last_logged = 0.0
    while time.time() - t0 < args.seconds:
        el = time.time() - t0
        if el <= args.patch_seconds and el >= next_patch:
            next_patch = el + 0.5
            for base, size in S.regions(h):
                off = 0
                while off < size:
                    want = min(0x100000, size - off)
                    data = S.read_some(h, base + off, want)
                    if data:
                        for src, dst in S.REDIRECTS.items():
                            start = 0
                            while True:
                                i = data.find(src, start)
                                if i < 0:
                                    break
                                va = base + off + i
                                if va not in late.setdefault(
                                        src.decode(), set()):
                                    late[src.decode()].add(va)
                                    S.write_bytes(h, va, dst)
                                start = i + 1
                    off += want
            if el - last_logged >= 30.0:
                last_logged = el
                hosts = {k: len(v) for k, v in late.items() if v}
                log('late-patch t=%.0fs hosts=%s' % (el, hosts))
        # poll capture
        if os.path.exists(cap):
            try:
                rows = [json.loads(l) for l in open(
                    cap, encoding='utf-8', errors='replace') if l.strip()]
            except Exception:
                rows = []
            new = [r for r in rows
                   if r.get('port') == 8081 and r.get('data_hex')]
            if new:
                packets = [bytes.fromhex(r['data_hex']) for r in new]
                log('captured %d 8081 packet(s) at t=%.1fs lens=%s'
                    % (len(packets), el, [len(p) for p in packets]))
                break
        time.sleep(0.25)

    if not packets:
        log('no 8081 traffic captured within %.0fs' % args.seconds)

    result = {'pid': pid, 'packets': [p.hex() for p in packets],
              'candidates': []}
    if packets:
        cands = scan_for_key(h, packets, args.out, log, args.scan_limit)
        full = [c for c in cands if c['confirmed'] == len(packets)]
        log('candidates=%d full_matches=%d' % (len(cands), len(full)))
        cands.sort(key=lambda c: -c['confirmed'])
        result['candidates'] = cands
        with open(os.path.join(args.out, 'aes_key_candidates.jsonl'), 'w',
                  encoding='utf-8') as fh:
            for c in cands:
                fh.write(json.dumps(c, ensure_ascii=False) + '\n')
        if full:
            with open(os.path.join(args.out, 'aes_key_FOUND.json'), 'w',
                      encoding='utf-8') as fh:
                json.dump(full, fh, ensure_ascii=False, indent=2)
            log('KEY FOUND -> aes_key_FOUND.json')

    with open(os.path.join(args.out, 'aes_key_early_summary.json'), 'w',
              encoding='utf-8') as fh:
        json.dump(result, fh, ensure_ascii=False, indent=2)

    stop_evt.set()
    time.sleep(0.5)
    try:
        listener_trace.close()
    except Exception:
        pass
    # leave the game running; do not kill it
    # Stop the 8081 wait early; the non-daemon schedule hunt keeps running and
    # the process script will wait for it before exiting.
    log('wait loop finished; waiting for schedule hunt to complete')
    for t in threading.enumerate():
        if t.name.startswith('Thread-') and t is not threading.current_thread():
            t.join(timeout=args.scan_limit + 60)
    log('done pid=%d' % pid)
    logf.close()
    return 0


if __name__ == '__main__':
    sys.exit(main())
