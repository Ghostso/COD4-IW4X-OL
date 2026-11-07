import socket, sys

srv = ("127.0.0.1", 28960)
s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
s.bind(("127.0.0.1", 0))
s.settimeout(2.0)
lport = s.getsockname()[1]
pkt = bytearray(29)
pkt[0] = 0x0D; pkt[1] = 0x02; pkt[2] = 0x00
for i in range(3, 23):
    pkt[i] = 0xAA
pkt[23:27] = bytes([127, 0, 0, 1])
pkt[27] = lport & 0xFF
pkt[28] = (lport >> 8) & 0xFF
s.sendto(bytes(pkt), srv)
try:
    data, addr = s.recvfrom(2048)
except socket.timeout:
    print("NO_REPLY from %s localport=%d" % (srv, lport)); sys.exit(2)
print("REPLY len=%d first=0x%02x from=%s localport=%d" % (len(data), data[0], addr, lport))
ok = (len(data) == 29 and data[0] == 0x0C and bytes(data[23:29]) == bytes(pkt[23:29]))
print("NAT_ROUNDTRIP_OK" if ok else "NAT_ROUNDTRIP_MISMATCH")
sys.exit(0 if ok else 3)
