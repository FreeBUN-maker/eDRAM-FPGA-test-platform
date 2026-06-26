import os
import subprocess
import sys


def main():
    lib_exe = os.environ.get("MSVC_LIB")
    if not lib_exe:
        raise SystemExit("MSVC_LIB is not set")

    args = sys.argv[1:]
    if not args:
        raise SystemExit("missing ar arguments")

    mode = args[0]
    if mode == "-s":
        return 0
    if mode in ("-rc", "-rcs"):
        if len(args) < 2:
            raise SystemExit("missing output archive")
        output = args[1]
        inputs = args[2:]
        subprocess.run(
            [lib_exe, "/nologo", f"/OUT:{output}", *inputs],
            check=True,
        )
        return 0

    raise SystemExit(f"unsupported ar mode: {mode}")


if __name__ == "__main__":
    raise SystemExit(main())
