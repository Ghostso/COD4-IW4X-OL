import re
d = open(r'E:\codol_re\client_image_20261027.bin', 'rb').read()
VA = 0x400000
want = [b'connect', b'reconnect', b'disconnect', b'net_disconnect', b'net_start',
        b'map_restart', b'map', b'devmap', b'ui_startmatch', b'startmatch',
        b'partymigrate', b'party_hostmigration', b'net_connect', b'cl_connect',
        b'cl_connectraw', b'connectlocal', b'connectlobby']
for w in want:
    # exact null-terminated occurrences
    for m in re.finditer(re.escape(w) + rb'\x00', d):
        off = m.start()
        # check preceding byte null or non-printable
        if off == 0 or not (32 <= d[off-1] < 127):
            print('%08X %r' % (VA + off, w.decode()))
