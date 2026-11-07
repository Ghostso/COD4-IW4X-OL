# -*- coding: utf-8 -*-
import struct
import img, mem
from img import call_rel32_hits
M = mem.M

def _scan_regions(pred_byte, handler):
    hits = []
    for (s, sz, data) in M.regions:
        i = data.find(pred_byte)
        while i >= 0:
            r = handler(s, data, i)
            if r is not None:
                hits.append(r)
            i = data.find(pred_byte, i+1)
    return sorted(hits)

def dump_callers(target):
    def h(s, data, i):
        if i + 5 > len(data):
            return None
        rel = struct.unpack_from("<i", data, i+1)[0]
        if s + i + 5 + rel == target:
            return s + i
        return None
    return _scan_regions(b"\xE8", h)

def dump_dword_refs(value):
    pat = struct.pack("<I", value)
    hits = []
    for (s, sz, data) in M.regions:
        i = data.find(pat)
        while i >= 0:
            hits.append(s+i)
            i = data.find(pat, i+1)
    return sorted(hits)

def img_dword_refs(value):
    return img.dword_refs(value)
