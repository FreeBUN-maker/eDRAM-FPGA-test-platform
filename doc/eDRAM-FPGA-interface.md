# FPGA -> eDRAM (0V/3.3V)
## 写信号
- LOAD (低有效)
- WG0~WG2控制写入Group
    - 000 -> WBL0~WBL7
    001 -> WBL8~WBL15
    …
    111 -> WBL56~WBL63
- DIN0~DIN7传输写入数据
EN-WWL (低有效)
A0~A5控制写入哪一行 (WWL)
选择WBL组后打开WWL写入
> __时序控制__
> 1. 使能LOAD信号
> 2. 控制WG扫描0x000到0x111，每一个WG值稳定后输入DIN[7:0]数据，完成一整行buffer的写入
> 3. 控制EN-WWL有效，完成一整行的同时写入

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
> 1. 使能READ信号（置为0）
> 2. 输出RG、W信号完成读出位置选择
> 3. 使能EN-RWL信号进行读出
> 4. 将P0~P7上的读出信号存入FPGA上的寄存器中，供后续返回给PC

# eDRAM -> FPGA (0/3.3V)
## 读信号
- P0～P7
    - 读出一组RBL数据

# 供电口
- 5V, 3.3V, GND

