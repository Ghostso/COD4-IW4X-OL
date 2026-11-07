#!/usr/bin/env python3
"""Main-line experiment A: local TQoS closure + in-game UI screenshots.

Steps:
  1. kill stale game processes
  2. launch suspend_host_redirect.py which
       - rewrites ied-tqos.qq.com -> 127.0.0.1 in the suspended image
       - binds local UDP/8000 (and friends) and answers TQoS with variant 3
       - creates the TCLS handoff block
  3. take a desktop BitBlt screenshot every few seconds to a shots/ dir
  4. after N seconds, stop and summarize

No system network setting is touched.
"""
import argparse
import json
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
GAME = os.path.join(ROOT, 'run_codol_001', 'sandbox_ifs1_20260923',
                    'codoMP_client_shipRetail.exe')
CWD = os.path.join(ROOT, 'run_codol_001', 'sandbox_ifs1_20260923')


def kill_tree():
    for exe in ('codoMP_client_shipRetail.exe', 'TQMCenter.exe',
                'IIPSHostApp.exe', 'TP3Helper.exe', 'CrossProxy.exe'):
        subprocess.run(['taskkill', '/F', '/IM', exe, '/T'],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(2)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', required=True)
    ap.add_argument('--seconds', type=float, default=150.0)
    ap.add_argument('--variant', type=int, default=3)
    ap.add_argument('--shot-every', type=float, default=3.0)
    ap.add_argument('--no-listeners', action='store_true')
    args = ap.parse_args()

    os.makedirs(args.out, exist_ok=True)
    shots = os.path.join(args.out, 'shots')
    os.makedirs(shots, exist_ok=True)
    kill_tree()

    harness_out = os.path.join(args.out, 'harness')
    py = sys.executable
    cmd = [py, '-X', 'utf8', '-u',
           os.path.join(HERE, 'suspend_host_redirect.py'),
           '--exe', GAME, '--cwd', CWD, '--out', harness_out,
           '--seconds', str(int(args.seconds) + 5),
           '--reply-variant', str(args.variant)]
    if args.no_listeners:
        cmd.append('--no-listeners')
    hlog = open(os.path.join(args.out, 'harness.stdout'), 'w',
                encoding='utf-8', errors='replace')
    harness = subprocess.Popen(cmd, stdout=hlog, stderr=subprocess.STDOUT)

    shot_log = open(os.path.join(args.out, 'shots.jsonl'), 'w',
                    encoding='utf-8')
    shotter = os.path.join(HERE, '_pop_desktop_shot.py')
    t0 = time.time()
    n = 0
    while time.time() - t0 < args.seconds and harness.poll() is None:
        n += 1
        png = os.path.join(shots, 'shot_%04d.png' % n)
        try:
            r = subprocess.run([py, '-X', 'utf8', shotter, png],
                               capture_output=True, text=True, timeout=25)
            rec = {'n': n, 't': round(time.time() - t0, 2),
                   'out': r.stdout.strip(), 'err': r.stderr.strip()[:200]}
        except Exception as exc:
            rec = {'n': n, 't': round(time.time() - t0, 2),
                   'error': repr(exc)}
        shot_log.write(json.dumps(rec, ensure_ascii=False) + '\n')
        shot_log.flush()
        time.sleep(args.shot_every)

    try:
        harness.terminate()
    except Exception:
        pass
    time.sleep(2)
    kill_tree()
    shot_log.close()
    hlog.close()

    # summarize the local listener trace
    lt = os.path.join(harness_out, 'local_listeners.jsonl')
    events = []
    if os.path.isfile(lt):
        for line in open(lt, encoding='utf-8', errors='replace'):
            try:
                events.append(json.loads(line))
            except Exception:
                pass
    payloads = [e for e in events if e.get('data_hex')]
    summary = {
        'out': args.out,
        'variant': args.variant,
        'shots': n,
        'listener_events': len(events),
        'payloads': len(payloads),
        'udp_ports': sorted(set(e.get('port') for e in payloads
                                if e.get('proto') == 'udp')),
        'tqos_requests': sum(1 for e in payloads
                             if str(e.get('data_hex', '')).startswith('7572')),
        'tqos_replies_sent': sum(1 for e in events if e.get('sent_reply_len')),
    }
    with open(os.path.join(args.out, 'A_RESULT.json'), 'w',
              encoding='utf-8') as fh:
        json.dump(summary, fh, indent=2)
    print(json.dumps(summary, ensure_ascii=False), flush=True)
    return 0


if __name__ == '__main__':
    sys.exit(main())
