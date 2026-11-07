import re, struct

# Test regex extraction on actual client command bytes:
body = b"\x0a\x01\x00\x00\x00\x00\x00\x00\x00\x13\x08\x1b\x00\x00\x00\x17\x00\x00\x00mmbook 796 AQAAAAAAAAA= 0\x00"

m_book = re.search(rb"mmbook\s+(\d+)\s+([^\s\x00]+)\s+(\d+)", body)
if m_book:
    book_a = int(m_book.group(1))
    book_token = m_book.group(2)
    book_b = int(m_book.group(3))
    sender_id = (book_a & 0xFFFFFFFF) | ((book_b & 0xFFFFFFFF) << 32)
    print(f"Extracted: A={book_a}, token={book_token}, B={book_b}")
    print(f"sender_id: {sender_id} (0x{sender_id:016X})")
    print(f"sender_id_low (A): {sender_id & 0xFFFFFFFF}")
    print(f"sender_id_high (B): {sender_id >> 32}")
else:
    print("Failed to match!")
