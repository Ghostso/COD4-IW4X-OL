import re, sys
root = r"D:\BaiduNetdiskDownload\使命召唤OL\CODOL_SERVER_319_20261021"

# ---------------- 1) usercmd.c : move field 4-bit ----------------
p = root + r"\src\world\usercmd.c"
lines = open(p, encoding="utf-8").read().split("\n")

i_mv = None
for i, L in enumerate(lines):
    if "uint32_t mv = mr_delta(&r, (uint32_t)((uint8_t)old.forwardmove" in L:
        i_mv = i; break
assert i_mv is not None, "mv line not found"

# nearest previous '{' line
i_brace = None
for j in range(i_mv - 1, -1, -1):
    if lines[j].strip() == "{":
        i_brace = j; break
assert i_brace is not None, "brace not found"

# closing '}' of that block = first line after i_mv whose strip == '}'
i_end = None
for j in range(i_mv, len(lines)):
    if lines[j].strip() == "}":
        i_end = j; break
assert i_end is not None, "end brace not found"

# comment block above brace: walk back from i_brace-1 over lines forming the C comment
i_cstart = None
k = i_brace - 1
if lines[k].strip() == "":
    k -= 1
j = k
while j >= 0:
    if lines[j].strip().startswith("/*"):
        i_cstart = j; break
    j -= 1

new_lines = []
new_lines.append("            /* move: CODOL \u7ebf\u683c\u5f0f\u662f**\u5355\u4e2a 4bit \u975e\u5bf9\u9f50 delta \u4f4d\u57df**\uff0c\u4e0e\u53c2\u7167 read_input")
new_lines.append("             *   \u9010\u884c\u4e00\u81f4\u3002\u8be5\u5e03\u5c40\u5df2\u5728\u771f\u5b9e\u5ba2\u6237\u7aef\u5b57\u8282\u4e0a\u9a8c\u8bc1\uff1a\u53c2\u7167\u540c\u6b21\u8fd0\u884c\u89e3\u51fa 910 \u6761")
new_lines.append("             *   \u53ef\u9760\u547d\u4ee4 + 120 \u6b21\u5f00\u706b\uff0c\u800c\u5f00\u706b\u4e8b\u4ef6\u5fc5\u9700 inputs \u975e\u7a7a\u3002")
new_lines.append("             *   \u8bed\u4e49: bit0=\u524d bit1=\u540e bit2=\u53f3 bit3=\u5de6\u3002")
new_lines.append("             *   \u2605 \u5207\u52ff\u7528 IW4X \u7684 unpack_move: \u90a3\u662f IW4X **\u79c1\u6709\u5185\u5b58\u7ed3\u6784**\u7684 2\u00d7int8,")
new_lines.append("             *     \u642c\u5230\u8fd9\u91cc\u4f1a\u8ba9 4bit\u219416bit \u9519\u4f4d\uff0c\u4f4d\u6d41\u7acb\u523b\u5931\u6b65\uff0c\u7ec8\u7ed3\u7b26\u6821\u9a8c\u5fc5\u7136\u5931\u8d25\u3002 */")
new_lines.append("            {")
new_lines.append("                uint32_t oldmove = (uint32_t)((old.forwardmove > 0 ? 1u : 0u) |")
new_lines.append("                                              (old.forwardmove < 0 ? 2u : 0u) |")
new_lines.append("                                              (old.rightmove   > 0 ? 4u : 0u) |")
new_lines.append("                                              (old.rightmove   < 0 ? 8u : 0u));")
new_lines.append("                uint32_t mv = mr_delta(&r, oldmove, first_key, 4, false) & 0xFu;")
new_lines.append("                c.forwardmove = (int8_t)((mv & 1u ? 1 : 0) - (mv & 2u ? 1 : 0));")
new_lines.append("                c.rightmove   = (int8_t)((mv & 4u ? 1 : 0) - (mv & 8u ? 1 : 0));")
new_lines.append("            }")

start = i_cstart if i_cstart is not None else i_brace
lines[start:i_end+1] = new_lines
open(p, "w", encoding="utf-8", newline="\n").write("\n".join(lines))
print("usercmd.c patched: replaced lines %d..%d" % (start, i_end))

# ---------------- 2) player.c : wish dir = +-1, not /127 ----------------
p2 = root + r"\src\world\player.c"
s2 = open(p2, encoding="utf-8").read()
old2 = "    wish_f = (float)c->forwardmove / 127.0f;\n    wish_r = (float)c->rightmove   / 127.0f;"
assert old2 in s2, "player wish block not found"
new2 = ("    /* forwardmove/rightmove \u5df2\u662f\u53c2\u7167\u8bed\u4e49\u7684\u00b11/\u4e2d\u6027\u65b9\u5411\u91cf(bit0..bit3)\uff0c\u4e0d\u662f\u6a21\u62df\u91cf\u3002 */\n"
        "    wish_f = (float)c->forwardmove;\n    wish_r = (float)c->rightmove;")
s2 = s2.replace(old2, new2, 1)
open(p2, "w", encoding="utf-8", newline="\n").write(s2)
print("player.c patched")
