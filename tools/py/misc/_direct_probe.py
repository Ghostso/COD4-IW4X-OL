from pathlib import Path
p=Path('_direct_probe.txt')
p.write_text('ok\n',encoding='ascii')
print(p.read_text(encoding='ascii'))
