#!/usr/bin/env python3
"""把 markdown 里 ## 五、/## 六、/## 七、 之后的编号顺延（插入新节后使用）。
用法: renumber_sections.py <file> <start_num> [headings_that_already_exist...]
只做一件事：把 '## <中文数字>、' 形式的标题按出现顺序重新编号。
"""
import re, sys, io

CN = "一二三四五六七八九十"
def cn(n):
    if n <= 10: return CN[n-1]
    if n < 20: return "十" + CN[n-11]
    return CN[n//10-1] + "十" + (CN[n%10-1] if n % 10 else "")

path = sys.argv[1]
s = io.open(path, encoding="utf-8").read()
pat = re.compile(r"^## ([一二三四五六七八九十]+)、", re.M)
idx = [0]
def repl(m):
    idx[0] += 1
    return "## %s、" % cn(idx[0])
s2 = pat.sub(repl, s)
io.open(path, "w", encoding="utf-8", newline="").write(s2)
print("renumbered %d sections" % idx[0])
