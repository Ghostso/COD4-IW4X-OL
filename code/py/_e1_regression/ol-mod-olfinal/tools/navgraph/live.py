"""Optional read-only log adapter. Python 3.10+, standard library only."""
import argparse
import json
import re
import secrets
import threading
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

HERE = Path(__file__).resolve().parent
PLAYER = re.compile(r'p(?P<slot>\d+):state=(?P<state>\d+):ps=(?P<x>-?\d+),(?P<y>-?\d+),(?P<z>-?\d+):ent=')
STAMP = re.compile(r'ACTORROUTE serverTime=(\d+)')


class Feed:
    def __init__(self, config):
        self.config = config
        self.latest = None
        self.lock = threading.Lock()

    def accept(self, line):
        stamp = STAMP.search(line)
        if not stamp:
            return
        for match in PLAYER.finditer(line):
            if int(match['slot']) != self.config['slot']:
                continue
            foot = [int(match[k]) for k in ('x', 'y', 'z')]
            with self.lock:
                self.latest = dict(foot=foot, p=[foot[0], foot[1], foot[2] + self.config['probeOffset']],
                                   serverTime=int(stamp[1]), state=int(match['state']), received=time.monotonic())

    def snapshot(self):
        with self.lock:
            result = dict(self.latest) if self.latest else None
        if result is None:
            return dict(fresh=False, reason='Waiting for new ACTORROUTE diagnostics in the selected log.')
        age = time.monotonic() - result.pop('received')
        low_x, high_x, low_y, high_y = self.config['bounds']
        result.update(ageSeconds=round(age, 2), fresh=age < self.config['freshSeconds'] and result['state'] == 2,
                      inRoom=low_x <= result['foot'][0] <= high_x and low_y <= result['foot'][1] <= high_y)
        return result

    def tail(self, path):
        while True:
            try:
                with path.open(encoding='utf-8', errors='replace') as source:
                    source.seek(0, 2)
                    partial = ''
                    while True:
                        if path.stat().st_size < source.tell():
                            break
                        chunk = source.readline()
                        if not chunk:
                            time.sleep(.1)
                            continue
                        partial += chunk
                        if partial.endswith('\n'):
                            self.accept(partial)
                            partial = ''
            except OSError:
                time.sleep(1)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--log', type=Path, help='Server log; omitted opens a file picker.')
    parser.add_argument('--config', type=Path, default=HERE / 'live-config.json')
    parser.add_argument('--open', action='store_true', help='Open the default browser.')
    parser.add_argument('--offline', action='store_true', help='Serve the editor without a game or log.')
    args = parser.parse_args()
    if not args.log and not args.offline:
        try:
            from tkinter import Tk, filedialog
            root = Tk()
            root.withdraw()
            selected = filedialog.askopenfilename(title='Select CodolGameServer.log', filetypes=[('Server logs', '*.log'), ('All files', '*')])
            root.destroy()
        except ImportError:
            parser.error('File picker unavailable. Supply --log with your server log path.')
        if not selected:
            return
        args.log = Path(selected)
    if args.log and not args.log.is_file():
        parser.error('The selected log file does not exist.')
    config = json.loads(args.config.read_text(encoding='utf-8'))
    feed = Feed(config)
    token = secrets.token_urlsafe(24)

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.headers.get('Host') != f'127.0.0.1:{self.server.server_port}':
                self.send_error(403)
                return
            if self.path == f'/{token}/':
                body = (HERE / 'Editor.html').read_bytes()
                kind = 'text/html; charset=utf-8'
            elif self.path == f'/{token}/position':
                body = json.dumps(feed.snapshot()).encode()
                kind = 'application/json'
            else:
                self.send_error(404)
                return
            self.send_response(200)
            self.send_header('Content-Type', kind)
            self.send_header('Cache-Control', 'no-store')
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *_):
            pass

    server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    url = f'http://127.0.0.1:{server.server_port}/{token}/'
    if args.log:
        threading.Thread(target=feed.tail, args=(args.log,), daemon=True).start()
    print(url, flush=True)
    print('Read-only local editor. Ctrl+C stops this helper. Save JSON before closing the browser.', flush=True)
    if args.open:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == '__main__':
    main()
