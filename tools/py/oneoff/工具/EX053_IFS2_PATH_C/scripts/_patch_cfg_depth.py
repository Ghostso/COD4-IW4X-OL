from pathlib import Path
p = Path('scripts/_tmp_high_reuse_deep.py')
s = p.read_text(encoding='utf-8')
old = "for x in disasm(start, count=1, maxlen=64):"
new = "for x in disasm(start, maxlen=0x10000):"
assert old in s
p.write_text(s.replace(old, new), encoding='utf-8')
print('patched cfg')
