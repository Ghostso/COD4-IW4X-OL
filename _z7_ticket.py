import base64, json, os, sys
sys.path.insert(0, os.path.abspath(r"CODOLServer\lobby_server"))
from mklobby_response import TICKET_LEN, NULL_REF, client_ticket, server_ticket
ct = client_ticket()
print("client_ticket len:", len(ct), "first4:", ct[:4].hex(), "== NULL_REF_BYTES:", ct[:4] == NULL_REF.to_bytes(4,"little"))
try:
    st = server_ticket()
    print("server_ticket len:", len(st), "first4:", st[:4].hex())
except Exception as e:
    print("server_ticket():", e)
