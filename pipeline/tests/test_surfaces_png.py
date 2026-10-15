"""Brief M3-06: the PNG writer and the standard-library reader hold the pinned format.

`png_l8` and `read_png_l8` are the step's own: no Pillow (the lane adds no dependency). The
reader refuses every PNG that is not the pinned 8-bit grey one, valid or not, because the
game reads exactly that format and `manifest` shows what it will get. The PNGs the refusals
are made from are written here, chunk by chunk.

Does NOT prove: that Godot decodes the writer's PNG (the game's SurfaceGrid test decodes the
shared fixture's, brief M3-10); that a Pillow-written PNG of the same pixels is refused only
for its format, never for its pixels.
"""

import struct
import zlib

import numpy as np
import pytest

from mattini.surfaces import SurfacesError, png_l8, read_png_l8

SIGNATURE = b"\x89PNG\r\n\x1a\n"


def _chunk(kind: bytes, body: bytes, crc: int | None = None) -> bytes:
    crc = zlib.crc32(kind + body) if crc is None else crc
    return struct.pack(">I", len(body)) + kind + body + struct.pack(">I", crc)


def _png(
    pixels: np.ndarray,
    *,
    header: tuple = (8, 0, 0, 0, 0),
    filters: dict | None = None,
    chunks: tuple = (),
    crc: int | None = None,
    stream: bytes | None = None,
    tail: bytes = b"",
) -> bytes:
    """A PNG of `pixels` written here; the keywords break one thing at a time."""
    rows, columns = pixels.shape
    lines = np.zeros((rows, columns + 1), dtype=np.uint8)
    lines[:, 1:] = pixels
    for row, value in (filters or {}).items():
        lines[row, 0] = value
    data = zlib.compress(lines.tobytes(), 9) if stream is None else stream
    ihdr = struct.pack(">II", columns, rows) + bytes(header)
    return (
        SIGNATURE
        + _chunk(b"IHDR", ihdr, crc)
        + b"".join(chunks)
        + _chunk(b"IDAT", data)
        + _chunk(b"IEND", b"")
        + tail
    )


def _pixels() -> np.ndarray:
    return np.random.default_rng(4).integers(0, 5, size=(9, 13), dtype=np.uint8)


def test_what_the_writer_writes_the_reader_reads():
    for shape in ((1, 1), (9, 13), (40, 7), (7, 40)):
        pixels = np.random.default_rng(shape[0]).integers(0, 5, size=shape, dtype=np.uint8)
        decoded = read_png_l8(png_l8(pixels))
        assert decoded.dtype == np.uint8 and np.array_equal(decoded, pixels)


def test_the_test_s_own_writer_writes_what_the_reader_reads():
    """The hand-written PNG the refusals are made from is itself accepted: so each refusal
    below is for the one thing that was broken."""
    assert np.array_equal(read_png_l8(_png(_pixels())), _pixels())


@pytest.mark.parametrize(
    "pixels",
    [
        np.zeros((3, 3), dtype=np.int64),
        np.zeros((3, 3), dtype=np.float32),
        np.zeros(9, dtype=np.uint8),
        np.zeros((2, 3, 3), dtype=np.uint8),
        np.zeros((0, 3), dtype=np.uint8),
        np.full((3, 3), 5, dtype=np.uint8),
        [[0, 1], [2, 3]],
    ],
    ids=["int64", "float32", "1-D", "3-D", "empty", "class-5", "a-list"],
)
def test_the_writer_refuses_what_is_not_classes(pixels):
    with pytest.raises(SurfacesError):
        png_l8(pixels)


@pytest.mark.parametrize(
    ("png", "pattern"),
    [
        (b"", "signature"),
        (b"GIF89a" + bytes(40), "signature"),
        (SIGNATURE, "cut short"),
        (_png(_pixels())[:-8], "cut short"),
        (_png(_pixels())[:30], "cut short"),
        (_png(_pixels(), crc=12345), "CRC"),
        (_png(_pixels(), tail=b"\x00"), "after IEND"),
        (_png(_pixels(), header=(16, 0, 0, 0, 0)), "8-bit grey"),
        (_png(_pixels(), header=(8, 2, 0, 0, 0)), "8-bit grey"),
        (_png(_pixels(), header=(8, 3, 0, 0, 0)), "8-bit grey"),
        (_png(_pixels(), header=(8, 4, 0, 0, 0)), "8-bit grey"),
        (_png(_pixels(), header=(8, 0, 1, 0, 0)), "8-bit grey"),
        (_png(_pixels(), header=(8, 0, 0, 1, 0)), "8-bit grey"),
        (_png(_pixels(), header=(8, 0, 0, 0, 1)), "interlaced"),
        (_png(_pixels(), filters={4: 1}), "row 4 .* filter 1"),
        (_png(_pixels(), filters={0: 4, 8: 2}), "row 0 .* filter 4"),
        (_png(_pixels(), chunks=(_chunk(b"tEXt", b"k\x00v"),)), "chunks"),
        (_png(_pixels(), chunks=(_chunk(b"PLTE", bytes(3)),)), "chunks"),
        (_png(_pixels(), stream=b"not zlib"), "zlib"),
        (_png(_pixels(), stream=zlib.compress(bytes(5), 9)), "zlib stream holds"),
        (_png(_pixels(), stream=zlib.compress(bytes(9 * 14 + 1), 9)), "zlib stream holds"),
        (_png(_pixels(), stream=zlib.compress(bytes(9 * 14), 9) + b"junk"), "zlib stream"),
    ],
    ids=[
        "empty",
        "gif",
        "signature-only",
        "no-iend",
        "cut-in-ihdr",
        "bad-crc",
        "after-iend",
        "16-bit",
        "rgb",
        "palette",
        "grey-alpha",
        "compression-1",
        "filter-method-1",
        "interlaced",
        "sub-filter-row",
        "two-filter-rows",
        "text-chunk",
        "palette-chunk",
        "not-zlib",
        "too-short",
        "too-long",
        "junk-after-the-stream",
    ],
)
def test_a_png_of_another_shape_is_refused(png, pattern):
    with pytest.raises(SurfacesError, match=pattern):
        read_png_l8(png)


def test_a_missing_ihdr_or_idat_is_refused():
    body = struct.pack(">IIBBBBB", 2, 2, 8, 0, 0, 0, 0)
    no_idat = SIGNATURE + _chunk(b"IHDR", body) + _chunk(b"IEND", b"")
    with pytest.raises(SurfacesError, match="IHDR, IDAT"):
        read_png_l8(no_idat)
    idat = _chunk(b"IDAT", zlib.compress(bytes(6), 9))
    with pytest.raises(SurfacesError, match="IHDR, IDAT"):
        read_png_l8(SIGNATURE + idat + _chunk(b"IHDR", body) + _chunk(b"IEND", b""))
    with pytest.raises(SurfacesError, match="not 13 bytes"):
        read_png_l8(SIGNATURE + _chunk(b"IHDR", body[:-1]) + idat + _chunk(b"IEND", b""))


def test_a_png_claiming_a_huge_size_is_refused_without_inflating_it():
    body = struct.pack(">IIBBBBB", 1 << 30, 1 << 30, 8, 0, 0, 0, 0)
    huge = SIGNATURE + _chunk(b"IHDR", body) + _chunk(b"IDAT", b"x") + _chunk(b"IEND", b"")
    with pytest.raises(SurfacesError, match="pixels"):
        read_png_l8(huge)
