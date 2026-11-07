# -*- coding: utf-8 -*-
"""Try the recovered Tenio TAS cipher on players\\config_mp.cfg."""

import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(PROJECT, 'COD OL', 'scripts'))

import tas_crypt  # noqa: E402

CFG = os.path.join(PROJECT, 'COD OL', 'players', 'config_mp.cfg')


def filetime_key(path):
    st = os.stat(path)
    ft = int(st.st_mtime * 10000000) + 116444736000000000
    lo, hi = ft & 0xFFFFFFFF, (ft >> 32) & 0xFFFFFFFF
    return struct.pack('<II', lo, hi)


def main():
    data = open(CFG, 'rb').read()
    print('config size', len(data))
    keys = [
        ('default', tas_crypt.DEFAULT_KEY),
        ('cfg_filetime', filetime_key(CFG)),
        ('exe_filetime', filetime_key(os.path.join(PROJECT, 'COD OL',
                                                   'codoMP_client_shipRetail.exe'))),
        ('base_filetime', filetime_key(os.path.join(PROJECT, 'COD OL',
                                                    'codoMP_client_shipRetailBase.dll'))),
        ('tcls_filetime', filetime_key(os.path.join(PROJECT, 'COD OL', 'TCLS',
                                                    'TenProtect', 'TASLogin.exe'))),
        ('zero', b'\x00' * 8),
        ('ones', b'\x11' * 8),
    ]
    markers = [b'seta ', b'bind ', b'dwlobby', b'onlinegame', b'cl_', b'sv_']
    for name, key in keys:
        try:
            out = tas_crypt.decrypt(key, data)
        except Exception as exc:  # noqa: BLE001
            print('%-16s decrypt error %s' % (name, exc))
            continue
        printable = sum(1 for b in out[:512] if 32 <= b < 127 or b in (9, 10, 13))
        ratio = printable / max(1, min(len(out), 512))
        hits = [m.decode() for m in markers if m in out]
        print('%-16s key=%s printable=%.2f hits=%s' % (name, key.hex(), ratio, hits))
        if ratio > 0.75 or hits:
            dump = os.path.join(HERE, '_cfg_dec_%s.bin' % name)
            open(dump, 'wb').write(out)
            print('  wrote', dump)
            print('  head', repr(out[:256]))


if __name__ == '__main__':
    main()
