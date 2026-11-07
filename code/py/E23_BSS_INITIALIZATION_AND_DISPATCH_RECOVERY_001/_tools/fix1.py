from pathlib import Path
p=Path(r"D:\BaiduNetdiskDownload\使命召唤OL\E23_BSS_INITIALIZATION_AND_DISPATCH_RECOVERY_001\E23_EXECUTIVE_SUMMARY.md")
t=p.read_text(encoding="utf-8")
old="三个是缓冲区 Range/Advance 辅助、两个是帧缓冲读取辅助"
new="其中 0xA878A0/0xA87830/0xA85AD0 是缓冲区 Range/Advance + memcpy 辅助、0xA85640/0xA85BE0 是 thiscall 字段分派"
assert old in t
t=t.replace(old,new)
p.write_text(t,encoding="utf-8")
print("updated")
