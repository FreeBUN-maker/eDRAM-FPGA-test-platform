# FPGA-PC UART通信协议

该文档定义PC端通过UART控制FPGA进行eDRAM读写测试的指令集。

FPGA端作为slave运行。PC端发送完整的命令frame，FPGA端接收并校验完整frame后，再由内部状态机产生eDRAM侧控制时序。PC端不直接通过UART逐拍控制`LOAD`、`READ`、`EN-WWL`、`EN-RWL`等底层信号。

## UART物理层约定

- 默认串口配置：`115200-8-N-1`
    - 波特率：115200
    - 数据位：8 bit
    - 校验位：无
    - 停止位：1 bit
- UART传输单位为byte。本文中的一个字段若无特别说明，均为1 byte。
- 多byte数值后续若需要扩展，默认使用little-endian。本协议v1暂不使用多byte整数。

## 基本字段

| 字段 | 宽度 | 说明 |
| --- | --- | --- |
| `SOF` | 1 byte | 请求frame起始字节，固定为`0x55` |
| `SOF_R` | 1 byte | 响应frame起始字节，固定为`0xAA` |
| `LEN` | 1 byte | 从`OP`/`STATUS`开始，到payload结束的字节数，不包含`SOF`和`CHK` |
| `OP` | 1 byte | PC发送的操作码 |
| `STATUS` | 1 byte | FPGA返回的执行状态 |
| `CHK` | 1 byte | 异或校验字节 |

## Frame格式

### PC -> FPGA请求frame

```text
[SOF=0x55] [LEN] [OP] [ARGS...] [CHK]
```

其中：

```text
LEN = 1 + ARGS字节数
CHK = LEN ^ OP ^ ARGS[0] ^ ARGS[1] ^ ...
```

### FPGA -> PC响应frame

```text
[SOF_R=0xAA] [LEN] [STATUS] [OP_ECHO] [DATA...] [CHK]
```

其中：

```text
LEN = 2 + DATA字节数
CHK = LEN ^ STATUS ^ OP_ECHO ^ DATA[0] ^ DATA[1] ^ ...
```

`OP_ECHO`为本次响应对应的请求`OP`。如果FPGA无法确定请求`OP`，例如frame长度错误导致无法解析，则`OP_ECHO`置为`0x00`。

FPGA接收到错误的`SOF`时不返回响应，只丢弃字节并继续等待下一个`0x55`。

## 地址和数据映射

eDRAM阵列规模为`64 x 64`，UART协议中的地址由`ROW`和`GROUP`组成。

| 字段 | 有效范围 | 说明 |
| --- | --- | --- |
| `ROW` | `0x00`~`0x3F` | 6 bit行地址，对应`WWL`/`RWL`选择 |
| `GROUP` | `0x00`~`0x07` | 3 bit组地址，每组对应8条`WBL`/`RBL` |
| `DATA` | `0x00`~`0xFF` | 8 bit数据，对应一组`DIN[7:0]`或`P[7:0]` |

`DATA`的bit映射如下：

```text
DATA[0] -> WBL/RBL group内第0条线
DATA[1] -> WBL/RBL group内第1条线
...
DATA[7] -> WBL/RBL group内第7条线
```

例如`GROUP=3`时，`DATA[0]`对应`WBL24`或`RBL24`，`DATA[7]`对应`WBL31`或`RBL31`。

## 状态码

| 状态码 | 名称 | 说明 |
| --- | --- | --- |
| `0x00` | `ACK` | 命令成功完成 |
| `0x01` | `NACK_BAD_LEN` | `LEN`与该`OP`要求的长度不匹配 |
| `0x02` | `NACK_BAD_CHK` | `CHK`校验失败 |
| `0x03` | `NACK_BAD_OP` | 不支持的`OP` |
| `0x04` | `NACK_BAD_ARG` | 参数越界，例如`ROW > 63`或`GROUP > 7` |
| `0x05` | `NACK_BUSY` | FPGA正在执行上一条命令，暂时不能接收新事务 |
| `0x06` | `NACK_TIMEOUT` | eDRAM控制状态机执行超时 |

`STATUS=0x00`表示ACK。非零`STATUS`均表示NACK。

## 指令集

### `PING`

用于检查PC和FPGA之间的UART链路是否可用。

| 项目 | 内容 |
| --- | --- |
| `OP` | `0x00` |
| 请求payload | 无 |
| 成功响应payload | `0xA5` |

请求：

```text
[55] [01] [00] [01]
```

响应：

```text
[AA] [03] [00] [00] [A5] [A6]
```

### `WRITE_ROW`

向eDRAM写入完整一行数据。该命令是推荐的基本写入命令。

| 项目 | 内容 |
| --- | --- |
| `OP` | `0x01` |
| 请求payload | `[ROW] [D0] [D1] [D2] [D3] [D4] [D5] [D6] [D7]` |
| 成功响应payload | 无 |

`D0`~`D7`分别对应`GROUP=0`~`GROUP=7`的8 bit数据。

FPGA收到该命令后执行：

1. 使eDRAM写入控制信号进入空闲状态。
2. 使能`LOAD`。
3. 依次设置`WG=0`~`WG=7`，并输出对应的`DIN[7:0]=D0`~`D7`。
4. 设置写入行地址`A[5:0]=ROW`。
5. 使能`EN-WWL`，将一整行写入eDRAM。
6. 恢复写入控制信号为空闲状态。
7. 返回ACK。

示例：向`ROW=12`写入8组数据`00 11 22 33 44 55 66 77`。

```text
[55] [0A] [01] [0C] [00] [11] [22] [33] [44] [55] [66] [77] [07]
```

成功响应：

```text
[AA] [02] [00] [01] [03]
```

### `READ_GROUP`

读取eDRAM某一行中的一个8 bit group。

| 项目 | 内容 |
| --- | --- |
| `OP` | `0x02` |
| 请求payload | `[ROW] [GROUP]` |
| 成功响应payload | `[DATA]` |

FPGA收到该命令后执行：

1. 使eDRAM读出控制信号进入空闲状态。
2. 设置`W[5:0]=ROW`。
3. 设置`RG[2:0]=GROUP`。
4. 使能`READ`和`EN-RWL`。
5. 在读出信号稳定后采样`P[7:0]`。
6. 恢复读出控制信号为空闲状态。
7. 返回ACK和采样得到的`DATA`。

示例：读取`ROW=12`、`GROUP=3`。

```text
[55] [03] [02] [0C] [03] [0E]
```

若读出数据为`0x5A`，响应为：

```text
[AA] [03] [00] [02] [5A] [5B]
```

### `READ_ROW`

读取eDRAM某一行的完整64 bit数据。

| 项目 | 内容 |
| --- | --- |
| `OP` | `0x03` |
| 请求payload | `[ROW]` |
| 成功响应payload | `[D0] [D1] [D2] [D3] [D4] [D5] [D6] [D7]` |

FPGA收到该命令后依次执行8次group读取：

```text
GROUP = 0, 1, 2, 3, 4, 5, 6, 7
```

返回payload中的`D0`~`D7`分别对应`GROUP=0`~`GROUP=7`。

示例：读取`ROW=12`。

```text
[55] [02] [03] [0C] [0D]
```

### `RESET`

使UART协议解析器和eDRAM控制信号回到初始空闲状态。

| 项目 | 内容 |
| --- | --- |
| `OP` | `0x04` |
| 请求payload | 无 |
| 成功响应payload | 无 |

空闲状态定义：

| 信号 | 空闲值 |
| --- | --- |
| `LOAD` | `1` |
| `READ` | `1` |
| `EN-WWL` | `1` |
| `EN-RWL` | `1` |
| `WG[2:0]` | `0` |
| `RG[2:0]` | `0` |
| `DIN[7:0]` | `0` |
| `A[5:0]` | `0` |
| `W[5:0]` | `0` |

请求：

```text
[55] [01] [04] [05]
```

### `STATUS`

读取FPGA控制器状态。

| 项目 | 内容 |
| --- | --- |
| `OP` | `0x05` |
| 请求payload | 无 |
| 成功响应payload | `[STATE] [LAST_ERR]` |

`STATE` bit定义：

| bit | 名称 | 说明 |
| --- | --- | --- |
| `0` | `BUSY` | `1`表示eDRAM控制状态机忙 |
| `7:1` | Reserved | 保留，当前固定为`0` |

`LAST_ERR`为最近一次NACK状态码。若上一次错误不存在，则为`0x00`。

请求：

```text
[55] [01] [05] [04]
```

若控制器空闲且无错误，响应为：

```text
[AA] [04] [00] [05] [00] [00] [01]
```

### 输出信号snapshot payload

`READ_OUTPUTS`和`READ_OUTPUT_TRACE`使用同一种5 byte输出信号snapshot格式。该snapshot从FPGA顶层输出端口的驱动net采样，用于PC端检查FPGA实际正在或曾经驱动到eDRAM接口的数字信号值。

| byte | bit | 内容 |
| --- | --- | --- |
| `S0` | `0` | `LOAD_N` |
| `S0` | `1` | `READ_N` |
| `S0` | `2` | `EN_WWL_N` |
| `S0` | `3` | `EN_RWL_N` |
| `S0` | `7:4` | Reserved，固定为`0` |
| `S1` | `2:0` | `WG[2:0]` |
| `S1` | `5:3` | `RG[2:0]` |
| `S1` | `7:6` | Reserved，固定为`0` |
| `S2` | `7:0` | `DIN[7:0]` |
| `S3` | `5:0` | `A[5:0]` |
| `S3` | `7:6` | Reserved，固定为`0` |
| `S4` | `5:0` | `W[5:0]` |
| `S4` | `7:6` | Reserved，固定为`0` |

空闲状态snapshot为：

```text
[0F] [00] [00] [00] [00]
```

### `READ_OUTPUTS`

读取当前eDRAM输出端口snapshot。该命令不启动eDRAM读写事务。

| 项目 | 内容 |
| --- | --- |
| `OP` | `0x06` |
| 请求payload | 无 |
| 成功响应payload | `[S0] [S1] [S2] [S3] [S4]` |

请求：

```text
[55] [01] [06] [07]
```

若当前输出端口为空闲状态，响应为：

```text
[AA] [07] [00] [06] [0F] [00] [00] [00] [00] [0E]
```

### `READ_OUTPUT_TRACE`

读取最近一次eDRAM事务期间捕获到的输出端口trace记录。trace记录只保存控制信号处于active状态且snapshot发生变化的采样点，用于在`WRITE_ROW`完成后检查写入过程中FPGA实际驱动过的`WG`、`DIN`和行地址等信号。

| 项目 | 内容 |
| --- | --- |
| `OP` | `0x07` |
| 请求payload | `[INDEX]` |
| 成功响应payload | `[COUNT] [INDEX] [S0] [S1] [S2] [S3] [S4]` |

`COUNT`表示最近一次事务中可查询的trace记录数量，`INDEX`选择其中一条记录。若`INDEX >= COUNT`，FPGA返回`NACK_BAD_ARG`。

请求`INDEX=0`：

```text
[55] [02] [07] [00] [05]
```

示例响应表示共有9条记录，第0条snapshot为`LOAD_N=0, WG=0, DIN=0x00`：

```text
[AA] [09] [00] [07] [09] [00] [0E] [00] [00] [00] [00] [09]
```

## 错误处理规则

1. `SOF`错误：FPGA不响应，继续等待下一个`0x55`。
2. `LEN`错误：FPGA返回`NACK_BAD_LEN`。
3. `CHK`错误：FPGA返回`NACK_BAD_CHK`，且不改变eDRAM控制状态。
4. `OP`不支持：FPGA返回`NACK_BAD_OP`。
5. 参数越界：FPGA返回`NACK_BAD_ARG`。
6. 控制器忙：FPGA返回`NACK_BUSY`。
7. eDRAM控制状态机超时：FPGA返回`NACK_TIMEOUT`，并回到空闲状态。

## Python构造frame示例

```python
SOF = 0x55

def checksum(data):
    value = 0
    for byte in data:
        value ^= byte
    return value & 0xff

def build_request(op, args=()):
    body = [op, *args]
    length = len(body)
    chk = checksum([length, *body])
    return bytes([SOF, length, *body, chk])

def write_row_frame(row, data_groups):
    assert 0 <= row <= 63
    assert len(data_groups) == 8
    return build_request(0x01, [row, *data_groups])

def read_group_frame(row, group):
    assert 0 <= row <= 63
    assert 0 <= group <= 7
    return build_request(0x02, [row, group])
```

示例：

```python
frame = write_row_frame(
    row=12,
    data_groups=[0x00, 0x11, 0x22, 0x33, 0x44, 0x55, 0x66, 0x77],
)
ser.write(frame)
```

对应发送字节：

```text
55 0A 01 0C 00 11 22 33 44 55 66 77 07
```

## 后续可扩展指令

以下指令暂不放入v1基本指令集，等基础读写验证完成后再考虑：

- `WRITE_GROUP`：单独写入某个8 bit group。是否安全取决于eDRAM写入时未选中WBL的行为。
- `LOAD_GROUP` / `COMMIT_WRITE`：将PC侧写入拆成显式buffer load和row commit两个阶段，用于底层调试。
- `BURST_WRITE_ROW` / `BURST_READ_ROW`：连续写入或读取多行，提高吞吐率。
- `RAW_SIGNAL_WRITE`：直接控制底层信号，仅用于bring-up和调试，不作为正式测试路径。
