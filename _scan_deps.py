"""扫描 dist 内各文件的 DLL 依赖关系，判断 libcrypto-3.dll 被谁引用。"""
import struct
import sys
from pathlib import Path

DIST = Path(r"E:\Repositories\class-random-picker\main.dist")


def pe_imports(path):
    with open(path, "rb") as f:
        data = f.read()
    if data[:2] != b"MZ":
        return None
    pe_off = struct.unpack_from("<I", data, 0x3C)[0]
    if data[pe_off : pe_off + 4] != b"PE\x00\x00":
        return None
    nsec = struct.unpack_from("<H", data, pe_off + 6)[0]
    opt_off = pe_off + 24
    magic = struct.unpack_from("<H", data, opt_off)[0]
    if magic == 0x10B:      # PE32
        data_dirs = opt_off + 96
    elif magic == 0x20B:    # PE32+
        data_dirs = opt_off + 112
    else:
        return None
    imp_rva = struct.unpack_from("<I", data, data_dirs + 8)[0]  # DataDirectory[1] = Import
    sec_off = opt_off + struct.unpack_from("<H", data, pe_off + 20)[0]
    secs = []
    for i in range(nsec):
        s = sec_off + i * 40
        va, vsize = struct.unpack_from("<II", data, s + 12)
        raw_off, raw_size = struct.unpack_from("<II", data, s + 20)
        secs.append((va, max(vsize, raw_size), raw_off))
    def rva2off(rva):
        for va, size, raw_off in secs:
            if va <= rva < va + size:
                return raw_off + (rva - va)
        return None
    if imp_rva == 0:
        return []
    dlls = []
    off = rva2off(imp_rva)
    while off is not None:
        name_rva = struct.unpack_from("<I", data, off + 12)[0]
        if name_rva == 0:
            break
        no = rva2off(name_rva)
        end = data.index(b"\x00", no)
        dlls.append(data[no:end].decode("ascii", "replace"))
        off += 20
    return dlls


targets = sys.argv[1:]
if not targets:
    # 扫描 dist 里所有 PE 文件，找谁依赖 libcrypto / qt6network / qt6svg / qt6pdf
    for p in sorted(DIST.rglob("*")):
        if p.suffix.lower() not in (".dll", ".pyd", ".exe"):
            continue
        deps = pe_imports(p)
        if not deps:
            continue
        hits = [d for d in deps if any(k in d.lower() for k in
                ("libcrypto", "qt6network", "qt6svg", "qt6pdf"))]
        if hits:
            rel = p.relative_to(DIST)
            print(f"{rel}  ->  {', '.join(sorted(set(hits)))}")
else:
    for t in targets:
        deps = pe_imports(t)
        print(f"{t}  ->  {deps}")
