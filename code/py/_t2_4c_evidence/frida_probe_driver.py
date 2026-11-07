"""T-2.4-C Stage C driver: Frida runtime probes against a harmless process.

Attaches the installed Frida to a harmless, driver-owned Python process and runs
five isolated probes. It NEVER touches CODOL: no game process is launched,
attached, injected, read or terminated, and no game export is called.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import time
import uuid
from pathlib import Path

EVIDENCE = Path(__file__).resolve().parent

# Keep Frida's extracted runtime inside this evidence directory so nothing leaks
# into the project tree or the machine-wide temp area. Must precede "import frida".
FRIDA_TMP = EVIDENCE / "frida-tmp"
FRIDA_TMP.mkdir(parents=True, exist_ok=True)
os.environ["TEMP"] = str(FRIDA_TMP)
os.environ["TMP"] = str(FRIDA_TMP)
os.environ["TMPDIR"] = str(FRIDA_TMP)
tempfile.tempdir = str(FRIDA_TMP)

import frida  # noqa: E402

HOST = EVIDENCE / "probe_host.py"
RAW_LOG = EVIDENCE / "frida_raw.jsonl"
DRIVER_LOG = EVIDENCE / "driver.log"
HANDSHAKE = EVIDENCE / "host_handshake.json"
STOP_FILE = EVIDENCE / "host_stop.signal"
LIFECYCLE = EVIDENCE / "host_lifecycle.json"
RESULTS = EVIDENCE / "T2_4C_RESULTS.json"

MESSAGE_TIMEOUT = 8.0
HOST_MAX_SECONDS = 240.0
HOST_EXIT_GRACE = 15.0

CASE_EXIT = {"PASS": 0, "FAIL": 1, "ERROR": 2, "TIMEOUT": 124, "SKIPPED": 77}

RUN_ID = "T24C-" + time.strftime("%Y%m%dT%H%M%S") + "-" + uuid.uuid4().hex[:8]
ABSENT_EXPORT = "t24c_absent_export_" + uuid.uuid4().hex


def log(line: str) -> None:
    text = "[" + time.strftime("%Y-%m-%dT%H:%M:%S") + "] " + line
    print(text)
    with DRIVER_LOG.open("a", encoding="utf-8") as stream:
        stream.write(text + "\n")


def raw(entry: dict) -> None:
    document = dict(entry)
    document["logged_at"] = time.time()
    with RAW_LOG.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(document, ensure_ascii=False) + "\n")


def powershell() -> Path:
    system_root = Path(os.environ.get("SystemRoot", r"C:\Windows"))
    candidate = system_root / "SysWOW64" / "WindowsPowerShell" / "v1.0" / "powershell.exe"
    return candidate if candidate.is_file() else Path("powershell")


def process_facts(pid: int) -> dict:
    script = (
        "$p = Get-CimInstance Win32_Process -Filter \"ProcessId = " + str(int(pid)) + "\"; "
        "if ($null -eq $p) { Write-Output 'ABSENT' } else { "
        "Write-Output $p.ExecutablePath; Write-Output $p.CommandLine }"
    )
    result = subprocess.run(
        [str(powershell()), "-NoProfile", "-NonInteractive", "-Command", script],
        capture_output=True, text=True, encoding="utf-8", errors="replace", check=False,
    )
    lines = [line for line in result.stdout.strip().splitlines() if line.strip()]
    if not lines or lines[0].strip() == "ABSENT":
        return {"exists": False, "path": None, "command_line": None}
    return {
        "exists": True,
        "path": lines[0].strip(),
        "command_line": lines[1].strip() if len(lines) > 1 else None,
    }


def start_host():
    nonce = uuid.uuid4().hex
    STOP_FILE.unlink(missing_ok=True)
    HANDSHAKE.unlink(missing_ok=True)
    argv = [
        sys.executable, str(HOST), nonce, str(HANDSHAKE), str(STOP_FILE), str(HOST_MAX_SECONDS),
    ]
    process = subprocess.Popen(
        argv,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    record = {
        "spawned_pid": process.pid,
        "spawned_at": time.time(),
        "spawned_at_iso": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "nonce": nonce,
        "argv": argv,
    }
    deadline = time.monotonic() + 30.0
    handshake = None
    while time.monotonic() < deadline:
        if HANDSHAKE.is_file():
            try:
                handshake = json.loads(HANDSHAKE.read_text(encoding="utf-8"))
                break
            except ValueError:
                pass
        time.sleep(0.05)
    facts = process_facts(process.pid)
    record["handshake"] = handshake
    record["handshake_matches_pid"] = bool(handshake) and handshake.get("pid") == process.pid
    record["handshake_matches_nonce"] = bool(handshake) and handshake.get("nonce") == nonce
    record["os_facts"] = facts
    record["os_path_matches"] = bool(facts.get("path")) and (
        Path(facts["path"]).resolve() == Path(sys.executable).resolve()
    )
    record["os_cmdline_has_host"] = bool(facts.get("command_line")) and (
        str(HOST) in facts["command_line"]
    )
    record["identity_ok"] = bool(
        record["handshake_matches_pid"]
        and record["handshake_matches_nonce"]
        and record["os_path_matches"]
        and record["os_cmdline_has_host"]
    )
    return process, record


def stop_host(process, record) -> dict:
    result = {"stop_file_created": False, "graceful_exit": False, "exit_code": None,
              "forced_single_pid_terminate": False, "identity_rechecked": None}
    facts = process_facts(process.pid)
    recheck = {
        "exists": facts["exists"],
        "path_matches": bool(facts.get("path")) and (
            Path(facts["path"]).resolve() == Path(sys.executable).resolve()
        ),
        "cmdline_has_host": bool(facts.get("command_line")) and (str(HOST) in facts["command_line"]),
    }
    result["identity_rechecked"] = recheck
    if not facts["exists"]:
        result["graceful_exit"] = True
        result["exit_code"] = process.poll()
        return result
    STOP_FILE.write_text("stop", encoding="utf-8")
    result["stop_file_created"] = True
    deadline = time.monotonic() + HOST_EXIT_GRACE
    while time.monotonic() < deadline and process.poll() is None:
        time.sleep(0.1)
    code = process.poll()
    if code is None:
        if recheck["path_matches"] and recheck["cmdline_has_host"]:
            # Single-PID terminate, allowed only because the identity was re-verified.
            # Deliberately NOT taskkill /T /F.
            process.terminate()
            result["forced_single_pid_terminate"] = True
            try:
                code = process.wait(timeout=10.0)
            except subprocess.TimeoutExpired:
                code = None
        else:
            result["refused_to_terminate"] = True
    result["exit_code"] = code
    result["graceful_exit"] = (not result["forced_single_pid_terminate"]) and (code is not None)
    return result


def payloads(messages):
    out = []
    for message in messages:
        if isinstance(message, dict):
            out.append(message.get("payload", message))
    return out


def errors(messages):
    return [m for m in messages if isinstance(m, dict) and m.get("type") == "error"]


def run_case(device, pid, name, probe_file, terminal, timeout, expected):
    case = {
        "id": name,
        "probe_file": probe_file.name,
        "expected": expected,
        "started_at": time.time(),
        "started_at_iso": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "ended_at": None,
        "ended_at_iso": None,
        "duration_s": None,
        "status": "ERROR",
        "exit_code": None,
        "messages": [],
        "frida_session": {},
        "notes": [],
    }
    source = (
        probe_file.read_text(encoding="utf-8")
        .replace("__TEST_ID__", RUN_ID)
        .replace("__ABSENT_NAME__", ABSENT_EXPORT)
    )
    session = None
    script = None
    try:
        session = device.attach(pid)
        case["frida_session"]["attach_ok"] = True
        script = session.create_script(source)
        case["frida_session"]["create_script_ok"] = True
        received = []

        def on_message(message, _data):
            raw({"case": name, "direction": "message", "payload": message})
            received.append(message)

        script.on("message", on_message)
        try:
            script.load()
            case["frida_session"]["load_ok"] = True
        except Exception as error:
            case["frida_session"]["load_ok"] = False
            case["frida_session"]["load_error"] = type(error).__name__ + ": " + str(error)
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if terminal(received):
                break
            time.sleep(0.02)
        case["messages"] = received
        case["timed_out"] = not terminal(received)
    except Exception as error:
        case["frida_session"]["exception"] = type(error).__name__ + ": " + str(error)
        case["timed_out"] = False
    finally:
        if script is not None:
            try:
                script.unload()
                case["frida_session"]["unload_ok"] = True
            except Exception as error:
                case["frida_session"]["unload_ok"] = False
                case["frida_session"]["unload_error"] = type(error).__name__ + ": " + str(error)
        if session is not None:
            try:
                session.detach()
                case["frida_session"]["detach_ok"] = True
            except Exception as error:
                case["frida_session"]["detach_ok"] = False
                case["frida_session"]["detach_error"] = type(error).__name__ + ": " + str(error)
        case["ended_at"] = time.time()
        case["ended_at_iso"] = time.strftime("%Y-%m-%dT%H:%M:%S")
        case["duration_s"] = round(case["ended_at"] - case["started_at"], 3)
    return case


def classify_a(case, pid):
    found = [p for p in payloads(case["messages"]) if isinstance(p, dict) and p.get("test") == "A"]
    if case.get("timed_out"):
        return "TIMEOUT", "no probe A message within the deadline"
    if not found:
        return "ERROR", "probe A produced no message"
    payload = found[0]
    case["observed"] = payload
    version = payload.get("frida_version")
    if not isinstance(version, str) or not version:
        return "FAIL", "Frida.version was not a non-empty string"
    if payload.get("pid") != pid:
        return "FAIL", "Process.id did not match the attached PID"
    return "PASS", "native Frida " + version + " executed the probe in pid " + str(pid)


def classify_b(case):
    found = [p for p in payloads(case["messages"]) if isinstance(p, dict) and p.get("test") == "B"]
    if case.get("timed_out"):
        return "TIMEOUT", "no probe B message within the deadline"
    if not found:
        return "ERROR", "probe B produced no message"
    results = found[0].get("results")
    case["observed"] = found[0]
    if not isinstance(results, list) or not results:
        return "FAIL", "probe B returned no results"
    for entry in results:
        if entry.get("global_threw"):
            return "FAIL", "findExportByName threw for an existing export: " + str(entry)
        if entry.get("global_is_null"):
            return "FAIL", "findExportByName returned null for an existing export: " + str(entry.get("name"))
        if not entry.get("global_address"):
            return "FAIL", "findExportByName returned an empty address: " + str(entry.get("name"))
    return "PASS", "existing exports resolved to non-null addresses: " + ", ".join(
        str(entry.get("name")) for entry in results
    )


def classify_c(case):
    found = [p for p in payloads(case["messages"]) if isinstance(p, dict) and p.get("test") == "C"]
    if case.get("timed_out"):
        return "TIMEOUT", "no probe C message within the deadline"
    if not found:
        return "ERROR", "probe C produced no message"
    payload = found[0]
    case["observed"] = payload
    if payload.get("threw"):
        return "FAIL", "findExportByName threw for an absent export: " + str(payload.get("error"))
    if payload.get("status") != "loaded":
        return "FAIL", "probe C did not reach the loaded state"
    if payload.get("is_null") is not True:
        return "FAIL", "findExportByName did not return null for an absent export"
    if payload.get("address") is not None:
        return "FAIL", "absent export produced an address"
    return "PASS", "absent export " + str(payload.get("absent")) + " returned null without throwing"


def classify_d(case):
    found_errors = errors(case["messages"])
    case["observed"] = {
        "error_messages": found_errors,
        "payloads": [p for p in payloads(case["messages"]) if isinstance(p, dict)],
        "reported_result": None,
    }
    if case.get("timed_out"):
        return "TIMEOUT", "the deliberate exception was never reported within the deadline"
    if not found_errors:
        return "FAIL", "the deliberate script exception was not reported to the driver"
    for message in found_errors:
        description = json.dumps(message, ensure_ascii=False)
        if "confirmed" in description or "refused" in description:
            return "FAIL", "the exception was reported as confirmed/refused"
    return "PASS", "the deliberate script exception was reported as an error, not as a result"


def classify_e(case, host_alive_after):
    case["observed"] = {
        "timed_out": case.get("timed_out"),
        "payloads": [p for p in payloads(case["messages"]) if isinstance(p, dict)],
        "host_alive_after": host_alive_after,
    }
    if not case.get("timed_out"):
        return "FAIL", "probe E did not time out, so the timeout path was not exercised"
    session = case.get("frida_session", {})
    if not session.get("unload_ok"):
        return "FAIL", "the session could not be closed after the timeout"
    if not session.get("detach_ok"):
        return "FAIL", "the session could not be detached after the timeout"
    return "PASS", "the probe timed out after the deadline and the session was closed cleanly"


def main() -> int:
    started = time.time()
    log("run_id=" + RUN_ID)
    log("stage=C")
    log("frida_python_version=" + frida.__version__)
    log("python=" + sys.version.split()[0] + " exe=" + sys.executable)
    log("absent_export_name=" + ABSENT_EXPORT)

    environment = {
        "run_id": RUN_ID,
        "stage": "C",
        "python_version": sys.version.split()[0],
        "python_executable": sys.executable,
        "frida_python_version": frida.__version__,
        "frida_native_version": None,
        "frida_temp_dir": str(FRIDA_TMP),
        "message_timeout_s": MESSAGE_TIMEOUT,
        "host_max_seconds": HOST_MAX_SECONDS,
        "host_exit_grace_s": HOST_EXIT_GRACE,
        "absent_export_name": ABSENT_EXPORT,
    }

    device = frida.get_local_device()
    process, host_record = start_host()
    pid = process.pid
    log("host_spawned pid=" + str(pid) + " identity_ok=" + str(host_record["identity_ok"]))

    cases = []
    cleanup = None
    host_alive_after_probes = None

    if not host_record["identity_ok"]:
        log("host identity could not be confirmed; no attach performed")
        for name, probe in (("A", "probe_A.js"), ("B", "probe_B.js"), ("C", "probe_C.js"),
                            ("D", "probe_D.js"), ("E", "probe_E.js")):
            cases.append({
                "id": name, "probe_file": probe, "status": "SKIPPED", "exit_code": CASE_EXIT["SKIPPED"],
                "notes": ["host identity could not be confirmed"],
            })
    else:
        plan = [
            ("A", "probe_A.js",
             lambda received: any(isinstance(m, dict) and isinstance(m.get("payload"), dict)
                                  and m["payload"].get("test") == "A" for m in received),
             "attach, load the probe and receive a message carrying the run id"),
            ("B", "probe_B.js",
             lambda received: any(isinstance(m, dict) and isinstance(m.get("payload"), dict)
                                  and m["payload"].get("test") == "B" for m in received),
             "an existing export resolves to a non-null address"),
            ("C", "probe_C.js",
             lambda received: any(isinstance(m, dict) and isinstance(m.get("payload"), dict)
                                  and m["payload"].get("test") == "C" for m in received),
             "an absent export returns null without throwing"),
            ("D", "probe_D.js",
             lambda received: any(isinstance(m, dict) and m.get("type") == "error" for m in received),
             "a deliberate script exception is reported as an error"),
            ("E", "probe_E.js", lambda received: False,
             "the probe never answers and the driver times out"),
            ("F", "probe_F.js",
             lambda received: any(isinstance(m, dict) and isinstance(m.get("payload"), dict)
                                  and m["payload"].get("test") == "A" for m in received),
             "a contradictory result is rejected instead of reported as success"),
        ]
        for name, probe, terminal, expected in plan:
            log("case " + name + " starting")
            case = run_case(device, pid, name, EVIDENCE / probe, terminal,
                            MESSAGE_TIMEOUT, expected)
            if name == "A":
                status, note = classify_a(case, pid)
                environment["frida_native_version"] = (
                    case.get("observed", {}).get("frida_version")
                    if isinstance(case.get("observed"), dict) else None
                )
            elif name == "B":
                status, note = classify_b(case)
            elif name == "C":
                status, note = classify_c(case)
            elif name == "D":
                status, note = classify_d(case)
            elif name == "F":
                # Negative control: the probe deliberately contradicts itself, so the
                # ONLY correct outcome is that the validator rejects it.
                observed_status, observed_note = classify_a(case, pid)
                case["expected_classification"] = "FAIL"
                case["observed_classification"] = observed_status
                if observed_status == "FAIL":
                    status, note = "PASS", "negative control correctly rejected: " + observed_note
                else:
                    status, note = "FAIL", (
                        "negative control was accepted as " + observed_status + ": " + observed_note
                    )
            else:
                facts_now = process_facts(pid)
                host_alive_after_probes = facts_now["exists"]
                status, note = classify_e(case, host_alive_after_probes)
            case["status"] = status
            case["exit_code"] = CASE_EXIT[status]
            case["verdict"] = note
            log("case " + name + " -> " + status + " (" + note + ")")
            cases.append(case)

    log("cleanup starting")
    cleanup = stop_host(process, host_record)
    log("cleanup exit_code=" + str(cleanup["exit_code"]) + " graceful=" + str(cleanup["graceful_exit"]))

    finished = time.time()
    results = {
        "run_id": RUN_ID,
        "stage": "C",
        "scope": "harmless driver-owned process only; no CODOL process was launched, attached, read or terminated",
        "environment": environment,
        "host": host_record,
        "cases": cases,
        "cleanup": cleanup,
        "host_alive_after_probes": host_alive_after_probes,
        "started_at": started,
        "started_at_iso": time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(started)),
        "finished_at": finished,
        "finished_at_iso": time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(finished)),
        "duration_s": round(finished - started, 3),
        "not_verified": [
            "no CODOL process was started, attached, injected, read or terminated",
            "CODOL_GameServerSetEnabled(false) was not called",
            "the game plugin CodolGameServer.Localnet32 was not loaded or queried",
            "UDP port release and client exit were not tested",
            "success on this harmless process does not imply CODOL compatibility",
        ],
    }
    RESULTS.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    LIFECYCLE.write_text(json.dumps({
        "run_id": RUN_ID,
        "host": host_record,
        "cleanup": cleanup,
        "host_alive_after_probes": host_alive_after_probes,
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    log("results written to " + str(RESULTS))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
