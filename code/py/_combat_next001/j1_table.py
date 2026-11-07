# -*- coding: utf-8 -*-
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from peimg import PE
pe = PE.load()
va = [
 ("Program image base","0x400000"),
 ("accepted handler (mmbook accepted)","0x632680"),
 ("  gate: cmp byte [esi+0x278],0","0x63268D"),
 ("  G2: cmp [0x76446b0],3","0x63269B"),
 ("  G3: cmp [esi+0xe360],edi(jl)","0x6326AA"),
 ("  G4: cmp [ebp+8],[esi+0x3a048]","0x6326B9"),
 ("  G5: cmp [ebp+0xc],[esi+0x3a04c]","0x6326C8"),
 ("  G6: strncmp mmbook accepted","0x6326DF"),
 ("  PASS: [esi+0x288]=1","0x63280B"),
 ("  PASS: [0x849b61c]=1","0x632827"),
 ("  listener loop + vtable+0x24","0x632824"),
 ("  bridge call 0x6293B0","0x63285A"),
 ("FAIL path: ret 0x14","0x632916"),
 ("listener broadcast (second)","0x6328A5"),
 ("bridge 0x6293B0","0x6293B0"),
 ("  gate vtable+0x5c","0x629898"),
 ("  parse address blob 0xB95C50","0x62942B"),
 ("  zero 0x150 at esp+0x18","0x629442"),
 ("  init 0xB74BC0 on esp+0x18","0x62945F"),
 ("  copy A/B.. from [esi+0x1cc..]","0x629464"),
 ("  call 0x470360 ecx=esp+0x18","0x6294AF"),
 ("battle-connect 0x470360","0x470360"),
 ("  reads [esi+0x43..0x57]","0x470471"),
 ("  call 0x7BFD70 address ctor","0x4704BE"),
 ("  error EXE_HOSTUNREACH","0x4704CA"),
 ("  store netchan +0x14..+0x28","0x470510"),
 ("  state=3 write","0x470467"),
 ("per-frame driver 0x5C2A80","0x5C2A80"),
 ("  guard [0x76446a1]","0x5C2A9B"),
 ("state machine 0x5C05F0","0x5C05F0"),
 ("  gate A cmp [esi+0x278],0","0x5C068D"),
 ("  gate B cmp [0x76446b0],3","0x5C069B"),
 ("  switch(eax-3)","0x5C0707"),
 ("  case0 getchallenge","0x5C070E"),
 ("  build getchallenge fmt","0x5C0729"),
 ("  send/post 0x675260","0x5C075A"),
 ("formatter 0x675260","0x675260"),
 ("  inner 0x6751F0","0x6751F0"),
 ("  inner 0x6750A0","0x6750A0"),
 ("  post call [0xCA8128]","0x67512B"),
 ("UDP socket create 0xC7B8F0","0xC7B8F0"),
 ("  caller 0xC5D7EF","0xC5D7EF"),
 ("netchan ptr slot 0x331C0C8","0x331C0C8"),
]
print("%-40s %-10s %-10s" % ("label","VA","fileoff"))
for label, v in va:
    a = int(v, 16)
    off = pe.va_to_off(a)
    print("%-40s %-10s %-10s" % (label, v, ("0x%X" % off) if off is not None else "-"))
