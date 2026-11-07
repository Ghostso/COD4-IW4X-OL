import sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
# 71/3 三种 payload（从 lobby 日志逐字抄录的前缀）
s = {
 "8061B": "10 43 72 65 61 74 65 52 6f 6f 6d 7c 24 7b 54 49 4d 45 53 54 41 4d 50 5f 4f 46 46 53 45 54 28 2d 35 29 7d 7c 31 36 37 30 31 37 38",
 "435B":  "",
}
h = bytes.fromhex(s["8061B"].replace(" ",""))
print("前缀(%d 字节):" % len(h))
print("  hex :", h.hex(" "))
print("  ascii:", h.decode("latin1"))
print()
# 结构: 10 <string>  ->  tag 0x10 = field 2, LEN 定界字符串
print("解: tag=0x%02X (field %d, wiretype %d)" % (h[0], h[0]>>3, h[0]&7))
L = h[1]
print("   长度字节=0x%02X=%d -> 字符串 %r" % (L, L, h[2:2+L].decode("latin1")))
print("   剩余:", h[2+L:].hex(" "))
