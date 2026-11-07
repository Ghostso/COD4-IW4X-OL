import struct, json
pkts=[
"75720010000800030000000b000070a10000006400180000",
"75720010000800030000000b000070a20000006400180000",
"75720010000800030000000b000070a30000006400180000",
]
for h in pkts:
    d=bytes.fromhex(h)
    print('\nraw',h,'len',len(d))
    print('  magic',d[:2], d[:2].decode('ascii','replace'))
    for name,off,fmt in [('f02',2,'<H'),('f04',4,'<H'),('f06',6,'<H'),('f08',8,'<H'),('f0a',10,'<H'),('d0c',12,'<I'),('d10',16,'<I'),('d14',20,'<I')]:
        print('  %-5s off=%2d = %s (%d)'%(name,off,hex(struct.unpack_from(fmt,d,off)[0]),struct.unpack_from(fmt,d,off)[0]))
