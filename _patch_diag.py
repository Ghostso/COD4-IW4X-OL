# -*- coding: utf-8 -*-
import io, sys
path = r"CODOL-Combat-Server-v0.1\src\Engine\GameWorld.cs"
with io.open(path, "r", encoding="utf-8-sig", newline="") as f:
    c = f.read()
crlf = "\r\n"

old = ("        public void IntegratePlayer(PlayerState p, double dt)" + crlf +
       "        {" + crlf +
       "            double wantX, wantY;" + crlf +
       "            ComputeMoveVelocity(p, out wantX, out wantY);")

new = ("        public void IntegratePlayer(PlayerState p, double dt)" + crlf +
       "        {" + crlf +
       "            double wantX, wantY;" + crlf +
       "            ComputeMoveVelocity(p, out wantX, out wantY);" + crlf +
       crlf +
       "            // [MOVEFIX-DIAG] 诊断日志：确认 move 位和速度是否非零" + crlf +
       "            if (p.Move != 0 || wantX != 0 || wantY != 0)" + crlf +
       "            {" + crlf +
       "                _log.Info(\"MOVE\", \"slot=\" + p.Slot + \" move=0x\" + p.Move.ToString(\"X\") +" + crlf +
       "                          \" want=\" + wantX.ToString(\"0.0\") + \",\" + wantY.ToString(\"0.0\") +" + crlf +
       "                          \" yaw=\" + p.Yaw + \" pos=\" + p.X.ToString(\"0.0\") + \",\" + p.Y.ToString(\"0.0\"));" + crlf +
       "            }")

if old not in c:
    print("ABORT: IntegratePlayer pattern not found", file=sys.stderr); sys.exit(1)
c = c.replace(old, new, 1)
with io.open(path, "w", encoding="utf-8-sig", newline="") as f:
    f.write(c)
print("OK: IntegratePlayer diag added")