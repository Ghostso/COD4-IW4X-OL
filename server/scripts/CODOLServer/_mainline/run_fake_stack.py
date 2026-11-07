#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
run_fake_stack.py -- orchestrate the local CODOL server harness.

Starts the fake TQoS/IIPS server on the loopback ports, then launches the game
with hostname redirection applied while it is still suspended, and keeps both
alive for the requested duration.

Run elevated. Observation/harness only; no system network changes.
"""

import argparse
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--exe', required=True)
    ap.add_argument('--cwd', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--seconds', type=float, default=90.0)
    ap.add_argument('--reply', action='store_true')
    ap.add_argument('--variant', type=int, default=0)
    args = ap.parse_args()

    os.makedirs(args.out, exist_ok=True)
    server_out = os.path.join(args.out, 'server')
    os.makedirs(server_out, exist_ok=True)

    srv_argv = [sys.executable, '-X', 'utf8', '-u',
                os.path.join(HERE, 'fake_tqos_server.py'),
                '--out', server_out, '--seconds', str(args.seconds + 20),
                '--ports', '8000,8081', '--variant', str(args.variant)]
    if args.reply:
        srv_argv.append('--reply')
    server = subprocess.Popen(srv_argv, stdout=subprocess.PIPE,
                              stderr=subprocess.STDOUT, text=True,
                              encoding='utf-8', errors='replace')
    print('fake server pid=%d' % server.pid, flush=True)
    time.sleep(2.0)

    game_out = os.path.join(args.out, 'game')
    os.makedirs(game_out, exist_ok=True)
    game_argv = [sys.executable, '-X', 'utf8', '-u',
                 os.path.join(HERE, 'suspend_host_redirect.py'),
                 '--exe', args.exe, '--cwd', args.cwd,
                 '--out', game_out, '--no-listeners',
                 '--seconds', str(args.seconds)]
    game = subprocess.Popen(game_argv, stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT, text=True,
                            encoding='utf-8', errors='replace')
    print('redirect launcher pid=%d' % game.pid, flush=True)

    t0 = time.time()
    while time.time() - t0 < args.seconds + 5:
        time.sleep(1)
        if game.poll() is not None and server.poll() is not None:
            break
    for p in (game, server):
        if p.poll() is None:
            p.terminate()
    time.sleep(1)
    try:
        out, _ = game.communicate(timeout=5)
        print('--- game launcher ---')
        print(out)
    except Exception:
        pass
    try:
        out, _ = server.communicate(timeout=5)
        print('--- fake server ---')
        print(out[-4000:])
    except Exception:
        pass
    return 0


if __name__ == '__main__':
    sys.exit(main())
