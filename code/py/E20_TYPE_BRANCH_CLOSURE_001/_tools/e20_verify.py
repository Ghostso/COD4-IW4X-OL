import sys
sys.path.insert(0,"_tools")
from pe_helper import PE
from capstone import *
p="D:/BaiduNetdiskDownload/CODOL_2697_Launcher/runtime/game/aplib-recovered/codol2697-static-candidate.bin"

C=PE(p); md=Cs(CS_ARCH_X86,CS_MODE_32); md.detail=True
print(chr(34)+chr(34).join([chr(105),chr(109),chr(97),chr(103),chr(101),chr(98),chr(97),chr(115),chr(101)])+chr(34),hex(C.IB))
o,_=C.off(0x6A9969)
print(chr(34)+chr(34).join([chr(98),chr(114),chr(97),chr(110),chr(99),chr(104),chr(32),chr(114),chr(97),chr(119)])+chr(34),C.d[o:o+0x1A].hex(chr(32)))
for ins in md.disasm(C.d[o:o+0x1A],C.IB+0x6A9969): print(chr(37)+chr(48)+chr(54)+chr(88)+chr(32)+chr(37)+chr(115)+chr(32)+chr(37)+chr(115)+chr(37)+chr(40)+chr(105)+chr(110)+chr(115)+chr(46)+chr(97)+chr(100)+chr(100)+chr(114)+chr(101)+chr(115)+chr(115)+chr(45)+chr(67)+chr(46)+chr(73)+chr(66)+chr(44)+chr(105)+chr(110)+chr(115)+chr(46)+chr(109)+chr(110)+chr(101)+chr(109)+chr(111)+chr(110)+chr(105)+chr(99)+chr(44)+chr(105)+chr(110)+chr(115)+chr(46)+chr(111)+chr(112)+chr(95)+chr(115)+chr(116)+chr(114)+chr(41))
for a in (0x6A9978,0x6A997D):
 o,_=C.off(a); print(hex(a),chr(34)+chr(34).join([chr(114),chr(97),chr(119)])+chr(34),C.d[o:o+8].hex(chr(32)))
for a,n in ((0x6A84E0,0x120),(0x6A9720,0x100)):
 o,_=C.off(a)
 for ins in md.disasm(C.d[o:o+n],C.IB+a):
  s=ins.op_str.lower()
  print(chr(34)+chr(34).join([chr(37),chr(48),chr(54),chr(88),chr(32),chr(37),chr(115),chr(32),chr(37),chr(115)])+chr(34) % (ins.address-C.IB,ins.mnemonic,ins.op_str))