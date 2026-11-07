import sys, os
sys.path.insert(0, os.path.abspath(r"CODOLServer\lobby_server"))
try:
    from mklobby_response import TASK_ANSWER, TICKET_LEN, NULL_REF
    print("IMPORT OK (authoritative)")
except Exception as e:
    print("IMPORT FAILED:", e)
    TASK_ANSWER = {0: 1, 10: 11, 12: 13, 24: 25, 26: 27, 32: 57}
print("TASK_ANSWER =", TASK_ANSWER)
print("has 32 ->", TASK_ANSWER.get(32))
print("TICKET_LEN =", hex(TICKET_LEN), "NULL_REF =", hex(NULL_REF))
