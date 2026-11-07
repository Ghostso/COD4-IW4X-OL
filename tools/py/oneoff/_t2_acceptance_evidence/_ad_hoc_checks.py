import contextlib, io, json, os, pathlib, subprocess, sys, time
sys.path.insert(0, r'F:\桌面\ol\ol-mod-olfinal\tools\runtime')
import CodolGame

results = []

# --- check 1: does subprocess.run(timeout=...) actually terminate the child? ---
marker = pathlib.Path(r'D:\BaiduNetdiskDownload\使命召唤OL\_t2_acceptance_evidence\_timeout_child_pid.txt')
marker.unlink(missing_ok=True)
child = ("import os,time,pathlib;"
         "pathlib.Path(r'" + str(marker) + "').write_text(str(os.getpid()));"
         "time.sleep(60)")
started = time.monotonic()
raised = None
try:
    subprocess.run([sys.executable, '-c', child], capture_output=True, timeout=3.0, check=False)
except subprocess.TimeoutExpired:
    raised = 'TimeoutExpired'
elapsed = time.monotonic() - started
pid = int(marker.read_text()) if marker.exists() else None
alive_after = None
if pid is not None:
    probe = subprocess.run(['tasklist','/FI',f'PID eq {pid}','/FO','CSV','/NH'], capture_output=True, text=True, errors='replace')
    alive_after = str(pid) in probe.stdout
results.append({'check':'subprocess.run timeout kills child','raised':raised,
                'elapsed_s':round(elapsed,2),'child_pid':pid,'child_still_alive':alive_after})

# --- check 2: exit-code aggregation across multiple client PIDs ---
def run_stop(pids, outcomes, terminate_returns):
    state = {'n': 0}
    def running():
        state['n'] += 1
        return list(pids) if state['n'] == 1 else []
    calls = []
    def graceful(pid, timeout=20.0):
        calls.append(pid)
        return outcomes[pid]
    def terminate(targets):
        return list(terminate_returns)
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = CodolGame.stop(None)
    return code, calls, out.getvalue(), err.getvalue()

cases = [
    ('both confirmed',            [111,222], {111:('confirmed','ok'),222:('confirmed','ok')}, [], 0),
    ('one refused, one confirmed',[111,222], {111:('refused','exit 2'),222:('confirmed','ok')}, [], 4),
    ('both refused',              [111,222], {111:('refused','e'),222:('refused','e')}, [], 4),
    ('both unavailable',          [111,222], {111:('unavailable','x'),222:('unavailable','x')}, [], 0),
    ('refused AND terminate fails',[111],     {111:('refused','exit 2')}, [111], 3),
    ('confirmed but terminate fails',[111],   {111:('confirmed','ok')}, [111], 3),
]
orig_running = CodolGame.running_pids
orig_graceful = CodolGame.request_graceful_stop
orig_terminate = CodolGame.terminate_pids
try:
    for name, pids, outcomes, term, expected in cases:
        CodolGame.running_pids = lambda p=list(pids): None  # replaced below
        state = {'n': 0}
        def make_running(p):
            s = {'n': 0}
            def r():
                s['n'] += 1
                return list(p) if s['n'] == 1 else []
            return r
        CodolGame.running_pids = make_running(pids)
        CodolGame.request_graceful_stop = (lambda oc: (lambda pid, timeout=20.0: oc[pid]))(outcomes)
        CodolGame.terminate_pids = (lambda t: (lambda targets: list(t)))(term)
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = CodolGame.stop(None)
        results.append({'check':'aggregation: '+name,'pids':pids,'expected':expected,'actual':code,
                        'match':code==expected,'stderr_has_warning':('WARNING' in err.getvalue()),
                        'stderr_has_graceful_note':('did not confirm the UDP transport release' in err.getvalue())})
finally:
    CodolGame.running_pids = orig_running
    CodolGame.request_graceful_stop = orig_graceful
    CodolGame.terminate_pids = orig_terminate

print(json.dumps(results, indent=2, ensure_ascii=False))
pathlib.Path(r'D:\BaiduNetdiskDownload\使命召唤OL\_t2_acceptance_evidence\ad_hoc_checks.json').write_text(json.dumps(results, indent=2), encoding='utf-8')