import json, base64, sys, os
sys.path.insert(0, os.path.abspath(r"CODOLServer\lobby_server"))
from mklobby_response import client_ticket, server_ticket
ct = client_ticket(); st = server_ticket()
print("client_ticket: len=%d first8=%s tag_ok=%s" % (len(ct), ct[:8].hex(), ct[:4] == b"\xde\xad\xbd\xef"))
print("server_ticket: len=%d first8=%s tag_ok=%s" % (len(st), st[:8].hex(), st[:4] == b"\xde\xad\xbd\xef"))
print("lsg_server_ticket(=server): first4=%s" % st[:4].hex())
