## 1. RTL Structure

- [x] 1.1 Create `src/rtl` module skeletons for PL top, UART blocks, command dispatcher, response encoder, and eDRAM controller
- [x] 1.2 Define shared opcode, status code, frame length, and eDRAM timing constants in a common RTL package or localparam block
- [x] 1.3 Implement `edram_pl_top.sv` ports for PL clock/reset, UART RX/TX, and eDRAM control/data pins
- [x] 1.4 Wire top-level reset so all eDRAM output controls enter documented idle values

## 2. UART Receive and Transmit Path

- [x] 2.1 Implement `uart_baud_gen.sv` with configurable `CLK_HZ` and `UART_BAUD`
- [x] 2.2 Implement `uart_rx.sv` for `115200-8-N-1` byte reception and framing-error reporting
- [x] 2.3 Implement `uart_tx.sv` for byte serialization with ready/valid handshake
- [x] 2.4 Implement `uart_frame_parser.sv` for `SOF`, `LEN`, `OP`, `ARGS`, and XOR checksum validation
- [x] 2.5 Implement `uart_resp_encoder.sv` for ACK/NACK response frame generation with checksum

## 3. Command Dispatcher

- [x] 3.1 Implement opcode, payload length, row, and group validation before eDRAM transaction start
- [x] 3.2 Implement `PING`, `RESET`, and `STATUS` commands without starting eDRAM transactions
- [x] 3.3 Implement `WRITE_ROW` dispatch from UART payload to one eDRAM row-write micro-operation
- [x] 3.4 Implement `READ_GROUP` dispatch from UART payload to one eDRAM group-read micro-operation
- [x] 3.5 Implement `READ_ROW` as eight serialized group-read micro-operations with ordered response data
- [x] 3.6 Implement `NACK_BUSY`, `NACK_TIMEOUT`, and `LAST_ERR` update behavior

## 4. eDRAM Control FSM

- [x] 4.1 Implement eDRAM idle-state output assignment for reset, idle, error, and recovery states
- [x] 4.2 Implement per-group `LOAD` setup, active pulse, and recovery timing for all eight write groups
- [x] 4.3 Implement row commit timing with stable `A[5:0]` and active-low `EN-WWL`
- [x] 4.4 Implement group read timing with stable `W[5:0]`, `RG[2:0]`, active-low `READ`, and active-low `EN-RWL`
- [x] 4.5 Implement delayed `P[7:0]` sampling and read-data return to the dispatcher
- [x] 4.6 Implement controller timeout detection and forced idle recovery

## 5. Simulation and Verification

- [ ] 5.1 Add parser tests for valid frames, invalid `SOF`, bad checksum, bad length, bad opcode, and bad arguments
- [ ] 5.2 Add response encoder tests for ACK and NACK frame bytes and XOR checksum
- [ ] 5.3 Add dispatcher tests for `PING`, `RESET`, `STATUS`, busy handling, and timeout handling
- [ ] 5.4 Add eDRAM write timing tests that check `WG`, `DIN`, `LOAD`, `A`, and `EN-WWL` cycle order
- [ ] 5.5 Add eDRAM read timing tests that check `W`, `RG`, `READ`, `EN-RWL`, and `P[7:0]` sample timing
- [ ] 5.6 Add top-level UART command tests for `WRITE_ROW`, `READ_GROUP`, and `READ_ROW`

## 6. Vivado and Documentation

- [ ] 6.1 Add Vivado Tcl file-list updates for the new `src/rtl` modules
- [ ] 6.2 Add or update XDC placeholders for UART and eDRAM PL pins once board pin mapping is selected
- [ ] 6.3 Update `doc/eDRAM-FPGA-interface.md` to align wording with the selected per-group `LOAD` pulse and read sampling timing
- [ ] 6.4 Run available simulation or lint commands and record the exact commands and results in the implementation notes
