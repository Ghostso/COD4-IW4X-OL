"""验证 frida_tcls_dir_redirect.js 的 connect 重定向是否生效。

流程：
  1. 起本地目录服务器（TCP 10009，replay 模式）。
  2. 用 frida spawn 方式启动 _test_redirect_client.py。
  3. attach 后由 Frida 注入重定向脚本。
  4. 客户端原本连 116.130.229.168:10009，应被改写成本机并被回 774 字节。

只用回环地址与本地进程，不改动任何系统网络配置。
"""
import json
import os
import subprocess
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT = os.path.dirname(HERE)
FRIDA_EXE = os.path.join(
    os.environ.get('LOCALAPPDATA', ''),
    'Programs', 'Python', 'Python311', 'Scripts', 'frida.exe')

SERVER_PY = os.path.join(HERE, 'tcls_dir_server.py')
CLIENT_PY = os.path.join(HERE, '_test_redirect_client.py')
REDIRECT_JS = os.path.join(HERE, 'frida_tcls_dir_redirect.js')


def main():
    tmp = tempfile.mkdtemp(prefix='codol_redir_test_')
    server_log = os.path.join(tmp, 'server.jsonl')
    frida_log = os.path.join(tmp, 'frida.jsonl')
    client_out = os.path.join(tmp, 'client.out')

    server = subprocess.Popen(
        ['python', SERVER_PY, '--bind', '0.0.0.0', '--port', '10009',
         '--mode', 'replay', '--log', server_log],
        cwd=PROJECT,
        stdout=open(os.path.join(tmp, 'server.out'), 'wb'),
        stderr=subprocess.STDOUT)
    time.sleep(2.0)
    if server.poll() is not None:
        print('server failed to start', file=sys.stderr)
        return 2

    try:
        # frida CLI 支持 -f <exe> 来 spawn；但 .py 不可直接 spawn。
        # 改用「先起客户端，再按 PID attach」。
        client = subprocess.Popen(
            ['python', CLIENT_PY],
            cwd=PROJECT,
            stdout=open(client_out, 'wb'),
            stderr=subprocess.STDOUT)

        # 客户端内部会先 sleep 5 秒，给它 attach 留出窗口。
        time.sleep(1.5)
        frida = subprocess.Popen(
            [FRIDA_EXE, '-p', str(client.pid), '-l', REDIRECT_JS,
             '-o', frida_log, '-q'],
            cwd=PROJECT,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT)

        client.wait(timeout=40)
        time.sleep(1.0)
        frida.terminate()
        try:
            frida.wait(timeout=8)
        except subprocess.TimeoutExpired:
            frida.kill()
    finally:
        server.terminate()
        try:
            server.wait(timeout=5)
        except subprocess.TimeoutExpired:
            server.kill()

    print('=== client output ===')
    print(open(client_out, encoding='utf-8', errors='replace').read())

    print('=== frida events ===')
    if os.path.exists(frida_log):
        with open(frida_log, encoding='utf-8', errors='replace') as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except ValueError:
                    print(line)
                    continue
                kind = rec.get('kind')
                if kind in ('redirect_installed', 'connect_rewrite',
                            'connect_pass', 'connect_result', 'send', 'recv'):
                    print(json.dumps(rec, ensure_ascii=False))

    print('=== server events ===')
    if os.path.exists(server_log):
        with open(server_log, encoding='utf-8', errors='replace') as fh:
            for line in fh:
                print(line.rstrip())
    return 0


if __name__ == '__main__':
    sys.exit(main())
