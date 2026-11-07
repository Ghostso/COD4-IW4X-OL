import json, socket, os

STATE = os.path.join('CODOLServer', 'logs', 'elevated_agent.json')
st = json.load(open(STATE, encoding='utf-8'))
req = {
    'token': st['token'],
    'action': 'run',
    'argv': ['python', '-X', 'utf8',
             r'CODOL-LOBBY-FULL-LIFECYCLE-REPAIR-056\TOOLS\hunt_nuked_key.py',
             r'E:\codol_nuked_hunt2', '280', '10'],
    'cwd': os.getcwd(),
    'timeout': 360,
}
s = socket.create_connection(('127.0.0.1', int(st['port'])), timeout=380)
s.sendall((json.dumps(req) + '\n').encode('utf-8'))
data = b''
while not data.endswith(b'\n'):
    chunk = s.recv(65536)
    if not chunk:
        break
    data += chunk
s.close()
print(data.decode('utf-8', errors='replace'))
