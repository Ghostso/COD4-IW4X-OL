# 验证实验 B28

## 步骤
1. 写一个单测直接调 process_usercmd_dt，buttons=0x01
2. 断言 ps->velocity[2] > 0

## 通过判据
vz 变正

## 失败判据
vz 不变 ⇒ 确认死路径

## 成本
离线 20 分钟
