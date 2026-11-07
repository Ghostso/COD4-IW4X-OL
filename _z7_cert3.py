# -*- coding: utf-8 -*-
import os, io
GR = os.path.join("CODOLServer", "lobby_server")
d = open(os.path.join(GR,"ca_append.pem"),"rb").read()
print("=== ca_append.pem ===")
print(d.decode("utf-8","replace"))
