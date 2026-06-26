# FPGA eDRAM测试平台
本项目用于构建基于FPGA的eDRAM测试平台，平台的基本功能定义如下：
- 该平台可以同时与PC端、eDRAM器件电路板进行连接
- 该平台可以通过串口接收PC端发来的指令，并根据指令输出eDRAM器件的控制信号；可以通过串口将eDRAM器件的读出结果发送回PC端进行结果验证
- 该平台能够根据`doc/eDRAM-interface.md`文件中定义的eDRAM接口，正确地输出控制信号来控制eDRAM进行写入、读出操作
- FPGA搭建只用开发板的PL端，降低工程复杂度

# 文件结构
- doc: 存放功能描述、使用方法等项目文档
- src: 存放rtl设计文件以及控制vivado配置的tcl脚本
- sim: 存放用于测试的代码文件
- FPGA-instruction: 存放FPGA的使用说明书