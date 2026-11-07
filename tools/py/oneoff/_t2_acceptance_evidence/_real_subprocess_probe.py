import json, os, pathlib, sys, tempfile, time
sys.path.insert(0, r'F:\桌面\ol\ol-mod-olfinal\tools\runtime')
import CodolGame

before_temp = (os.environ.get('TEMP'), os.environ.get('TMP'), tempfile.tempdir)
before_runtime = pathlib.Path(r'F:\桌面\ol\ol-mod-olfinal', '.runtime').exists()

started = time.monotonic()
outcome, detail = CodolGame.request_graceful_stop(999999, timeout=25.0)
elapsed = time.monotonic() - started

after_temp = (os.environ.get('TEMP'), os.environ.get('TMP'), tempfile.tempdir)
after_runtime = pathlib.Path(r'F:\桌面\ol\ol-mod-olfinal', '.runtime').exists()

report = {
  'check': 'real subprocess bridge, nonexistent PID (no game, no injection)',
  'pid': 999999,
  'outcome': outcome,
  'detail_first_200': detail[:200],
  'elapsed_s': round(elapsed, 2),
  'launcher_TEMP_unchanged': before_temp == after_temp,
  'launcher_temp_before': list(before_temp),
  'launcher_temp_after': list(after_temp),
  'dot_runtime_existed_before': before_runtime,
  'dot_runtime_exists_after': after_runtime,
}
print(json.dumps(report, indent=2, ensure_ascii=False))
pathlib.Path(r'D:\BaiduNetdiskDownload\使命召唤OL\_t2_acceptance_evidence\real_subprocess_probe.json').write_text(json.dumps(report, indent=2), encoding='utf-8')