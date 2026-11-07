import subprocess
import time
import os
import json

# Kill existing processes
os.system('taskkill /F /IM python.exe 2>nul')

# Start probe server
probe = subprocess.Popen([
    'python', '-X', 'utf8',
    'CODOLServer\\lobby_server\\lobby_probe_server.py',
    '--cert-dir', 'CODOLServer\\lobby_server',
    '--bind', '127.0.0.1',
    '--port', '8443',
    '--log', 'CODOLServer\\logs\\lobby_probe.jsonl'
], cwd=r'D:\BaiduNetdiskDownload\使命召唤OL',
    stdout=open('CODOLServer\logs\probe_out.txt', 'w'),
    stderr=subprocess.STDOUT)

# Start socket server
socket_srv = subprocess.Popen([
    'python', '-X', 'utf8',
    'CODOLServer\lobby_server\lobby_socket_server.py',
    '--cert-dir', 'CODOLServer\lobby_server',
    '--bind', '127.0.0.2',
    '--port', '8444',
    '--log', 'CODOLServer\logs\lobby_socket.jsonl'
], cwd=r'D:\BaiduNetdiskDownload\使命召唤OL',
    stdout=open('CODOLServer\logs\socket_out.txt', 'w'),
    stderr=subprocess.STDOUT)

print('Servers started:', probe.pid, socket_srv.pid)
time.sleep(3)

# Check if processes are alive
print('Probe alive:', probe.poll() is None)
print('Socket alive:', socket_srv.poll() is None)

# Check logs
for log in [r'CODOLServer\logs\lobby_probe.jsonl', r'CODOLServer\logs\lobby_socket.jsonl']:
    if os.path.exists(log):
        with open(log, 'r', encoding='utf-8', errors='ignore') as f:
            lines = [json.loads(l) for l in f if l.strip()]
        print(f'=== {log} ({len(lines)} lines) ===')
        for l in lines[-5:]:
            print(l)
    else:
        print(f'{log}: NOT FOUND')

# Wait a bit more
time.sleep(2)

# Run the game test
watch = subprocess.Popen([
    'python', '-X', 'utf8',
    'CODOLServer\_mainline\_lobby_watch.py',
    '--cwd', 'run_codol_001\sandbox_ifs1_20260923',
    '--out', 'CODOLServer\_mainline\_lobby_run_fixed',
    '--seconds', '180',
    '--step', '0.5'
], cwd=r'D:\BaiduNetdiskDownload\使命召唤OL\CODOLServer\_mainline',
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE)

# Wait for completion
stdout, stderr = watch.communicate(timeout=200)
print('Watch exit code:', watch.returncode)
print('Stdout:', stdout.decode()[:2000])
print('Stderr:', stderr.decode()[:2000])

# Check verdict
verdict = subprocess.run([
    'python', '-X', 'utf8',
    'CODOLServer\_mainline\_lobby_verdict.py',
    '--log', 'CODOLServer\_mainline\_lobby_run_fixed\watch.jsonl'
], capture_output=True, text=True, timeout=30)
print('Verdict:', verdict.stdout)