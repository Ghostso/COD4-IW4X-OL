#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Verify every offset claimed in SUBAGENT_QOS_KEY.md against the runtime dump."""

import os
import struct

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENGINE_BASE = 0x00994000
DUMP = os.path.join(ROOT, 'run_codol_001', 'runs',
                    'ENGINE_DUMP_20260925_114204', 'engine', 'engine_best.bin')


def main():
    d = open(DUMP, 'rb').read()

    def b(va, n):
        o = va - ENGINE_BASE
        return d[o:o + n]

    def u32(va):
        return struct.unpack('<I', b(va, 4))[0]

    checks = [
        ('qos_cs "Body" tail', 0x00E4444C, b'\x00Body\x00', b(0x00E4444C, 6)),
        ('qos_cs tableID', 0x00E44458, 0x000B02D6, u32(0x00E44458)),
        ('qos_cs slot', 0x00E4445C, 32, u32(0x00E4445C)),
        ('qos_cs 0x5172', 0x00E44460, 0x5172, u32(0x00E44460)),
        ('qos_cs hash', 0x00E44464, 0x7E40DF4B, u32(0x00E44464)),
        ('qos_cs 19', 0x00E44480, 19, u32(0x00E44480)),
        ('qos_cs 24a', 0x00E44488, 24, u32(0x00E44488)),
        ('qos_cs 24b', 0x00E4448C, 24, u32(0x00E4448C)),
        ('qos_cs str_len', 0x00E444A0, 11, u32(0x00E444A0)),
        ('qos_cs sub0', 0x00E444A8, 384, u32(0x00E444A8)),
        ('qos_cs sub3', 0x00E444B4, 840, u32(0x00E444B4)),
        ('qos_cs "qos_cs"', 0x00E444EC, b'qos_cs\x00\x00', b(0x00E444EC, 8)),
        ('QOS_CS_MAGIC "ru"', 0x00E44570, b'ru\x00\x00', b(0x00E44570, 4)),
        ('qos_ss "qos_ss"', 0x00E4042C, b'qos_ss\x00\x00', b(0x00E4042C, 8)),
        ('QOS_SS_MAGIC "su"', 0x00E404B0, b'su\x00\x00', b(0x00E404B0, 4)),
        ('qos_ss tableID', 0x00E40398, 0x000B02D6, u32(0x00E40398)),
        ('qos_ss 13a', 0x00E403C0, 13, u32(0x00E403C0)),
        ('qos_ss 15a', 0x00E403C8, 15, u32(0x00E403C8)),
        ('qos_ss str_len', 0x00E403E0, 11, u32(0x00E403E0)),
        ('qos_ss sub0', 0x00E403E8, 240, u32(0x00E403E8)),
        ('iv_seed str', 0x00D5A114, b'iv_seed\x00', b(0x00D5A114, 8)),
        ('356c4bc3 str', 0x00D5A33C, b'356c4bc3\x00', b(0x00D5A33C, 9)),
        ('server_ticket', 0x00D5A31C, b'server_ticket\x00', b(0x00D5A31C, 14)),
        ('43FC hex', 0x00D5A238, b'43FCB2AC', b(0x00D5A238, 8)),
    ]
    bad = 0
    for name, va, expect, got in checks:
        ok = (got == expect)
        if not ok:
            bad += 1
        print('%-22s VA %08X  %s  got=%s' % (
            name, va, 'OK ' if ok else 'BAD', repr(got)))
    print('')
    print('total=%d  bad=%d' % (len(checks), bad))


if __name__ == '__main__':
    main()
