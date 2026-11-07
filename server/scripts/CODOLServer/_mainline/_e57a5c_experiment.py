"""Single-byte experiment: unlock the resource-registration dispatcher.

Background (all read from the decrypted runtime image, base 0x400000):

    008083B3  cmp byte [0xE57A5C], 0
    008083BA  je 0x8085CD          ; 0 -> the whole block is skipped
    008083C0  mov al, [0xC7AF440]  ; only reached when 0xE57A5C != 0
    ...
    008083D2  mov eax, 8
    008083D9  call 0x50E930

Measured across two full runs: 0xE57A50..0xE57A5F is constant for the whole
run, and 0xE57A5C reads 0.  So 0xC7AF440 is never even read, and any patch
aimed at 0xC7AF440 would be aimed at dead code.

0xE57A5C lives in .data (a config-populated enable table), so writing it is a
data write -- the same class of change as the lobby host/port globals, which
are already used by the normal flow.  It is NOT a .text patch.

This driver runs one full lobby chain with the byte set to 1 and reports
whether anything downstream moved.  Reversible: it is a single byte and the
process is restarted for every attempt anyway.

Usage:
  python -X utf8 CODOLServer/_mainline/_e57a5c_experiment.py \
      --sandbox <ABS_SANDBOX> --attempts 3 --seconds 150
"""
from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
import threading
import time

MAINLINE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, MAINLINE)

import auto_lobby_loop as loop  # noqa: E402

LS = loop.LS
PY = sys.executable


def start_plain(log_dir: str, echo_85: bool = False,
                echo_85_rule: str = "send", follow_85: bool = False,
                follow_85_rule: str = "send", follow_85_cbc: bool = False,
                follow_85_aes_key: str = "",
                follow_85_rand_iv: bool = False,
                follow_85_delay: float = 0.0,
                follow_85_wait_flag: str = "",
                serve_delay: float = 0.0,
                token: str = "0x1122334455667788",
                p608_key_file: str = "",
                reply_85_cbc: bool = False,
                reply_85_aes_key: str = "",
                reply_85_aes_key_file: str = "",
                reply_85_zero_keys: bool = False,
reply_85_len_field: int = -1,
reply_85_pad_after_tag: int = 0,
                reply_85_rand_iv: bool = False,
                reply_85_seqs: str = "1",
                reply_85_arm_first: bool = False,
                echo_85_inner89: bool = False,
                echo_85_keep_type: bool = False,
                echo_85_session_file: str = "",
                key_file: str = "",
                reply_85_task: bool = False,
                reply_85_out_keys: bool = False,
                secrets_file: str = "",
                port: int = 8446):
    os.makedirs(log_dir, exist_ok=True)
    ready = os.path.join(log_dir, "ready.flag")
    echo = os.path.join(log_dir, "echo.txt")
    tx = os.path.join(log_dir, "tx.txt")
    rx = os.path.join(log_dir, "rx.txt")
    sess = os.path.join(log_dir, "session.txt")
    plain = os.path.join(LS, "lobby_plain_probe.py")
    out = open(os.path.join(log_dir, "plain.out"), "ab")
    err = open(os.path.join(log_dir, "plain.err"), "ab")
    argv = [PY, "-X", "utf8", "-u", plain,
            "--bind", "127.0.0.2", "--port", str(port),
            "--log", os.path.join(log_dir, "plain.jsonl"),
            "--lobby-handshake", "--magic", "0xDC",
            "--token", token,
            "--ready-file", ready, "--ready-timeout", "150",
            "--echo-file", echo, "--hold-after-83", "80",
            "--keepalive4", "00000000", "--keepalive4-every", "5"]
    if serve_delay > 0:
        argv += ["--serve-delay", str(serve_delay)]
    if echo_85:
        argv += ["--echo-85", "--echo-85-rule", echo_85_rule]
        if echo_85_inner89:
            argv.append("--echo-85-inner89")
        if echo_85_keep_type:
            argv.append("--echo-85-keep-type")
        # Always pass the session file: the probe waits for it to become
        # non-zero and substitutes it into the reply's 16-byte block.  Passing
        # it only when the caller pre-set the path meant the substitution
        # never happened in the normal flow.
        argv += ["--echo-85-session-file", sess]
        # The rewrap needs the same key the observer exports.  'send' uses the
        # tx source (obj+0x60C), 'receive' uses the 0x620 source.
        argv += ["--key-file", tx if echo_85_rule == "send" else rx]
    if reply_85_task:
        # DW 任务应答路径(密钥取自 provider +0x9C, 见 handoff 28.x)
        argv.append("--reply-85-task")
        if reply_85_out_keys:
            argv.append("--reply-85-out-keys")
        if secrets_file:
            argv += ["--secrets-file", secrets_file]
            # 只等很短: provider 密钥在"客户端处理完 0x83 之后"才建立,
            # 等太久会把 0x83 本身堵住(2026-10-05 实测自锁)。
            # 密钥若晚到, 由探针的 pending_frames 补答兜底。
            argv += ["--wait-keys-max", "3"]
    if follow_85:
        argv += ["--follow-85", "--follow-85-rule", follow_85_rule,
                 "--follow-85-v1", "0" if follow_85_cbc else "1"]
        if follow_85_cbc:
            argv.append("--follow-85-cbc")
            if follow_85_rand_iv:
                argv.append("--follow-85-rand-iv")
            if follow_85_delay > 0:
                argv += ["--follow-85-delay", str(follow_85_delay)]
            if follow_85_wait_flag:
                argv += ["--follow-85-wait-flag", follow_85_wait_flag]
            # The CBC builder needs the AES key, and the inner-block builder
            # needs the codec source from the observer's tx/rx sidecar.  Both
            # used to be appended only inside the --reply-85-cbc branch, so a
            # plain --follow-85-cbc run shipped an empty src20 and silently
            # fell back to build_0x85(frame_len=200) -> 204-byte frames.
            if follow_85_aes_key:
                argv += ["--follow-85-aes-key", follow_85_aes_key]
            elif p608_key_file:
                argv += ["--follow-85-aes-key-file", p608_key_file]
            argv += ["--key-file", tx if follow_85_rule == "send" else rx]
    if reply_85_cbc:
        argv.append("--reply-85-cbc")
        # The reply builder signs/encrypts with a 20-byte source from
        # --key-file.  Without --follow-85 that flag was never set, so
        # src20 fell back to certificate DER bytes and every reply was
        # keyed with the wrong material (see handoff 27.1).  Always point
        # it at the same observer sidecar the rule implies.
        if "--key-file" not in argv:
            argv += ["--key-file", tx if follow_85_rule == "send" else rx]
        if reply_85_aes_key:
            argv += ["--reply-85-aes-key", reply_85_aes_key]
        if reply_85_seqs:
            argv += ["--reply-85-seqs", reply_85_seqs]
            if not follow_85 and follow_85_aes_key:
                argv += ["--follow-85-aes-key", follow_85_aes_key]
        if reply_85_arm_first:
            argv.append("--reply-85-arm-first")
        if reply_85_aes_key_file:
            argv += ["--reply-85-aes-key-file", reply_85_aes_key_file]
        if reply_85_zero_keys:
            argv.append("--reply-85-zero-keys")
    if reply_85_len_field >= 0:
        argv += ["--reply-85-len-field", str(reply_85_len_field)]
    if reply_85_pad_after_tag > 0:
        argv += ["--reply-85-pad-after-tag", str(reply_85_pad_after_tag)]
        if reply_85_rand_iv:
            argv.append("--reply-85-rand-iv")
        # The reply branch reads its codec source from --key-file too.  A
        # standalone --reply-85-cbc run (without --follow-85-cbc) still needs
        # it, so append here as well; duplicates are harmless.
        argv += ["--key-file", tx if follow_85_rule == "send" else rx]
    p = subprocess.Popen(argv, stdout=out, stderr=err)
    return p, ready, echo, tx, rx, sess


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


def launch_with_poke(tag_dir, seconds, ready, echo, sandbox, poke_spec,
                     dump_ranges="", dump_out="", dump_at=55, write_spec="",
                     key_file="", game_args="", eip_trace=False, obj_dump="",
                     dw_timeline=False, dw_timeline_start=0.0,
                     dw_timeline_end=1000000.0, dw_timeline_interval=0.001,
                     dw_bp=False,
                     tx_file="", rx_file="", session_file="",
                     secrets_file="",
                     p608_key_file="",
    poke_port="8443", force_85_pass=False,
    no_poke=False,
    observer_lobby_port=0,
    poke_lobby_644=False,
                     poke_g2f_on_st5=False,
                     poke_644_on_st5=False,
                     poke_e59_on_st5=False,
                     poke_e59_value=4,
                     poke_1f4_on_st5=False,
                     poke_1f4_value=2,
                     poke_dw_on_st5=False,
                     poke_dw_value=3,
compat4=False,
arm_bounds_relax=False,
                     patch_85_pass=False, patch_delay=0.0, debug_launch=False,
                     patch_87_gate=False, patch_85_srcbase=False,
                     patch_85_bufbase=False,
                     force_p608_zero_key=False,
                     bp_probe="", bp_log=""):
    """Same chain as auto_lobby_loop.launch, plus the -PokeE57 switch."""
    script = os.path.join(loop.ROOT, "run_codol_001",
                          "capture_elevated_network.ps1")
    argv = [PY, "-X", "utf8", "agent_client.py", "run", "powershell",
            "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", script,
            "-DurationSeconds", str(seconds),
            "-Sandbox", sandbox,
            *(["-LobbyPort3074", str(observer_lobby_port)]
              if observer_lobby_port else []),
            # NOTE: these two overwrite the client's internal constants and
            # therefore BYPASS hosts + dwauth.ini.  --no-poke leaves them out
            # so the document's mechanism (DNS route + ini port) is what the
            # client actually uses.
            *([] if no_poke else ["-PokeLobbyHost", "127.0.0.1",
                                  "-PokeLobbyPort", str(poke_port)]),
            *([] if no_poke else ["-PokeLobbyGlobals", "1"]),
            "-HandshakeReadyFile", ready,
            "-LobbyReadyOnly", "1",
            "-HandshakeEchoFile", echo,
            "-Post83Trace", "1",
            "-Post83Seconds", "80"]
    if poke_spec:
        argv += ["-PokeE57", poke_spec]
    if dump_ranges:
        argv += ["-DumpRanges", dump_ranges,
                 "-DumpOut", dump_out,
                 "-DumpAt", str(dump_at)]
    if write_spec:
        # NOTE: -DumpAt is NOT passed when there is no dump.  A previous
        # version passed it here, which made the observer treat DumpAt as
        # an always-on trigger and fire on the very first tick (t=0.0),
        # so --write-spec landed before the target memory was mapped.
        argv += ["-WriteSpec", write_spec]
    if key_file:
        argv += ["-HandshakeKeyFile", key_file]
    else:
        argv += ["-HandshakeKeyFile", rx_file]
    if tx_file:
        argv += ["-HandshakeTxFile", tx_file]
    if session_file:
        argv += ["-HandshakeSessionFile", session_file]
    if secrets_file:
        # F: 盘口径: provider+0x9C 的 AES 密钥 + 40B blob 还原出的 HMAC 密钥
        argv += ["-SecretsFile", secrets_file]
    if p608_key_file:
        # Keep the flag next to the key file (same directory) so the probe and
        # the observer resolve the same path.
        argv += ["-AcReadyFlag", (p608_key_file[:-4] + "_ac_ready.flag"
                                  if p608_key_file.endswith(".txt")
                                  else p608_key_file + "_ac_ready.flag")]
        argv += ["-HandshakeP608KeyFile", p608_key_file]
    if force_85_pass:
        argv += ["-Force85Pass", "1"]
    if poke_lobby_644:
        argv += ["-PokeLobby644", "1"]
    if poke_g2f_on_st5:
        argv += ["-PokeG2fOnSt5", "1"]
    if poke_644_on_st5:
        argv += ["-Poke644OnSt5", "1"]
    if poke_e59_on_st5:
        argv += ["-PokeE59OnSt5", "1",
                 "-PokeE59Value", str(poke_e59_value)]
    if poke_1f4_on_st5:
        argv += ["-Poke1f4OnSt5", "1",
                 "-Poke1f4Value", str(poke_1f4_value)]
    if poke_dw_on_st5:
        argv += ["-PokeDwOnSt5", "1",
                 "-PokeDwValue", str(poke_dw_value)]
    if compat4:
        argv += ["-Compat4", "1"]
    if arm_bounds_relax:
        argv += ["-ArmBoundsRelax", "1"]
    if patch_85_pass:
        argv += ["-Patch85Pass", "1"]
        if patch_delay > 0:
            argv += ["-PatchDelay", str(patch_delay)]
        if patch_87_gate:
            argv += ["-Patch87Gate", "1"]
        if patch_85_srcbase:
            argv += ["-Patch85Srcbase", "1"]
        if patch_85_bufbase:
            argv += ["-Patch85Bufbase", "1"]
    if force_p608_zero_key:
        argv += ["-ForceP608ZeroKey", "1"]
    if debug_launch:
        argv += ["-DebugLaunch", "1"]
    if game_args:
        argv += ["-GameArgs", game_args]
    if eip_trace:
        argv += ["-EipTrace", "1"]
    if dw_timeline:
        argv += ["-DwTimeline", "1",
                 "-DwTimelineStart", str(dw_timeline_start),
                 "-DwTimelineEnd", str(dw_timeline_end),
                 "-DwTimelineInterval", str(dw_timeline_interval)]
    if dw_bp:
        argv += ["-DwBp", "1"]
    if obj_dump:
        argv += ["-ObjDump", obj_dump]
    r = subprocess.run(argv, capture_output=True, text=True,
                       encoding="utf-8", errors="replace",
                       timeout=1200, cwd=MAINLINE)
    text = (r.stdout or "") + (r.stderr or "")
    m = re.search(r"IFS1_ELEVATED_(\d{8}_\d{6})", text)
    return (m.group(0) if m else None), text


def report(tag):
    rows = loop.read_state(tag)
    if not rows:
        return None
    seq = loop.summarize(rows)
    names = [k[0] for k, *_ in seq]
    print("  states: %s" % [n for n in names if n], flush=True)
    # pull the interesting POST83_WATCH fields out of the raw stdout
    # loop.RUNS points at restore_iips_contract_001\runs (which holds the
    # state CSV), but the observer stdout lives under run_codol_001\runs.
    path = os.path.join(loop.ROOT, "run_codol_001", "runs", tag,
                        "aboprobe.stdout")
    pat = re.compile(r"([A-Za-z0-9]+)=([^/\s,]+)")
    watch = []
    if os.path.exists(path):
        for line in open(path, encoding="utf-8", errors="replace"):
            if "POST83_WATCH," not in line:
                continue
            f = dict(pat.findall(line))
            watch.append((float(line.split(",")[0]), f))
    if watch:
        first, last = watch[0][1], watch[-1][1]
        for k in ("tag", "hd28", "h91c", "h0c4", "zbuf", "stepId", "stepTbl",
                  "pv", "req190", "rqB0", "rqAC", "obj", "gA", "gB",
                  "load", "n9b0", "nab8", "p1", "s1", "bufa", "bufb",
                  "e57", "c440", "c1e0", "c0b0", "f69d", "f595", "f511",
                  "gate", "gec", "cfgobj", "st"):
            if first.get(k) != last.get(k):
                print("  %-7s %s -> %s   <== CHANGED" % (k, first.get(k),
                                                         last.get(k)),
                      flush=True)
            else:
                print("  %-7s %s (unchanged)" % (k, last.get(k)), flush=True)
        print("  watch samples: %d, span %.1f -> %.1f"
              % (len(watch), watch[0][0], watch[-1][0]), flush=True)
        return last
    return {}


def attach_breakpoint_probe(bp_probe, bp_log, existing_runs):
    """Wait for the fresh observer run, then attach the elevated x86 probe."""
    runs_dir = os.path.join(loop.ROOT, "run_codol_001", "runs")
    deadline = time.time() + 45.0
    run_dir = None
    pid = None
    while time.time() < deadline:
        try:
            names = [n for n in os.listdir(runs_dir)
                     if n not in existing_runs and
                     n.startswith("IFS1_ELEVATED_")]
        except OSError:
            names = []
        if names:
            run_dir = os.path.join(runs_dir, sorted(names)[-1])
            stdout = os.path.join(run_dir, "aboprobe.stdout")
            if os.path.exists(stdout):
                text = open(stdout, encoding="utf-8", errors="replace").read()
                matches = re.findall(r"PROCESS_CREATED,pid=(\d+)", text)
                if matches:
                    pid = int(matches[-1])
                    break
        time.sleep(0.2)

    if not pid:
        print("BP_PROBE: no game PID found", flush=True)
        return

    # Attach immediately after the PID appears.  ACE can set process
    # protection very early, so waiting until the .text is unpacked makes
    # DebugActiveProcess fail with ERROR_ACCESS_DENIED.  The probe retries
    # arming on every debug-event timeout and will arm at ~4.5 s, once the
    # real bytes exist.
    os.makedirs(os.path.dirname(os.path.abspath(bp_log)), exist_ok=True)
    argv = [PY, "-X", "utf8", "agent_client.py", "run",
            bp_probe, str(pid), os.path.abspath(bp_log), "80"]
    print("BP_PROBE: attaching pid=%d run=%s" %
          (pid, os.path.basename(run_dir)), flush=True)
    r = subprocess.run(argv, capture_output=True, text=True,
                       encoding="utf-8", errors="replace",
                       timeout=180, cwd=MAINLINE)
    print("BP_PROBE: exit=%s" % r.returncode, flush=True)
    text = ((r.stdout or "") + (r.stderr or "")).strip()
    if text:
        print(text[-2000:], flush=True)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sandbox", required=True)
    ap.add_argument("--attempts", type=int, default=3)
    ap.add_argument("--seconds", type=int, default=150)
    ap.add_argument("--poke", default="0x00E57A5A",
                    help="comma list of absolute byte addresses to set to 1 "
                         "(default: the arg-6 block gate 0xE57A5A)")
    ap.add_argument("--dump-ranges", default="",
                    help='targeted memory dump, e.g. '
                         '"0x3300000-0x3400000,0xC7AE000-0xC7B0000"')
    ap.add_argument("--dump-out", default="", help="output .bin for the dump")
    ap.add_argument("--write-spec", default="",
                    help='hex@addr list, e.g. "414243@0x0331D420"')
    ap.add_argument("--key-file", default="",
                    help="export the 20-byte [req+0x620] handshake key here")
    ap.add_argument("--echo-85", action="store_true",
                    help="echo the client's own 0x85 frames back to it")
    ap.add_argument("--echo-85-rule", choices=["send", "receive"],
                    default="send",
                    help="rewrap key for --echo-85: send uses obj+0x60C, "
                         "receive uses obj+0x620")
    ap.add_argument("--follow-85", action="store_true",
                    help="send a synthesised server->client 0x85 containing "
                         "an inner 0x89 message with a u32 source cursor")
    ap.add_argument("--follow-85-rule", choices=["send", "receive"],
                    default="send",
                    help="key for --follow-85: send uses obj+0x60C "
                    "(byte-exact rule), receive uses obj+0x620")
    ap.add_argument("--follow-85-cbc", action="store_true",
                    help="AES-CBC-encrypt the inner 0x89 message for "
                    "--follow-85 using the receive-side key")
    ap.add_argument("--follow-85-aes-key", default="",
                    help="16-byte hex AES key from the live p608 object")
    ap.add_argument("--p608-key-file", default="",
                    help="observer-published [p608+0x14] 16-byte AES key")
    ap.add_argument("--follow-85-rand-iv", action="store_true",
                    help="with --follow-85-cbc: random IV for the two initial "
                         "0x85 frames instead of all-zero")
    ap.add_argument("--follow-85-wait-flag", default="",
                    help="with --follow-85: wait for this file (observer's "
                         "obj+0xAC 0->382 edge) before sending")
    ap.add_argument("--follow-85-delay", type=float, default=0.0,
                    help="with --follow-85: wait N seconds before sending, so "
                         "the client is already in lobby state (it reaches "
                         "c8=2/5e8=3 at about T+38 s)")
    ap.add_argument("--reply-85-cbc", action="store_true",
                    help="reply to every inbound client 0x85 with a "
                    "server-side CBC frame using the same seq")
    ap.add_argument("--reply-85-aes-key", default="",
                    help="16-byte hex AES key for --reply-85-cbc")
    ap.add_argument("--reply-85-aes-key-file", default="",
                    help="file rewritten continuously by the observer with the "
                         "LIVE p608 key; defaults to --p608-key-file")
    ap.add_argument("--reply-85-len-field", type=lambda s: int(s, 0),
                    default=-1,
                    help="override the u32 length field in reply 0x85 frames "
                         "(client requires field + cursor <= obj+0xAC)")
    ap.add_argument("--reply-85-pad-after-tag", type=lambda s: int(s, 0),
                    default=0,
                    help="with --reply-85-cbc: append N zero bytes after the "
                         "8-byte tag so the client's own recorded frame size "
                         "exceeds the length field, letting the 0xBA3AC2 check "
                         "frame_len + cursor <= obj+0xAC pass")
    ap.add_argument("--reply-85-zero-keys", action="store_true",
                    help="with --reply-85-cbc: build replies with all-zero AES "
                         "and HMAC keys (pairs with --force-p608-zero-key)")
    ap.add_argument("--reply-85-rand-iv", action="store_true",
                    help="with --reply-85-cbc: use a random IV instead of the "
                         "all-zero default")
    ap.add_argument("--reply-85-seqs", default="1",
                    help="comma list of client 0x85 seq values to answer")
    ap.add_argument("--reply-85-arm-first", action="store_true",
                    help="with --reply-85-cbc: send the 0x87 arm before the "
                         "first 0x89 business reply")
    ap.add_argument("--reply-85-task", action="store_true",
                    help="DW 任务应答路径: 解客户端 0x85 任务帧, 按 "
                         "u32 len | 01 | TLV 回包; 密钥取自 observer 写的 "
                         "secrets.txt (provider +0x9C)")
    ap.add_argument("--reply-85-out-keys", action="store_true",
                    help="with --reply-85-task: 用已验证的发送侧密钥对 "
                         "(aes_out/hmac_out) 签名+加密应答")
    ap.add_argument("--echo-85-inner89", action="store_true",
                    help="with --echo-85: keep the client's outer frame and "
                         "seq, replace the 16-byte block with the 0x89 inner "
                         "message, then re-sign (combines the seq gate that "
                         "rewrap passes with the content the handler expects)")
    ap.add_argument("--echo-85-keep-type", action="store_true",
                    help="with --echo-85: keep the client's original frame "
                         "type 0xAB instead of rewriting it to 0x00")
    ap.add_argument("--force-85-pass", action="store_true",
                    help="data-side bypass: after the 0x83 stage, keep writing "
                    "[obj+0x644]=1 so the client's lobby state machine "
                    "advances as if the inbound 0x85 had validated.  "
                    "Writes only game data fields; no code patch.")
    ap.add_argument("--serve-delay", type=float, default=0.0,
                    help="delay the plain probe's handshake by N seconds, so "
                         "the client's frame processing happens after the "
                         "observer's patches")
    ap.add_argument("--patch-delay", type=float, default=0.0,
                    help="delay the --patch-85-pass writes until this many "
                         "seconds after launch (ACE finishes its startup "
                         "check by ~5.4 s; the lobby connects at ~39 s)")
    ap.add_argument("--patch-85-pass", action="store_true",
                    help="code-level bypass: patch the two live 0x85 validation "
                    "sites at 0xBA39D4 and 0xBA3A15. This may trigger ACE.")
    ap.add_argument("--patch-87-gate", action="store_true",
                    help="with --patch-85-pass: NOP the 0xBA3AE9 `jne`, so "
                         "every parsed opcode falls through to the 0x87 arm "
                         "and bypasses the 0x89 business branch. Diagnostic "
                         "only; do not use to validate the natural handshake. "
                         "This may trigger ACE.")
    ap.add_argument("--token", default="0x1122334455667788",
                    help="u64 token placed in the 0x81 frame. The client "
                    "splits it across [obj+0x638]/[obj+0x63C] and then "
                    "DEREFERENCES it, so a synthetic constant makes it read "
                    "garbage. 0x0 removes that confound.")
    # RESTORED 2026-10-02: the observer has always supported -PokeLobby644 and
    # the 09-28/09-29 era used it (65 of 75 valid runs emitted
    # POKE_LOBBY_COMPLETE with mgreq644=1).  This driver was later rewritten
    # without it, so every run since has had [req+0x644] left at 0 -- which is
    # exactly the "gate never opens" symptom that was then investigated for
    # days as if it were a newly discovered blocker.
    ap.add_argument("--poke-lobby-644", action="store_true",
                    help="restore the pre-09-30 behaviour: have the observer "
                    "write [req+0x644]=1 so the client's dispatcher takes the "
                    "armed path. This is the state the 'good era' runs used.")
    ap.add_argument("--compat4", action="store_true",
                    help="apply the four compatibility patches from "
                    "CODOL_LOBBY_WORKING_20261002.md (0xB9A78E / 0xB9A7C5 / "
                    "0xB9A7C4 call->jmp / 0xBA3C1C). Bytes verified "
                    "byte-exact against our runtime image before use.")
    ap.add_argument("--arm-bounds-relax", action="store_true",
                    help="client-side code patch: rewrite 0xBA3AC8 "
                    "`76 16` (jbe) to `EB 16` (jmp) so the 0xBA3AC2 bound "
                    "frame_len+cursor <= obj+0xAC stops rejecting our 0x85. "
                    "Same length, no other instruction disturbed. Bytes "
                    "verified before use (see handoff 23.5).")
    ap.add_argument("--poke-g2f-on-st5", action="store_true",
                    help="data-only: the moment UI stage [0x84ABA50] becomes 5, "
                    "set byte [0x84ABB2F]=1 so 0x4A93E0 can run and the DW "
                    "config chain (gate/gec/cfg/cfgobj) can start")
    ap.add_argument("--poke-644-on-st5", action="store_true",
                    help="data-only: while UI stage [0x84ABA50]==5, re-assert "
                    "[req+0x644]=1 so 0xBA0780 takes the 644!=0 branch and "
                    "0xB7A670 can return 2")
    ap.add_argument("--poke-e59-on-st5", action="store_true",
                    help="data-only: while UI stage [0x84ABA50]==5, hold "
                    "[0xE59D20] at --poke-e59-value to test the waiting state")
    ap.add_argument("--poke-e59-value", type=int, default=4,
                    help="value for --poke-e59-on-st5 (default 4)")
    ap.add_argument("--poke-1f4-on-st5", action="store_true",
                    help="data-only: while UI stage [0x84ABA50]==5, hold "
                    "[req+0x1F4] at --poke-1f4-value")
    ap.add_argument("--poke-1f4-value", type=int, default=2,
                    help="value for --poke-1f4-on-st5 (default 2)")
    ap.add_argument("--poke-dw-on-st5", action="store_true",
                    help="data-only: while st>=4, hold [0x849BA34] at "
                         "--poke-dw-value to test the DW pump")
    ap.add_argument("--poke-dw-value", type=int, default=3,
                    help="value for --poke-dw-on-st5 (default 3)")
    ap.add_argument("--no-poke", action="store_true",
                    help="do NOT overwrite the client's lobby host/port "
                    "constants. The working document routes by DNS (hosts) "
                    "and port (dwauth.ini), so poking memory fights our own "
                    "configuration. Use this to test the document's mechanism "
                    "as written.")
    ap.add_argument("--patch-85-srcbase", action="store_true",
                    help="with --patch-85-pass: enable the 0xBA3A90 "
                    "`push ebx -> push esi` rewrite. OFF by default because "
                    "that argument slots an OUTPUT pointer in 0xB783C0, so "
                         "enabling it corrupts the inner type byte.")
    ap.add_argument("--patch-85-bufbase", action="store_true",
                    help="with --patch-85-pass: rewrite 0xBA44BE "
                         "`mov ebx,eax` to `mov ebx,[eax+0x1C]` so the inner "
                         "reader gets the stream's byte buffer instead of its "
                         "capacity value")
    ap.add_argument("--debug-launch", action="store_true",
                    help="launch the game as a debuggee and set software "
                    "breakpoints at 0xBA4430, 0xBA3710 and 0xBA38F2. This "
                    "will trigger ACE.")
    ap.add_argument("--force-p608-zero-key", action="store_true",
                    help="data-only: install an all-zero AES-128 key and its "
                    "schedule into the live p608 provider before 0x85 handling")
    ap.add_argument("--bp-probe", default="",
                    help="path to BreakpointProbe.exe; attaches to the game PID "
                    "after it starts and dumps the 0xBA4430 / 0xBA3710 / "
                    "0xBA38F2 contexts")
    ap.add_argument("--bp-log", default="",
                    help="log file the breakpoint probe writes")
    # REVERTED 2026-10-02: 8443/8446 is the configuration the working chain
    # was actually built and verified with (09-29: 52/147 valid runs reached
    # the handshake).  A document suggested 3074; changing it broke the
    # established chain, so the defaults are back to what works.
    ap.add_argument("--plain-port", type=int, default=8446,
                    help="port the plain lobby probe binds (the client must "
                         "still be poked to --poke-port, normally 8443)")
    ap.add_argument("--poke-port", type=int, default=8443,
                    help="value written to the client's lobby port constant; "
                         "this is independent of --plain-port")
    ap.add_argument("--observer-lobby-port", type=int, default=8446,
                    help="port the observer writes into the client's lobby "
                         "globals (-LobbyPort3074).  Must match --plain-port "
                         "or the client dials a port nobody is listening on.")
    ap.add_argument("--dump-at", type=float, default=55.0,
                    help="elapsed seconds to take the dump (default 55)")
    ap.add_argument("--game-args", default="",
                    help='extra client command line after "-q", e.g. '
                         '"+set intro 0" (engine consumes "+<cmd>" tokens)')
    ap.add_argument("--eip-trace", action="store_true",
                    help="sample thread EIPs in 0xBA0000-0xBB0000 and log "
                         "ecx/esi/edi (to catch the 0xBA4430 dispatcher this)")
    ap.add_argument("--dw-timeline", action="store_true",
                    help="sample the DW pump state words and thread EIPs at "
                         "high frequency (read-only)")
    ap.add_argument("--dw-timeline-start", type=float, default=0.0,
                    help="start second for --dw-timeline")
    ap.add_argument("--dw-timeline-end", type=float, default=1000000.0,
                    help="end second for --dw-timeline")
    ap.add_argument("--dw-timeline-interval", type=float, default=0.001,
                    help="sampling interval in seconds for --dw-timeline")
    ap.add_argument("--dw-bp", action="store_true",
                    help="break on 0x7EF1C8 and 0x7EF1FF (requires --debug-launch)")
    ap.add_argument("--obj-dump", default="",
                    help="write [[0x08269774]+0x4F4 .. +0x700] the moment "
                         "[obj+0x5E8] first reaches 3")
    a = ap.parse_args()

    for attempt in range(1, a.attempts + 1):
        print("=" * 72, flush=True)
        print("ATTEMPT %d/%d  (poke %s := 1)" % (attempt, a.attempts, a.poke),
              flush=True)
        loop.stop_probe()
        d = os.path.join(loop.ROOT, "CODOLServer", "logs",
                         "E57A5C_%s_a%d"
                         % (time.strftime("%Y%m%d_%H%M%S"), attempt))
        loop.start_probe(d)
        secrets = os.path.join(d, "secrets.txt")
        plain, ready, echo, tx, rx, sess = start_plain(
            d, echo_85=a.echo_85, echo_85_rule=a.echo_85_rule,
            reply_85_task=a.reply_85_task, secrets_file=secrets,
            reply_85_out_keys=a.reply_85_out_keys,
            follow_85=a.follow_85, follow_85_rule=a.follow_85_rule,
            follow_85_cbc=a.follow_85_cbc,
            follow_85_aes_key=a.follow_85_aes_key,
            follow_85_rand_iv=a.follow_85_rand_iv,
            follow_85_delay=a.follow_85_delay,
            follow_85_wait_flag=a.follow_85_wait_flag,
            serve_delay=a.serve_delay,
            token=a.token,
            p608_key_file=a.p608_key_file,
            reply_85_cbc=a.reply_85_cbc,
            reply_85_aes_key=a.reply_85_aes_key,
            reply_85_aes_key_file=(a.reply_85_aes_key_file
                                   or a.p608_key_file),
            reply_85_zero_keys=a.reply_85_zero_keys,
    reply_85_len_field=a.reply_85_len_field,
    reply_85_pad_after_tag=a.reply_85_pad_after_tag,
            reply_85_rand_iv=a.reply_85_rand_iv,
            reply_85_seqs=a.reply_85_seqs,
            reply_85_arm_first=a.reply_85_arm_first,
            echo_85_inner89=a.echo_85_inner89,
            echo_85_keep_type=a.echo_85_keep_type,
            key_file=a.key_file, port=a.plain_port)
        time.sleep(1.5)
        bp_thread = None
        if a.bp_probe and a.bp_log:
            runs_dir = os.path.join(loop.ROOT, "run_codol_001", "runs")
            try:
                existing_runs = set(os.listdir(runs_dir))
            except OSError:
                existing_runs = set()
            bp_thread = threading.Thread(
                target=attach_breakpoint_probe,
                args=(os.path.abspath(a.bp_probe),
                      os.path.abspath(a.bp_log), existing_runs),
                daemon=True)
            bp_thread.start()
        tag, text = launch_with_poke(d, a.seconds, ready, echo, a.sandbox,
                                     poke_spec=a.poke,
                                     dump_ranges=a.dump_ranges,
                                     dump_out=a.dump_out,
                                     dump_at=a.dump_at,
                                     write_spec=a.write_spec,
                                     key_file=a.key_file,
                                     game_args=a.game_args,
                                     eip_trace=a.eip_trace,
                                     dw_timeline=a.dw_timeline,
                                     dw_timeline_start=a.dw_timeline_start,
                                     dw_timeline_end=a.dw_timeline_end,
                                     dw_timeline_interval=a.dw_timeline_interval,
                                     dw_bp=a.dw_bp,
                                     obj_dump=a.obj_dump,
                                     tx_file=tx,
                                     rx_file=rx,
                                     session_file=sess,
                                     secrets_file=secrets,
                                     p608_key_file=a.p608_key_file,
                                     force_85_pass=a.force_85_pass,
                                     poke_lobby_644=a.poke_lobby_644,
                                     poke_g2f_on_st5=a.poke_g2f_on_st5,
                                     poke_644_on_st5=a.poke_644_on_st5,
                                     poke_e59_on_st5=a.poke_e59_on_st5,
                                     poke_e59_value=a.poke_e59_value,
                                     poke_1f4_on_st5=a.poke_1f4_on_st5,
                                     poke_1f4_value=a.poke_1f4_value,
                                     poke_dw_on_st5=a.poke_dw_on_st5,
                                     poke_dw_value=a.poke_dw_value,
    compat4=a.compat4,
    arm_bounds_relax=a.arm_bounds_relax,
                                     patch_85_pass=a.patch_85_pass,
                                     patch_delay=a.patch_delay,
                                     patch_87_gate=a.patch_87_gate,
                                     patch_85_srcbase=a.patch_85_srcbase,
                                     patch_85_bufbase=a.patch_85_bufbase,
                                     debug_launch=a.debug_launch,
                                     force_p608_zero_key=a.force_p608_zero_key,
                                     poke_port=a.poke_port,
                                     no_poke=a.no_poke,
                                     observer_lobby_port=a.observer_lobby_port)
        if bp_thread is not None:
            bp_thread.join(timeout=170)
        print("run tag:", tag, "log:", d, flush=True)
        if not tag:
            print(text[-1500:], flush=True)
            stop(plain)
            loop.stop_probe()
            continue
        poke_line = [l for l in (text or "").splitlines()
                     if "POKE_E57" in l]
        for l in poke_line:
            print("  " + l.strip(), flush=True)
        last = report(tag)
        stop(plain)
        loop.stop_probe()
        if last:
            print("RESULT: run dir =", tag, flush=True)
            return 0
        print("  [startup flake, retrying]", flush=True)

    print("attempts exhausted", flush=True)
    return 1


if __name__ == "__main__":
    sys.exit(main())
