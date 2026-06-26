import os
import subprocess
import sys
from pathlib import Path

import cocotb
import cocotb.config
from cocotb.runner import Verilator, get_runner
from cocotb.runner import Verilog, is_verilog_source


ROOT = Path(__file__).resolve().parents[2]
RTL = ROOT / "src" / "rtl"
TB = ROOT / "sim" / "tb"
TB_INCLUDE = TB / "include"
BUILD = ROOT / "sim" / "build"
CONDA_PREFIX = Path(os.environ.get("CONDA_PREFIX", ""))
VSDEVCMD_CANDIDATES = [
    Path("C:/Program Files/Microsoft Visual Studio/2022/Community/Common7/Tools/VsDevCmd.bat"),
    Path("C:/Program Files/Microsoft Visual Studio/2022/Enterprise/Common7/Tools/VsDevCmd.bat"),
    Path("C:/Program Files/Microsoft Visual Studio/2022/BuildTools/Common7/Tools/VsDevCmd.bat"),
]
VSDEVCMD = next((path for path in VSDEVCMD_CANDIDATES if path.exists()), None)
CXX_CANDIDATES = []
MSYS_BIN = None
MINGW_BIN = None
MAKE_SHELL = None
AR = None
if CONDA_PREFIX:
    MSYS_BIN = CONDA_PREFIX / "Library" / "usr" / "bin"
    MINGW_BIN = CONDA_PREFIX / "Library" / "mingw-w64" / "bin"
    MAKE_SHELL = MSYS_BIN / "sh.exe"
    AR = MINGW_BIN / "ar.exe"
    CXX_CANDIDATES.extend([
        CONDA_PREFIX / "Library" / "bin" / "clang++.exe",
        MINGW_BIN / "g++.exe",
    ])
CXX_CANDIDATES.append(Path("C:/intelFPGA/20.1/modelsim_ase/gcc-4.2.1-mingw32vc12/bin/g++.exe"))
CXX = next((path for path in CXX_CANDIDATES if path.exists()), None)
if CXX is not None:
    os.environ["PATH"] = str(CXX.parent) + os.pathsep + os.environ.get("PATH", "")
for tool_dir in (MSYS_BIN, MINGW_BIN):
    if tool_dir is not None and tool_dir.exists():
        os.environ["PATH"] = str(tool_dir) + os.pathsep + os.environ.get("PATH", "")


def short_windows_path(path):
    if os.name != "nt" or path is None:
        return path
    try:
        result = subprocess.check_output(
            ["cmd", "/c", f'for %I in ("{path}") do @echo %~sI'],
            text=True,
        ).strip()
    except subprocess.SubprocessError:
        return path
    return result.strip('"') if result else str(path)


VSDEVCMD_SHORT = short_windows_path(VSDEVCMD)

if CONDA_PREFIX:
    conda_bin = CONDA_PREFIX / "Library" / "bin"
    verilator_script = conda_bin / "verilator"
    os.environ["PATH"] = str(conda_bin) + os.pathsep + os.environ.get("PATH", "")

    if verilator_script.exists():
        def _use_conda_verilator(self):
            self.executable = str(verilator_script)

        Verilator._simulator_in_path_build_only = _use_conda_verilator

if os.name == "nt":
    os.environ["PATH"] = cocotb.config.libs_dir + os.pathsep + os.environ.get("PATH", "")

    def _windows_build_command(self):
        self._simulator_in_path_build_only()

        for source in self.sources:
            if not is_verilog_source(source):
                raise ValueError(f"Verilator only supports Verilog sources: {source!r}")

        verilator_cpp = str(
            Path(cocotb.__file__).parent
            / "share"
            / "lib"
            / "verilator"
            / "verilator.cpp"
        )

        cmd = [
            "perl",
            self.executable,
            "-cc",
            "--exe",
            "-Mdir",
            str(self.build_dir),
            "-DCOCOTB_SIM=1",
            "--top-module",
            self.hdl_toplevel,
            "--vpi",
            "--public-flat-rw",
            "--prefix",
            "Vtop",
            "-o",
            self.hdl_toplevel,
            "-LDFLAGS",
            f"-L{cocotb.config.libs_dir}",
            "-LDFLAGS",
            "-lcocotbvpi_verilator",
        ]
        if self.waves:
            cmd.append("--trace")
        cmd += [arg for arg in self.build_args if type(arg) in (str, Verilog)]
        cmd += self._get_define_options(self.defines)
        cmd += self._get_include_options(self.includes)
        cmd += self._get_parameter_options(self.parameters)
        cmd += [verilator_cpp]
        cmd += [str(source) for source in self.sources if is_verilog_source(source)]
        cmd += [str(source) for source in self.verilog_sources]

        if CXX is not None:
            cxx_path = str(CXX).replace("\\", "/")
            cxx = (
                f"{cxx_path} --target=x86_64-w64-windows-gnu"
                if CXX.name.lower().startswith("clang++")
                else cxx_path
            )
        else:
            cxx = "cl"
        python3 = sys.executable.replace("\\", "/")
        verilator_root = str(CONDA_PREFIX / "Library").replace("\\", "/") if CONDA_PREFIX else None
        make_shell = str(MAKE_SHELL).replace("\\", "/") if MAKE_SHELL is not None and MAKE_SHELL.exists() else None
        ar = str(AR).replace("\\", "/") if AR is not None and AR.exists() else None
        make_cmd = [
            "make",
            "-C",
            str(self.build_dir),
            "-f",
            "Vtop.mk",
            f"VM_TRACE={int(self.waves)}",
            f"PYTHON3={python3}",
            f"CXX={cxx}",
            f"LINK={cxx}",
        ]
        if verilator_root is not None:
            make_cmd.append(f"VERILATOR_ROOT={verilator_root}")
        if make_shell is not None:
            make_cmd.append(f"SHELL={make_shell}")
        if ar is not None:
            make_cmd.append(f"AR={ar}")
        if CXX is None and VSDEVCMD is not None:
            self.build_dir.mkdir(parents=True, exist_ok=True)
            make_script = self.build_dir / "run_make.cmd"
            make_script.write_text(
                "\n".join([
                    "@echo off",
                    f'call "{VSDEVCMD}" -arch=x64 -host_arch=x64 >nul',
                    f'make -C "{self.build_dir}" -f Vtop.mk VM_TRACE={int(self.waves)} CXX=cl',
                    "exit /b %ERRORLEVEL%",
                    "",
                ]),
                encoding="ascii",
            )
            make_cmd = [str(make_script)]

        return [cmd, make_cmd]

    Verilator._build_command = _windows_build_command

COMMON = [RTL / "edram_pkg.sv"]

ALL_RTL = [
    RTL / "edram_pkg.sv",
    RTL / "uart_baud_gen.sv",
    RTL / "uart_rx.sv",
    RTL / "uart_tx.sv",
    RTL / "uart_frame_parser.sv",
    RTL / "uart_resp_encoder.sv",
    RTL / "edram_ctrl_fsm.sv",
    RTL / "cmd_dispatcher.sv",
    RTL / "edram_pl_top.sv",
]


def source_list(paths):
    return [str(path) for path in paths]


def run_one(top, module, sources, parameters=None):
    build_dir = BUILD / top
    runner = get_runner("verilator")
    runner.build(
        sources=source_list(sources),
        hdl_toplevel=top,
        build_dir=str(build_dir),
        parameters=parameters or {},
        always=True,
        clean=True,
        build_args=(
            [
                "--timing",
                "-CFLAGS",
                "-std=gnu++17",
                "-CFLAGS",
                f"-I{str(TB_INCLUDE).replace(os.sep, '/')}",
            ]
            if CXX is not None or os.name != "nt"
            else ["--timing", "--compiler", "msvc"]
        ),
        timescale=("1ns", "1ps"),
    )
    runner.test(
        hdl_toplevel=top,
        test_module=module,
        build_dir=str(build_dir),
        test_dir=str(TB),
        extra_env={
            "PYTHONPATH": str(TB) + os.pathsep + os.environ.get("PYTHONPATH", ""),
        },
        timescale=("1ns", "1ps"),
    )


def main():
    run_one(
        "uart_frame_parser",
        "test_uart_frame_parser",
        COMMON + [RTL / "uart_frame_parser.sv"],
    )
    run_one(
        "uart_resp_encoder",
        "test_uart_resp_encoder",
        COMMON + [RTL / "uart_resp_encoder.sv"],
    )
    run_one(
        "cmd_dispatcher",
        "test_cmd_dispatcher",
        COMMON + [RTL / "cmd_dispatcher.sv"],
    )
    timing_params = {
        "T_LOAD_SETUP_CYCLES": 1,
        "T_LOAD_PULSE_CYCLES": 1,
        "T_LOAD_RECOVER_CYCLES": 1,
        "T_WWL_SETUP_CYCLES": 1,
        "T_WWL_PULSE_CYCLES": 1,
        "T_WWL_RECOVER_CYCLES": 1,
        "T_READ_SETUP_CYCLES": 1,
        "T_RWL_PULSE_CYCLES": 2,
        "T_READ_SAMPLE_CYCLES": 2,
        "T_READ_RECOVER_CYCLES": 1,
        "CTRL_TIMEOUT_CYCLES": 200,
        "P_SYNC_STAGES": 1,
    }
    run_one(
        "edram_ctrl_fsm",
        "test_edram_ctrl_fsm",
        COMMON + [RTL / "edram_ctrl_fsm.sv"],
        timing_params,
    )
    top_params = {
        "CLK_HZ": 1_000_000,
        "UART_BAUD": 100_000,
        **timing_params,
    }
    run_one("edram_pl_top", "test_edram_pl_top", ALL_RTL, top_params)


if __name__ == "__main__":
    main()
