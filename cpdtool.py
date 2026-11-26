#!/usr/bin/env python3
"""
cpdtool — read and write A3101/HC16xx ".cpd" resource containers.

Format (reverse-engineered from Sega-M8-V6.0 stock firmware):

    A .cpd file is a standard ZIP archive with three signature substitutions
    and obfuscated member names:

        PK\\x03\\x04  (local file header)     ->  WQW\\x03
        PK\\x01\\x02  (central directory)     ->  WQW\\x02
        PK\\x05\\x06  (end of central dir)    ->  WQW\\x01

        member names are XOR-ed with 0xE5

    Everything else is unmodified ZIP: deflate compression, real CRC32,
    real sizes. So a .cpd round-trips through Python's zipfile once the
    substitutions are undone.

Usage:
    cpdtool.py list    <file.cpd>
    cpdtool.py extract <file.cpd> <outdir>
    cpdtool.py pack    <indir> <file.cpd>          # rebuild from a directory
    cpdtool.py tozip   <file.cpd> <file.zip>       # plain zip, for inspection
    cpdtool.py fromzip <file.zip> <file.cpd>
"""
import os
import struct
import sys
import zipfile

XOR_KEY = 0xE5

# (cpd signature, real zip signature)
SIGS = [
    (b'WQW\x03', b'PK\x03\x04'),
    (b'WQW\x02', b'PK\x01\x02'),
    (b'WQW\x01', b'PK\x05\x06'),
]


def deobf(name: bytes) -> bytes:
    return bytes(b ^ XOR_KEY for b in name)


obf = deobf  # XOR is symmetric


def _swap(data: bytes, to_zip: bool) -> bytes:
    """Swap container signatures in both directions."""
    out = bytearray(data)
    n = len(out)
    i = 0
    while i + 4 <= n:
        chunk = bytes(out[i:i + 4])
        for cpd_sig, zip_sig in SIGS:
            src, dst = (cpd_sig, zip_sig) if to_zip else (zip_sig, cpd_sig)
            if chunk == src:
                out[i:i + 4] = dst
                break
        i += 1
    return bytes(out)


def _rename_members(data: bytes, to_zip: bool) -> bytes:
    """XOR every stored filename in local headers and the central directory."""
    out = bytearray(data)
    n = len(out)

    i = 0
    while i + 30 <= n:
        if bytes(out[i:i + 4]) == b'PK\x03\x04':
            nl, el = struct.unpack_from('<HH', out, i + 26)
            s = i + 30
            out[s:s + nl] = deobf(bytes(out[s:s + nl]))
            csz = struct.unpack_from('<I', out, i + 18)[0]
            i = s + nl + el + csz
            continue
        if bytes(out[i:i + 4]) == b'PK\x01\x02':
            break
        i += 1

    # central directory
    i = 0
    while i + 46 <= n:
        if bytes(out[i:i + 4]) == b'PK\x01\x02':
            nl, el, cl = struct.unpack_from('<HHH', out, i + 28)
            s = i + 46
            out[s:s + nl] = deobf(bytes(out[s:s + nl]))
            i = s + nl + el + cl
            continue
        i += 1
    return bytes(out)


def cpd_to_zip(data: bytes) -> bytes:
    return _rename_members(_swap(data, True), True)


def zip_to_cpd(data: bytes) -> bytes:
    return _swap(_rename_members(data, False), False)


def cmd_list(path):
    raw = cpd_to_zip(open(path, 'rb').read())
    tmp = path + '.__tmp.zip'
    open(tmp, 'wb').write(raw)
    try:
        with zipfile.ZipFile(tmp) as z:
            bad = z.testzip()
            print('%-34s %9s %9s  %s' % ('NAME', 'STORED', 'SIZE', 'METHOD'))
            for info in z.infolist():
                print('%-34s %9d %9d  %s' % (
                    info.filename, info.compress_size, info.file_size,
                    'deflate' if info.compress_type == 8 else
                    'store' if info.compress_type == 0 else info.compress_type))
            print('\n%d entries, integrity: %s' % (
                len(z.infolist()), 'OK' if bad is None else 'FAILED on ' + bad))
    finally:
        os.unlink(tmp)


def cmd_extract(path, outdir):
    raw = cpd_to_zip(open(path, 'rb').read())
    tmp = path + '.__tmp.zip'
    open(tmp, 'wb').write(raw)
    try:
        os.makedirs(outdir, exist_ok=True)
        with zipfile.ZipFile(tmp) as z:
            z.extractall(outdir)
            print('extracted %d entries to %s' % (len(z.infolist()), outdir))
    finally:
        os.unlink(tmp)


def cmd_pack(indir, path):
    tmp = path + '.__tmp.zip'
    with zipfile.ZipFile(tmp, 'w', zipfile.ZIP_DEFLATED) as z:
        for root, _dirs, files in os.walk(indir):
            for f in sorted(files):
                full = os.path.join(root, f)
                rel = os.path.relpath(full, indir).replace(os.sep, '/')
                z.write(full, rel)
    try:
        open(path, 'wb').write(zip_to_cpd(open(tmp, 'rb').read()))
        print('packed %s' % path)
    finally:
        os.unlink(tmp)


def cmd_tozip(path, out):
    open(out, 'wb').write(cpd_to_zip(open(path, 'rb').read()))
    print('wrote %s' % out)


def cmd_fromzip(path, out):
    open(out, 'wb').write(zip_to_cpd(open(path, 'rb').read()))
    print('wrote %s' % out)


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        return 1
    cmd = sys.argv[1]
    if cmd == 'list':
        cmd_list(sys.argv[2])
    elif cmd == 'extract':
        cmd_extract(sys.argv[2], sys.argv[3])
    elif cmd == 'pack':
        cmd_pack(sys.argv[2], sys.argv[3])
    elif cmd == 'tozip':
        cmd_tozip(sys.argv[2], sys.argv[3])
    elif cmd == 'fromzip':
        cmd_fromzip(sys.argv[2], sys.argv[3])
    else:
        print(__doc__)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())