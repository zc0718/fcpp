#!/usr/bin/env python3
import argparse
import os
import re
import shutil
import subprocess
import sys
import tempfile

# 白名单正则：所有进入 OS 命令的 CLI/配置值必须先通过校验。
# （argv 列表无 shell + 白名单校验，防命令注入；同时覆盖 LLM 生成参数的沙箱逃逸场景。）
RE_LOCAL_PATH  = re.compile(r"^[A-Za-z0-9_./\\:-]+$")
RE_REMOTE_PATH = re.compile(r"^/[A-Za-z0-9._/-]+$")
RE_SSH_HOST    = re.compile(r"^[A-Za-z0-9_.-]+@[A-Za-z0-9_.-]+$")
RE_HEX_ADDR    = re.compile(r"^0x[0-9A-Fa-f]{1,16}$")
RE_CFG_PATH    = re.compile(r"^[A-Za-z0-9_./-]+$")
RE_PROBE       = re.compile(r"^[A-Za-z0-9:._-]{1,64}$")
RE_DEVICE      = re.compile(r"^[A-Za-z0-9]{1,32}$")
RE_SPEED       = re.compile(r"^\d{1,6}$")


def _reject(label, value):
    print(f"[ERROR] 非法参数 {label}: {value!r}（白名单校验失败，已拒绝执行）")
    sys.exit(2)


def run(cmd):
    print(">>", " ".join(cmd))
    subprocess.run(cmd, check=True)


def require_tool(tool_name):
    if shutil.which(tool_name) is None:
        print(f"未找到命令: {tool_name}，请先安装后再试")
        sys.exit(1)


def _deploy_adb(args):
    binary, remote = args.binary, args.remote
    if not RE_LOCAL_PATH.fullmatch(binary):
        _reject("--binary", binary)
    if not RE_REMOTE_PATH.fullmatch(remote):
        _reject("--remote", remote)
    run(["adb", "devices"])
    run(["adb", "push", binary, remote])
    run(["adb", "shell", "chmod", "+x", remote])
    if args.run:
        run(["adb", "shell", remote])


def _deploy_ssh(args):
    if not args.host:
        print("ssh 模式需要 --host，例如 root@192.168.77.2")
        sys.exit(1)
    binary, host, remote = args.binary, args.host, args.remote
    if not RE_LOCAL_PATH.fullmatch(binary):
        _reject("--binary", binary)
    if not RE_SSH_HOST.fullmatch(host):
        _reject("--host", host)
    if not RE_REMOTE_PATH.fullmatch(remote):
        _reject("--remote", remote)
    run(["scp", binary, f"{host}:{remote}"])
    run(["ssh", host, "chmod", "+x", remote])
    if args.run:
        run(["ssh", host, remote])


def _flash_openocd(args):
    if not args.target:
        print("openocd 模式需要 --target，例如 target/stm32f4x.cfg")
        sys.exit(1)
    require_tool("openocd")

    binary, addr, interface, target = args.binary, args.addr, args.interface, args.target
    if not RE_LOCAL_PATH.fullmatch(binary):
        _reject("--binary", binary)
    if not RE_HEX_ADDR.fullmatch(addr):
        _reject("--addr", addr)
    if not RE_CFG_PATH.fullmatch(interface):
        _reject("--interface", interface)
    if not RE_CFG_PATH.fullmatch(target):
        _reject("--target", target)

    verify_part = "" if args.no_verify else " verify"
    ext = os.path.splitext(binary)[1].lower()
    if ext in (".bin", ".img"):
        program_cmd = f"program {binary} {addr}{verify_part} reset exit"
    else:
        # ELF/HEX 由 openocd 根据文件元信息处理地址
        program_cmd = f"program {binary}{verify_part} reset exit"

    run([
        "openocd",
        "-f", interface,
        "-f", target,
        "-c", f"transport select {args.transport}",
        "-c", "init",
        "-c", "halt",
        "-c", program_cmd,
    ])


def _flash_pyocd(args):
    if not args.target:
        print("pyocd 模式需要 --target，例如 stm32f407vg")
        sys.exit(1)
    require_tool("pyocd")

    binary, target = args.binary, args.target
    if not RE_LOCAL_PATH.fullmatch(binary):
        _reject("--binary", binary)
    if not RE_CFG_PATH.fullmatch(target):
        _reject("--target", target)

    # J-Link CE + pyocd 在 non_interactive=true 时可能出现 open(serial) 失败。
    cmd = [sys.executable, "-m", "pyocd", "flash", binary, "-t", target,
           "-O", "jlink.non_interactive=false"]
    if args.probe:
        probe = args.probe
        if not RE_PROBE.fullmatch(probe):
            _reject("--probe", probe)
        cmd.extend(["-u", probe])
    ext = os.path.splitext(binary)[1].lower()
    if ext in (".bin", ".img"):
        if not RE_HEX_ADDR.fullmatch(args.addr):
            _reject("--addr", args.addr)
        cmd.extend(["-a", args.addr])
    if args.no_verify:
        cmd.append("--no-verify")
    run(cmd)


def _flash_jlink(args):
    if not args.device:
        print("jlink 模式需要 --device，例如 BAT32G157GK64FB")
        sys.exit(1)

    jlink_exe = shutil.which("JLinkExe")
    if jlink_exe is None:
        print("未找到命令: JLinkExe，请先安装 SEGGER J-Link 软件包")
        sys.exit(1)

    binary, device = args.binary, args.device
    if not RE_LOCAL_PATH.fullmatch(binary):
        _reject("--binary", binary)
    if not RE_DEVICE.fullmatch(device):
        _reject("--device", device)
    speed = str(args.speed)
    if not RE_SPEED.fullmatch(speed):
        _reject("--speed", speed)

    ext = os.path.splitext(binary)[1].lower()
    jlink_binary_path = binary
    temp_bin_path = None

    # J-Link Commander does not recognize custom extensions like .img,
    # even with an explicit address. Convert to a temporary .bin path.
    if ext == ".img":
        with tempfile.NamedTemporaryFile(suffix=".bin", delete=False) as f_bin:
            temp_bin_path = f_bin.name
        shutil.copyfile(binary, temp_bin_path)
        jlink_binary_path = temp_bin_path

    if ext in (".bin", ".img"):
        if not RE_HEX_ADDR.fullmatch(args.addr):
            _reject("--addr", args.addr)
        load_cmd = f"loadfile {jlink_binary_path} {args.addr}"
        verify_cmd = f"verifybin {jlink_binary_path} {args.addr}"
    else:
        # HEX/ELF/AXF 使用文件内地址信息。
        # J-Link 的 loadfile 已包含下载后校验，无需额外 verify 命令。
        load_cmd = f"loadfile {binary}"
        verify_cmd = None

    script_lines = [
        "r",
        "h",
        load_cmd,
    ]
    if (not args.no_verify) and verify_cmd:
        script_lines.append(verify_cmd)
    script_lines.append("r")
    if args.run:
        script_lines.append("g")
    script_lines.append("q")

    with tempfile.NamedTemporaryFile(mode="w", suffix=".jlink", delete=False) as f:
        script_path = f.name
        f.write("\n".join(script_lines) + "\n")

    try:
        cmd = [
            jlink_exe,
            "-device", device,
            "-if", args.transport.upper(),
            "-speed", speed,
            "-CommanderScript", script_path,
            "-ExitOnError", "1",
        ]
        if args.probe:
            probe = args.probe
            if not RE_PROBE.fullmatch(probe):
                _reject("--probe", probe)
            if probe.startswith("jlink:"):
                probe = probe.split(":", 1)[1]
            cmd.extend(["-SelectEmuBySN", probe])
        run(cmd)
    finally:
        try:
            os.remove(script_path)
        except OSError:
            pass
        if temp_bin_path:
            try:
                os.remove(temp_bin_path)
            except OSError:
                pass


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--binary", required=True, help="本地二进制/ELF路径")
    p.add_argument("--remote", required=True, help="板端目标绝对路径，如 /tmp/main")
    p.add_argument("--mode", choices=["adb", "ssh", "openocd", "pyocd", "jlink"], required=True)
    p.add_argument("--host", help="ssh 目标地址，如 root@192.168.77.2")
    p.add_argument("--run", action="store_true", help="传输后立即执行")
    p.add_argument("--addr", default="0x08000000", help="MCU 烧录起始地址（.bin 常用）")
    p.add_argument("--interface", default="interface/stlink.cfg", help="openocd 接口配置")
    p.add_argument("--target", help="openocd target cfg（openocd 模式必填）或 pyocd target name")
    p.add_argument("--transport", choices=["swd", "jtag"], default="swd", help="openocd 传输协议（默认 swd）")
    p.add_argument("--probe", help="pyocd 探针ID（如 69613170 或 jlink:69613170）")
    p.add_argument("--device", help="J-Link 目标器件名（jlink 模式必填），如 BAT32G157GK64FB")
    p.add_argument("--speed", default="4000", help="J-Link 接口速度(kHz)，默认 4000")
    p.add_argument("--no-verify", action="store_true", help="MCU 烧录后不做 verify")
    args = p.parse_args()

    if not os.path.isfile(args.binary):
        print(f"二进制不存在: {args.binary}")
        sys.exit(1)

    # 各模式函数内部会先做白名单校验再执行 OS 命令（无 shell）。
    if args.mode == "adb":
        _deploy_adb(args)
    elif args.mode == "ssh":
        _deploy_ssh(args)
    elif args.mode == "openocd":
        _flash_openocd(args)
    elif args.mode == "pyocd":
        _flash_pyocd(args)
    else:
        _flash_jlink(args)


if __name__ == "__main__":
    main()
