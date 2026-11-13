"""ai-happy-01 entry: emit the judged image as $MAKEFUN_OUTPUT_DIR/entry.png.

The image this entry submits lives in the repository as entry.png, next to
this file. This program validates it against the competition limits (whole
PNG, at most 1 MiB, at most 1024x1024) and copies it byte for byte to the
output directory, so the grader's two runs always produce identical bytes.

Standard library only. No network, no randomness, no clock reads.
"""

import hashlib
import os
import struct
import sys
import zlib

PNG_MAGIC = b"\x89PNG\r\n\x1a\n"
MAX_BYTES = 1_048_576
MAX_SIDE = 1024


def _die(message):
    print("error: " + message, file=sys.stderr)
    raise SystemExit(1)


def _dimensions(data):
    """Return (width, height) after checking the PNG is whole and in limits."""
    if len(data) > MAX_BYTES:
        _die("image is %d bytes, over the 1 MiB limit" % len(data))
    if data[:8] != PNG_MAGIC:
        _die("source is not a PNG (bad signature)")
    pos = 8
    seen_idat = False
    first = True
    while pos < len(data):
        if pos + 8 > len(data):
            _die("truncated PNG chunk header")
        size = struct.unpack(">I", data[pos:pos + 4])[0]
        ctype = data[pos + 4:pos + 8]
        end = pos + 8 + size + 4
        if end > len(data):
            _die("truncated PNG chunk: " + ctype.decode("latin-1"))
        body = data[pos + 8:pos + 8 + size]
        want_crc = struct.unpack(">I", data[pos + 8 + size:end])[0]
        got_crc = zlib.crc32(ctype + body) & 0xFFFFFFFF
        if want_crc != got_crc:
            _die("PNG chunk CRC mismatch: " + ctype.decode("latin-1"))
        if first:
            if ctype != b"IHDR" or size != 13:
                _die("PNG has no valid IHDR chunk first")
            first = False
        if ctype == b"IDAT":
            seen_idat = True
        if ctype == b"IEND":
            if pos + 12 != len(data):
                _die("trailing bytes after PNG IEND chunk")
            break
        pos = end
    else:
        _die("PNG has no IEND chunk")
    if not seen_idat:
        _die("PNG has no IDAT chunk")
    width, height = struct.unpack(">II", data[8 + 8:8 + 8 + 8])
    bit_depth = data[16 + 8]
    colour_type = data[16 + 9]
    if bit_depth not in (1, 2, 4, 8, 16):
        _die("PNG has an invalid bit depth: %d" % bit_depth)
    if colour_type not in (0, 2, 3, 4, 6):
        _die("PNG has an invalid colour type: %d" % colour_type)
    if width == 0 or height == 0:
        _die("image has a zero dimension")
    if width > MAX_SIDE or height > MAX_SIDE:
        _die("image is %dx%d, over the 1024x1024 limit" % (width, height))
    return width, height


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    source = os.path.join(here, "entry.png")
    out_dir = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")
    dest = os.path.join(out_dir, "entry.png")

    try:
        with open(source, "rb") as handle:
            data = handle.read()
    except OSError as exc:
        _die("cannot read %s: %s" % (source, exc))

    width, height = _dimensions(data)

    os.makedirs(out_dir, exist_ok=True)
    with open(dest, "wb") as handle:
        handle.write(data)

    with open(dest, "rb") as handle:
        written = handle.read()
    if written != data:
        _die("output verification failed: written bytes differ from source")
    digest = hashlib.sha256(written).hexdigest()

    print("wrote %s (%dx%d, %d bytes, sha256 %s)"
          % (dest, width, height, len(data), digest))


if __name__ == "__main__":
    main()
