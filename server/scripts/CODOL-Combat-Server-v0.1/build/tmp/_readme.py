import io
p = r"D:\BaiduNetdiskDownload\使命召唤OL\CODOL-Combat-Server-v0.1\README.md"
with io.open(p, "r", encoding="utf-8", newline="") as f:
    t = f.read()
nl = "\r\n" if "\r\n" in t else "\n"
old = "| `--run` | 启动战斗服主循环（默认） |"
new = old + nl + "| `--run --max-seconds N` | 运行 N 秒后自动退出（可重复验证启动、运行与清理） |"
assert t.count(old) == 1, t.count(old)
t = t.replace(old, new)
with io.open(p, "w", encoding="utf-8", newline="") as f:
    f.write(t)
print("README updated, newline=", repr(nl))
