## 1. Protocol Documentation

- [x] 1.1 Update `doc/FPGA-PC-UART-interface.md` with UART physical defaults and frame format
- [x] 1.2 Add command table with opcode, payload, response, and error behavior
- [x] 1.3 Add Python-side frame construction examples

## 2. RTL Parser Preparation

- [x] 2.1 Define protocol constants for SOF, opcode, status, and maximum frame length
- [x] 2.2 Implement UART request frame parser FSM
- [x] 2.3 Implement checksum validation and malformed-frame rejection

## 3. Command Execution

- [x] 3.1 Implement `WRITE_ROW` command dispatch to the eDRAM write FSM
- [x] 3.2 Implement `READ_GROUP` command dispatch and readback capture
- [x] 3.3 Implement `READ_ROW` command dispatch by scanning groups 0 through 7
- [x] 3.4 Implement `RESET`, `STATUS`, and `PING` commands

## 4. Response Path

- [x] 4.1 Implement response frame encoder
- [x] 4.2 Emit ACK responses for successful commands
- [x] 4.3 Emit NACK responses for checksum, length, opcode, argument, busy, and timeout errors

## 5. Host and Verification

- [x] 5.1 Add Python helper functions to build command frames and parse responses
- [x] 5.2 Add simulation tests for valid write/read/control frames
- [x] 5.3 Add simulation tests for bad checksum, bad length, unsupported opcode, and invalid arguments
- [x] 5.4 Verify the documented protocol examples match generated frame bytes

## Implementation Notes

- 2026-06-26: `conda run -n track4-fa python sim/tb/protocol.py` passed and validates the documented protocol example bytes.
- 2026-06-26: `conda run -n track4-fa python sim/tb/run_cocotb.py` passed with Verilator 5.048 and cocotb 1.9.2, including UART protocol valid/control/error-frame tests.
