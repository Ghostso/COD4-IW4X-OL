#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Client for elevated_agent.py. Usage:
    python agent_client.py ping
    python agent_client.py run python -X utf8 script.py args...
"""

import json
import os
import socket
import sys

STATE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                     'logs', 'elevated_agent.json')


def send(req):
    st = json.load(open(STATE, encoding='utf-8'))
    req['token'] = st['token']
    s = socket.create_connection(('127.0.0.1', int(st['port'])), timeout=600)
    s.sendall((json.dumps(req) + '\n').encode('utf-8'))
    data = b''
    while not data.endswith(b'\n'):
        chunk = s.recv(65536)
        if not chunk:
            break
        data += chunk
    s.close()
    return json.loads(data.decode('utf-8'))


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 1
    if sys.argv[1] == 'ping':
        r = send({'action': 'ping'})
    elif sys.argv[1] == 'run' and len(sys.argv) >= 3:
        r = send({'action': 'run', 'argv': sys.argv[2:],
                  'cwd': os.getcwd(), 'timeout': 1800})
    else:
        print(__doc__)
        return 1
    print(json.dumps(r, ensure_ascii=False, indent=2))
    return 0 if r.get('ok') and r.get('rc', 0) == 0 else 1


if __name__ == '__main__':
    sys.exit(main())
