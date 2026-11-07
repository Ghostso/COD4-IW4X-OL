import sys, os
sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\REF_LOBBY_KIT")
from codol_crypto import Buf
b = Buf(use_types=True)
b.blob(b"hello")
print(b.data().hex(" "))
