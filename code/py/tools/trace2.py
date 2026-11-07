#!/usr/bin/env python3
"""重新精确追踪 0x483a50：
- [ebp-0x2c]: RSA 解密输出（key 材料）→ 传给 cipher_setup 的 key
- [ebp-0x14]: 从未写入 → cipher_setup 的输出缓冲？
- [ebp-0x130]: 256 字节 → RSA 密文输入
- [ebp-0x134]: =0x28 → outlen
- [ebp-0x138]: → stat
- [ebp-0x15c]: rsa 上下文

重新读 0x483adf 之后到 0x483b29 的完整栈与调用。
"""
import subprocess

out = subprocess.run(
    ["python", "-I", "tools/disasm_dump.py", "0x483ab0", "230"],
    capture_output=True, text=True, encoding="utf-8", errors="replace").stdout
print(out)
