import sys
sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\E26_SERVER_HANDSHAKE_PEER_CROSSWALK_001\_tools")
from peh import Img
S=r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\server2697\native\bin2697\codol_dedrun.exe"
im=Img(S)
print("Server ImageBase",hex(im.IB),"SizeOfImage",hex(im.pe.OPTIONAL_HEADER.SizeOfImage))
print("EntryPoint RVA",hex(im.pe.OPTIONAL_HEADER.AddressOfEntryPoint))
for s in im.secs: print("  ",s)
print()
import pefile
pe=pefile.PE(S)
print("=== imports with send/recv ===")
for e in getattr(pe,"DIRECTORY_ENTRY_IMPORT",[]):
    names=[(i.name or b'').decode(errors='replace') for i in e.imports]
    hit=[n for n in names if n.lower() in ('send','sendto','recv','recvfrom','wsasend','wsarecv')]
    if hit: print("  %s %s"%(e.dll.decode(),hit))
