# FPGA -> eDRAM (0V/3.3V)
## 写信号
- LOAD (低有效)
- WG0~WG2控制写入Group
    - 000 -> WBL0~WBL7
    001 -> WBL8~WBL15
    …
    111 -> WBL56~WBL63
- DIN0~DIN7传输写入数据
- EN-WWL (低有效)
- A0~A5控制写入哪一行 (WWL)
- 选择WBL组后打开WWL写入
> __时序控制__
> 1. 空闲时保持LOAD、EN-WWL、READ、EN-RWL均为高电平
> 2. 对WG=0x000到0x111逐组写入：先输出稳定的WG和DIN[7:0]，等待配置的setup周期
> 3. 将LOAD拉低一个配置的pulse窗口，把当前组数据写入buffer
> 4. 将LOAD拉高并等待配置的recovery周期，再切换到下一组WG/DIN
> 5. 八组buffer全部写入后，输出稳定的A[5:0]，等待配置的行地址setup周期
> 6. 将EN-WWL拉低一个配置的pulse窗口，完成整行写入；随后拉高EN-WWL并进入recovery/idle
>
> FPGA RTL采用“每组一个LOAD低脉冲”的方式，避免在WG或DIN切换过程中保持LOAD有效。

## 读 (计算) 信号
- READ (低有效)
- RG0~RG2
    - 控制读出Group
    - 000 -> RBL0~RBL7
    001 -> RBL8~RBL15
    …
    111 -> RBL56~RBL63
- EN-RWL (低有效)
- W0~W5控制读出哪一行 (RWL)
- 选择RBL组后打开RWL读出
> __时序控制__:
> 1. 空闲时保持LOAD和EN-WWL为高电平，写侧控制保持无效
> 2. 先输出稳定的W[5:0]和RG[2:0]，完成读出行和Group选择
> 3. 将READ拉低并等待配置的read setup周期
> 4. 将EN-RWL拉低，使所选RWL/RBL组进入有效读出窗口
> 5. EN-RWL有效后，等待配置的read sample周期，再把P0~P7采样到FPGA寄存器中
> 6. 如果采样点早于配置的EN-RWL pulse窗口结束，继续保持EN-RWL有效直到pulse窗口满足
> 7. 将EN-RWL拉高，再将READ拉高，等待配置的recovery周期后返回idle；采样数据供后续返回给PC

# eDRAM -> FPGA (0/3.3V)
## 读信号
- P0～P7
    - 读出一组RBL数据

# 供电口
- 5V, 3.3V, GND
