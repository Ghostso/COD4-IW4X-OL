# -*- coding: utf-8 -*-
from pathlib import Path
base=Path(r"D:\BaiduNetdiskDownload\使命召唤OL\E25_HANDSHAKE_RESPONSE_SEND_PATH_001")
p=base/"E25_RESPONSE_BLOCK_FIELD_PROVENANCE.md"; t=p.read_text(encoding="utf-8")
old="""```asm
6ABA4B  call 0x4DAB40          ; 构造对象 (arg: [ebp-0x17c]+6, 0) -> eax
6ABA50  mov  ebx, eax          ; ebx = 序列化器/写入器对象
...
6ABAAA  call 0xDF6F97C         ; (ecx=ebx) 追加字段：eax=[esi+0x10], ecx=[esi+8]
6ABABB  call 0xDF6F97C         ; (ecx=ebx) 追加 8 字节：[ebp-0x38]
```"""
new="""```asm
6ABA25  push 0x1c
6ABA27  call 0x0DF9AA45         ; 分配 0x1C
6ABA2C  add esp,4
6ABA3D  mov ecx,[ebp-0x17c]     ; 长度来自 [ebp-0x17c]
6ABA43  add ecx,6
6ABA46  push 0                ; arg2 (flag)
6ABA48  push ecx              ; arg1 (initial size = [ebp-0x17c]+6)
6ABA49  mov ecx,eax
6ABA4B  call 0x0DAB40         ; <== 序列化器构造器 (RVA 0xDAB40)
6ABA50  mov ebx,eax           ; ebx = 序列化器
...
6ABAAA  call 0x0DF6F97C        ; (ecx=ebx) 追加字段：arg 来源 [esi+0x10]/[esi+8]
6ABABB  call 0x0DF6F97C        ; (ecx=ebx) 追加 8 字节：[ebp-0x38]
```

序列化器构造器 `0x0DAB40`（VA `0x4DAB40`）实测：

```asm
0DAB4B  mov cl,[ebp+0xC]        ; flag
0DAB4E  mov dword ptr [esi],0xCBBD1C
0DAB57  mov dword ptr [esi],0xCBBD24   ; <== node/serializer vtable
0DAB5D  mov dword ptr [esi+8],eax      ; 声明容量
0DAB63  mov byte ptr [esi+0x18],cl
0DAB70  push eax; call 0x0DF9AA45      ; 分配缓冲区
0DAB79  mov dword ptr [esi+0xC],eax    ; <== 字节缓冲
0DAB83  mov dword ptr [esi+0x14],eax   ; 写游标
0DAB86  mov dword ptr [esi+0x10],eax   ; 读游标
```"""
assert old in t
t=t.replace(old,new)
p.write_text(t,encoding="utf-8")
print("patched provenance")
