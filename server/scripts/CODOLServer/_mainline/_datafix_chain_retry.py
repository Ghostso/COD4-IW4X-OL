"""Retry the full lobby chain against the datafix sandbox.

The IIPS startup chain flakes: some launches exit with 0xFFFFFFFF right
after iips.dll loads, before ifs2.dll / the splash window.  This driver
re-runs the whole chain (8443 TLS probe + 8444 socket probe + 8446 plain
handshake probe + elevated observer) until one launch survives far enough
to be analysed, then prints the state timeline.

Usage:
  python -X utf8 CODOLServer/_mainline/_datafix_chain_retry.py \
      --sandbox <ABS_SANDBOX> --attempts 6 --seconds 130
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time

MAINLINE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, MAINLINE)

import auto_lobby_loop as loop  # noqa: E402

LS = loop.LS
PY = sys.executable


def start_plain(log_dir: str):
    os.makedirs(log_dir, exist_ok=True)
    ready = os.path.join(log_dir, "ready.flag")
    echo = os.path.join(log_dir, "echo.txt")
    plain = os.path.join(LS, "lobby_plain_probe.py")
    out = open(os.path.join(log_dir, "plain.out"), "ab")
    err = open(os.path.join(log_dir, "plain.err"), "ab")
    p = subprocess.Popen(
        [PY, "-X", "utf8", "-u", plain,
         "--bind", "127.0.0.1", "--port", "8446",
         "--log", os.path.join(log_dir, "plain.jsonl"),
         "--lobby-handshake", "--magic", "0xDC",
         "--token", "0x1122334455667788",
         "--ready-file", ready, "--ready-timeout", "150",
         "--echo-file", echo, "--hold-after-83", "80"],
        stdout=out, stderr=err)
    return p, ready, echo


def stop(p):
    if p is None:
        return
    try:
        p.terminate()
    except Exception:
        pass
    time.sleep(0.7)
    if p.poll() is None:
        try:
            p.kill()
        except Exception:
            pass


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sandbox", required=True)
    ap.add_argument("--attempts", type=int, default=6)
    ap.add_argument("--seconds", type=int, default=170)
    a = ap.parse_args()

    for attempt in range(1, a.attempts + 1):
        print("=" * 70, flush=True)
        print("ATTEMPT %d/%d" % (attempt, a.attempts), flush=True)
        loop.stop_probe()
        tag_dir = os.path.join(loop.ROOT, "CODOLServer", "logs",
                               "DATAFIX_CHAIN_%s_a%d"
                               % (time.strftime("%Y%m%d_%H%M%S"), attempt))
        loop.start_probe(tag_dir)
        plain, ready, echo = start_plain(tag_dir)
        time.sleep(1.5)

        tag, text = loop.launch(
            tag_dir, a.seconds,
            poke_host="127.0.0.1", poke_port=8443, patch_lobby_result=-1,
            poke_lobby_globals=1, poke_lobby_5e8=0, poke_lobby_9c4=0,
            handshake_ready_file=ready, abort_on_cfg0=0,
            lobby_ready_only=1, handshake_echo_file=echo,
            post83_trace=1, post83_seconds=80,
            poke_lobby_644=0, handshake_key_file="", eip_trace=0,
            sandbox=a.sandbox)
        print("run tag:", tag, "log:", tag_dir, flush=True)
        if not tag:
            print(text[-1500:], flush=True)
            stop(plain)
            loop.stop_probe()
            continue

        rows = loop.read_state(tag)
        seq = loop.summarize(rows)
        names = [k[0] for k, *_ in seq]
        max5e8 = 0
        for r in rows:
            try:
                max5e8 = max(max5e8, int(r.get("lobReq5e8") or 0))
            except ValueError:
                pass
        for key, t, ua50, hs, hst, objA, objC, stage in seq:
            print("  %-9s %-26s sub=%-3s err=%-5s code=%-6s "
                  "uA50=%-2s http=%s/%s objA=%s objC=%s stage=%s"
                  % (t, key[0], key[1], key[2], key[3], ua50, hs, hst,
                     objA, objC, stage), flush=True)
        print("  max5e8=%s states=%s" % (max5e8, names), flush=True)

        stop(plain)
        loop.stop_probe()

        if max5e8 >= 3 or any("DWLOBBY_PUMP_SUCCESS" in n for n in names):
            print("REACHED 5E8=3 / PUMP_SUCCESS -> run dir:", tag, flush=True)
            return 0
        real_names = [n for n in names if n]
        if not real_names and max5e8 == 0:
            print("  [startup flake: no DW state] retrying", flush=True)
            continue
        print("  [state reached but no 5E8=3] stopping for analysis", flush=True)
        return 2

    print("attempts exhausted", flush=True)
    return 1


if __name__ == "__main__":
    sys.exit(main())
