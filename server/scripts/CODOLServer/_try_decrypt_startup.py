# -*- coding: utf-8 -*-
"""Try the recovered TAS/TEA ciphers on the small startup data files."""

import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(PROJECT, 'COD OL', 'scripts'))

import tas_crypt  # noqa: E402
import tea_cfg  # noqa: E402

TARGETS = [
    os.path.join(PROJECT, 'COD OL', 'Game.dat'),
    os.path.join(PROJECT, 'COD OL', 'Tenparty.dat'),
    os.path.join(PROJECT, 'COD OL', 'components', 'tclsqmfix', 'TclsQmFix.dat'),
    os.path.join(PROJECT, 'COD OL', 'players', 'config_mp.cfg'),
]


def filetime_key(path):
    st = os.stat(path)
    ft = int(st.st_mtime * 10000000) + 116444736000000000
    return struct.pack('<II', ft & 0xFFFFFFFF, (ft >> 32) & 0xFFFFFFFF)


def score(data):
    if not data:
        return 0.0
    n = min(len(data), 1024)
    good = sum(1 for b in data[:n] if 32 <= b < 127 or b in (9, 10, 13))
    return good / n


def main():
    out = []
    for path in TARGETS:
        if not os.path.exists(path):
            continue
        data = open(path, 'rb').read()
        out.append('=' * 90)
        out.append('FILE %s size=%d' % (path, len(data)))
        candidates = [
            ('tas_default', tas_crypt.decrypt(tas_crypt.DEFAULT_KEY, data)),
            ('tas_filetime', tas_crypt.decrypt(filetime_key(path), data)),
            ('tea_1111', tea_cfg.tea_dec(data, b'1111111111111111')),
            ('tea_config', tea_cfg.tea_dec(data, b'configconfigconf')),
        ]
        for name, dec in candidates:
            out.append('  %-14s printable=%.2f head=%r' % (
                name, score(dec), dec[:48]))
        out.append('')
    text = '\n'.join(out)
    print(text)
    open(os.path.join(HERE, '_startup_dec_try.txt'), 'w', encoding='utf-8').write(text)


if __name__ == '__main__':
    main()
