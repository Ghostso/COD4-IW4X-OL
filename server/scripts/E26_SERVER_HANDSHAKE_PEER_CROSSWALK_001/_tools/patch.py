from pathlib import Path
base=Path(r"D:\BaiduNetdiskDownload\使命召唤OL\E26_SERVER_HANDSHAKE_PEER_CROSSWALK_001")
p=base/"E26_SERVER_RECEIVE_DISPATCH_CLOSURE.md"; t=p.read_text(encoding="utf-8")
old="""0855C8  mov ebx,[ebp+8]
0855CB  movzx eax,byte [ebx+0x40F88]
0855D2  imul eax,eax,0x408
0855DF  call 0x540133            ; 帧类型/长度检查
0855F5  ... 读取 CODOL2697_PROFILE_WIRE 配置（VA 0x7B9812）
085619  movzx eax,byte [esi]     ; 首字节
08561C  sub eax,0x4A             ; 'J' = 0x4A
08561F  cmp al,1                 ; 允许 0x4A/0x4B
085623  cmp byte [esi+1],0x20    ; 次字节 ' '
08564F  movzx eax,al             ; XOR 密钥字节
085663  call 0x49C4FE            ; XOR 变换"""
new="""0855C8  mov ebx,[ebp+8]
0855CB  movzx eax,byte [ebx+0x40F88]
0855D2  imul eax,eax,0x408
0855DF  call 0x540133            ; 帧类型/长度检查
0855F5  mov [esp],0x7B9812       ; 读取 CODOL2697_PROFILE_WIRE 配置值
085601  test eax,eax
085605  je 0x485619              ; 未设置 profile -> 直接走到字节检查
085610  call 0x765718            ; strcmp(profile,"text") (0x7B9829)
085619  movzx eax,byte [esi]     ; 首字节
08561C  sub eax,0x4A             ; 'J' = 0x4A
08561F  cmp al,1                 ; 允许 0x4A/0x4B
085623  cmp byte [esi+1],0x20    ; 次字节 ' ' -> 命中则 esi=0x7B9810 (单字节 '!')
08564F  movzx eax,al             ; XOR 密钥字节
085663  call 0x49C4FE            ; XOR 变换"""
assert old in t
t=t.replace(old,new)
old2="| `.text`(VA `0x1000`,VS `0x382BF8`)"
new2="| `.text`(VA `0x1000`,VirtualSize `0x382BF8`,RawSize `0x382C00`)"
t=t.replace(old2,new2)
p.write_text(t,encoding="utf-8"); print("patched")
# regenerate manifest
import hashlib
reps=sorted(base.glob("E26_*.md"), key=lambda x:x.name)
lines=["%s  %s"%(hashlib.sha256(x.read_bytes()).hexdigest(),x.name) for x in reps]
(base/"SHA256SUMS.txt").write_text("\n".join(lines)+"\n",encoding="ascii")
man={}
for ln in (base/"SHA256SUMS.txt").read_text(encoding="ascii").splitlines():
    if ln.strip():
        h,n=ln.split("  ",1); man[n]=h
cur={x.name:hashlib.sha256(x.read_bytes()).hexdigest() for x in base.glob("E26_*.md")}
print("manifest OK:", len(man)==8 and set(man)==set(cur) and all(man[n]==cur[n] for n in man))
