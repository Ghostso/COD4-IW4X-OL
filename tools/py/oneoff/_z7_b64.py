import base64
b64 = "3q297x0oMz5JVF9qdYCLlqGst8LN2OPu+QQPGiUwO0ZRXGdyfYiTnqm0v8rV4Ov2AQwXIi04Q05ZZG96hZCbprG8x9Ld6PP+CRQfKjVAS1ZhbHeCjZijrrnEz9rl8PsGERwnMj1IU15pdH+KlaCrtsHM1+Lt+AMOGSQvOkVQW2Y="
d = base64.b64decode(b64)
print("lsg_server_ticket: b64len=%d declen=%d" % (len(b64), len(d)))
print("  first4:", d[:4].hex(), "tag_ok:", d[:4] == bytes([0xDE,0xAD,0xBD,0xEF]))
# what the parser needs: size field (0xD5A0FC) vs decoded len
print("  size field says 128 (0x80); decoded =", len(d), "match:", len(d)==128)
# client_ticket too
b642 = "3q297xEWGyAlKi80OT5DSE1SV1xhZmtwdXp/hImOk5idoqessba7wMXKz9TZ3uPo7fL3/AEGCxAVGh8kKS4zOD1CR0xRVltgZWpvdHl+g4iNkpecoaarsLW6v8TJztPY3eLn7PH2+wAFCg8UGR4jKC0yNzxBRktQVVpfZGluc3g="
d2 = base64.b64decode(b642)
print("client_ticket: declen=%d first4=%s" % (len(d2), d2[:4].hex()))
