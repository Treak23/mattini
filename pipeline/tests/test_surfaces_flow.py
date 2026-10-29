"""Pinning tests for brief v0.4.0-01: the surfaces step writes the flow grid.

Pinned decisions (the brief; docs/SPEC.md §13 row 53, the owner's "1b" of 2026-10-27):
- `flow_grid(features, box, cell_m)` gives, for each cell of a `cell_m` (2 m) grid on the
  area's box, rows north to south, columns west to east (texel (r, c) centred at E = e_min +
  cell/2 + c * cell, N = n_max - cell/2 - r * cell), one byte: the downstream bearing of the
  nearest drawn stream. Drawn streams are exactly those the classes draw as water
  (TLM_FLIESSGEWAESSER OBJEKTART 4, VERLAUF 100 or 500), read segment by segment in vertex
  order: swisstopo draws them downstream ("Die Linien sind in Richtung des Gewässerflusses
  gerichtet", Objektkatalog swissTLM3D 2.4, February 2026, §8.1).
- `flow_code(dx, dy)`: 0 for a zero-length segment (never painted), else 1 + (round(bearing /
  1.5) mod 240), the bearing of (dE, dN) in [0, 360) degrees, 0 north and 90 east, Python's
  round (half to even): 1 north, 61 east, 121 south, 181 west, never above 240.
- The painting: the classes' exact stadium arithmetic in passes of radius FLOW_RADIUS_M
  (12 m), 11 m, ... 1 m; in each pass every segment is painted with its code in the order
  the classes read them (features as handed over, sorted by UUID; parts; segments), a later
  paint overwriting an earlier one. A cell takes the code of a nearest segment to within
  1 m (ties to the later); 0 where none lies within 12 m (ties included). The read margin
  MARGIN_M is raised to the radius (12 m), so every line that can reach a cell is read.
- The step compares the flow's pixels with config/surfaces.json's
  `expected_flow_pixels_sha256`, then its PNG (`png_l8`, values 0 to 240) with
  `expected_flow_png_sha256`, after the classes and before anything is written, refusing each
  difference with both values (the PNG's naming the machine's zlib); it writes
  surfaces/<area>-flow.png.import (the keep text) and surfaces/<area>-flow.png before the
  description, whose `flow` object is exactly {cell_m, columns, encoding, file,
  pixels_sha256, rows, sha256}, encoding "downstream-bearing-1.5deg". `built_surfaces_block`
  refuses a built flow that is not the description's or not design's, naming the rebuild.

The fixture's flow (tests/shared/surfaces_vectors.json 'flow') was computed three ways with
identical bytes (the step's code and two programs of design's own); its points and twins
are listed there. The synthetic cases below are design's too, each named by the harm it
catches.

Does NOT prove: that the game reads the flow (brief v0.4.0-02) or that the water drifts
along it (v0.4.0-03); that the real village's flow is design's (the step's own comparison
with config/surfaces.json, on a real run); that swisstopo drew every line downstream (56 of
56 parts in the village box were measured so at the triage, not by a test); how fast the
water flows.
"""

import hashlib
import json
import math
import shutil
import struct
import zlib
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest
from computed_for import recorded
from synthetic_tlm import zipped_tlm

from mattini import surfaces
from mattini.surfaces import (
    SurfacesError,
    build_surfaces,
    built_surfaces_block,
    check_surfaces_config,
    load_surfaces_config,
)
from mattini.world import load_world

REPO = Path(__file__).resolve().parents[2]
FIXTURE = REPO / "tests" / "shared" / "surfaces_fixture"
GENERATED = FIXTURE / "generated"
VECTORS = json.loads((REPO / "tests" / "shared" / "surfaces_vectors.json").read_text("utf-8"))
FLOW = VECTORS["flow"]
BOX = (2700012.0, 2700052.0, 1199971.0, 1200001.0)  # 40 m x 30 m: 20 x 15 cells of 2 m
ZIP_NAME = "swisstlm3d_2026-02_2056_5728.gdb.zip"
REBUILD = "python -m mattini surfaces"
KEEP = b'[remap]\n\nimporter="keep"\n'
ENCODING = "downstream-bearing-1.5deg"
FLOW_KEYS = {"cell_m", "columns", "encoding", "file", "pixels_sha256", "rows", "sha256"}
NORTH, EAST, SOUTH, WEST = 1, 61, 121, 181


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def flow_code(dx: int, dy: int) -> int:
    """`surfaces.flow_code`, looked up when called: before the change each test fails alone,
    naming what is missing, instead of the whole module at its import."""
    return surfaces.flow_code(dx, dy)


def flow_grid(features: dict, box: tuple, cell_m: float) -> np.ndarray:
    """`surfaces.flow_grid`, looked up when called (as `flow_code`)."""
    return surfaces.flow_grid(features, box, cell_m)


def _fixture_features() -> dict:
    """The fixture's features as the reader hands them over: those its vectors list."""
    source = json.loads((FIXTURE / "source.json").read_text(encoding="utf-8"))
    by_uuid = {f["uuid"]: f for features in source.values() for f in features}
    return {layer: [by_uuid[u] for u in uuids] for layer, uuids in VECTORS["read"].items()}


def _stream(uuid: str, points: list, verlauf: int = 100, objektart: int = 4) -> dict:
    """A TLM_FLIESSGEWAESSER feature in the reader's form; `points` in metres, local to the
    fixture's world origin (E 2'700'000, N 1'200'000), drawn in the order given."""
    coordinates = [[2700000000 + round(e * 1000), 1200000000 + round(n * 1000)] for e, n in points]
    return {
        "uuid": uuid,
        "attributes": {"OBJEKTART": objektart, "VERLAUF": verlauf},
        "geometry": {"type": "MultiLineString", "coordinates": [coordinates]},
    }


def _streams(*streams: dict) -> dict:
    return {"TLM_BODENBEDECKUNG": [], "TLM_FLIESSGEWAESSER": list(streams), "TLM_STRASSE": []}


def _column(e: float) -> int:
    """The column whose centre is at local E `e` (13, 15, ... 51 m)."""
    return round((e - 13) / 2)


def _row(n: float) -> int:
    """The row whose centre is at local N `n` (0, -2, ... -28 m)."""
    return round(-n / 2)


# ----------------------------------------------------------------------------- the code


@pytest.mark.parametrize(
    ("dx", "dy", "code", "harm"),
    [
        (0, 1000, NORTH, "a stream flowing north must read north"),
        (1000, 0, EAST, "a stream flowing east must read east (not north: E and N swapped)"),
        (0, -1000, SOUTH, "a stream flowing south must read south (not north: N negated)"),
        (-1000, 0, WEST, "a stream flowing west must read west (not east: E negated)"),
        (1000, 1000, 31, "45 degrees is code 31"),
        (13, 1000, NORTH, "0.745 degrees rounds to 0 steps"),
        (14, 1000, 2, "0.802 degrees rounds to 1 step of 1.5"),
        (-131, 10000, 240, "359.249 degrees is step 239"),
        (-130, 10000, NORTH, "359.255 degrees rounds to step 240, which is step 0: mod 240"),
        (-1, 100000, NORTH, "just west of north is north, never 241"),
        (0, 0, 0, "a zero-length segment has no direction"),
    ],
)
def test_a_segment_s_code_is_its_downstream_bearing_in_steps_of_1_5_degrees(dx, dy, code, harm):
    assert flow_code(dx, dy) == code, harm


def test_no_code_is_above_240_and_every_code_is_its_rounded_bearing():
    rng = np.random.default_rng(53)
    for dx, dy in rng.integers(-100000, 100001, size=(2000, 2)).tolist():
        if dx == 0 and dy == 0:
            continue
        code = flow_code(dx, dy)
        assert 1 <= code <= 240, (dx, dy, code)
        bearing = math.degrees(math.atan2(dx, dy)) % 360.0
        off = (bearing - (code - 1) * 1.5 + 180.0) % 360.0 - 180.0
        assert abs(off) <= 0.75 + 1e-9, (dx, dy, code, bearing)


# -------------------------------------------------------------------- the fixture's flow


def test_the_fixture_s_flow_is_the_designed_one():
    flow = flow_grid(_fixture_features(), BOX, 2.0)
    assert flow.dtype == np.uint8 and flow.shape == (FLOW["rows"], FLOW["columns"]) == (15, 20)
    wrong = [
        (point["name"], point["code"], int(flow[point["texel"][0], point["texel"][1]]))
        for point in FLOW["points"]
        if int(flow[point["texel"][0], point["texel"][1]]) != point["code"]
    ]
    assert wrong == [], "(point, designed code, code found); the vectors' twins name the harms"
    counts = np.bincount(flow.ravel(), minlength=256)
    assert {str(k): int(counts[k]) for k in np.flatnonzero(counts)} == FLOW["counts"]
    assert _sha(flow.tobytes()) == FLOW["pixels_sha256"]


def test_the_fixture_s_points_say_what_their_code_means():
    """The vectors' words are claims too (lesson 42): each point's centre, bearing and local
    downstream direction (x = +e, z = -n) follow from its texel and its code."""
    for point in FLOW["points"]:
        row, column = point["texel"]
        e, n = BOX[0] + 1 + 2 * column, BOX[3] - 1 - 2 * row
        assert point["lv95"] == [e, n], point["name"]
        assert point["local"] == [e - 2700000.0, 1200000.0 - n], point["name"]
        if point["code"] == 0:
            assert "bearing_deg" not in point and "direction_local" not in point, point["name"]
            continue
        bearing = (point["code"] - 1) * 1.5
        assert point["bearing_deg"] == bearing, point["name"]
        x, z = point["direction_local"]
        assert abs(x - math.sin(math.radians(bearing))) < 1e-6, point["name"]
        assert abs(z + math.cos(math.radians(bearing))) < 1e-6, point["name"]


# ------------------------------------------------------- the rule, one harm at a time


def test_a_stream_drawn_north_reads_north_and_the_same_line_drawn_south_reads_south():
    north = flow_grid(_streams(_stream("{A}", [(32.0, -40.0), (32.0, 10.0)])), BOX, 2.0)
    south = flow_grid(_streams(_stream("{A}", [(32.0, 10.0), (32.0, -40.0)])), BOX, 2.0)
    within = [c for c in range(20) if abs(13 + 2 * c - 32.0) <= 12]
    assert within == list(range(4, 16))
    assert (north[:, within] == NORTH).all(), "the line read in its own order: north"
    assert (south[:, within] == SOUTH).all(), "the line read backwards would turn every code"
    assert not north[:, [0, 1, 2, 3, 16, 17, 18, 19]].any(), "farther than 12 m: none"


def test_a_stream_drawn_east_reads_east_and_rows_run_north_to_south():
    flow = flow_grid(_streams(_stream("{A}", [(0.0, -10.0), (64.0, -10.0)])), BOX, 2.0)
    painted = np.flatnonzero(flow.any(axis=1)).tolist()
    assert painted == list(range(12)), (
        "rows 0 (N 0 m) to 11 (N -22 m, exactly 12 m from the line at N -10 m, ties included) are "
        "painted, rows 12 to 14 are not: rows from the south paint rows 3 to 14, a radius of 11 m "
        "or a strict distance test stops at row 10"
    )
    assert (flow[:12] == EAST).all(), "east: not north (E and N swapped), not west (read backwards)"


def test_the_nearer_stream_wins():
    flow = flow_grid(
        _streams(
            _stream("{A}", [(20.0, -40.0), (20.0, 10.0)]),  # north
            _stream("{B}", [(40.0, 10.0), (40.0, -40.0)]),  # south, later in order
        ),
        BOX,
        2.0,
    )
    assert (flow[:, _column(29)] == NORTH).all(), "9 m from A, 11 m from B: A (passes 12 to 1)"
    assert (flow[:, _column(31)] == SOUTH).all(), "11 m from A, 9 m from B: B"


@pytest.mark.parametrize(
    ("uuid_a", "uuid_b", "code"), [("{A}", "{B}", SOUTH), ("{C}", "{B}", NORTH)]
)
def test_within_one_pass_the_later_stream_wins(uuid_a, uuid_b, code):
    """The cell at E 31 m lies 11.5 m from both lines: one pass, the later in order paints last."""
    flow = flow_grid(
        _streams(
            *sorted(
                [
                    _stream(uuid_a, [(19.5, -40.0), (19.5, 10.0)]),  # north
                    _stream(uuid_b, [(42.5, 10.0), (42.5, -40.0)]),  # south
                ],
                key=lambda f: f["uuid"],
            )
        ),
        BOX,
        2.0,
    )
    assert flow[:, _column(31)].all(), "11.5 m from both lines: painted in the 12 m pass"
    assert (flow[:, _column(31)] == code).all(), "ties to the later segment, not the earlier"


def test_a_cell_exactly_12_m_from_a_stream_is_painted_and_one_farther_is_not():
    at_12 = flow_grid(_streams(_stream("{A}", [(1.0, -40.0), (1.0, 10.0)])), BOX, 2.0)
    assert (at_12[:, 0] == NORTH).all(), "12.000 m: the largest pass, ties included"
    assert not at_12[:, 1:].any(), "14 m: none"
    beyond = flow_grid(_streams(_stream("{A}", [(0.999, -40.0), (0.999, 10.0)])), BOX, 2.0)
    assert not beyond.any(), "12.001 m: none (a radius of 13 m would paint it)"
    at_13 = flow_grid(_streams(_stream("{A}", [(2.0, -40.0), (2.0, 10.0)])), BOX, 2.0)
    assert (at_13[:, 0] == NORTH).all() and not at_13[:, 1:].any(), "11 m in, 13 m out"


def test_the_read_margin_is_the_flow_radius():
    """A line 11 m outside the area paints the cells 12 m from it only if it is read: the step
    reads the area grown by MARGIN_M, so MARGIN_M must reach the radius (the fixture's s11)."""
    assert surfaces.FLOW_RADIUS_M == 12, "the largest pass, measured on the village (brief)"
    assert surfaces.MARGIN_M == surfaces.FLOW_RADIUS_M, "a line 11 m outside is read only so"


@pytest.mark.parametrize(
    ("objektart", "verlauf", "drawn"),
    [(4, 100, True), (4, 500, True), (4, 200, False), (4, 400, False), (7, 100, False)],
    ids=["above-ground", "waterfall", "underground", "on-a-bridge", "trockenrinne"],
)
def test_only_the_streams_the_classes_draw_as_water_give_a_flow(objektart, verlauf, drawn):
    flow = flow_grid(
        _streams(_stream("{A}", [(32.0, -40.0), (32.0, 10.0)], verlauf, objektart)), BOX, 2.0
    )
    assert bool(flow.any()) is drawn, f"OBJEKTART {objektart}, VERLAUF {verlauf}: drawn {drawn}"


def test_a_zero_length_segment_is_never_painted():
    alone = flow_grid(_streams(_stream("{A}", [(32.0, -14.0), (32.0, -14.0)])), BOX, 2.0)
    assert not alone.any(), "a repeated vertex has no direction: nothing, not north"
    line = [(32.0, -40.0), (32.0, -14.0)]
    without = flow_grid(_streams(_stream("{A}", line)), BOX, 2.0)
    repeated = flow_grid(_streams(_stream("{A}", [*line, line[-1]])), BOX, 2.0)
    assert (repeated == without).all(), "a repeated last vertex paints over nothing"


def test_a_bearing_just_west_of_north_is_code_1_never_241():
    flow = flow_grid(_streams(_stream("{A}", [(32.1, -40.0), (32.0, 10.0)])), BOX, 2.0)
    assert set(np.unique(flow).tolist()) == {0, NORTH}


def test_the_flow_holds_no_code_above_240():
    rng = np.random.default_rng(8)
    streams = [
        _stream(f"{{{i:02d}}}", rng.uniform([-10, -40], [62, 10], size=(5, 2)).round(3).tolist())
        for i in range(12)
    ]
    flow = flow_grid(_streams(*streams), BOX, 2.0)
    assert flow.max() <= 240 and flow.any()


# ------------------------------------------------------------------------------ the step


def _case(tmp_path: Path) -> SimpleNamespace:
    """The fixture's world, datasets, lock and config, and a raw folder as `download tlm`
    leaves it, holding the fixture's source.json as a zipped FileGDB."""
    world = load_world(FIXTURE / "world.json")
    source = json.loads((FIXTURE / "source.json").read_text(encoding="utf-8"))
    (tmp_path / "make").mkdir()
    data = zipped_tlm(tmp_path / "make", source, zip_name=ZIP_NAME).read_bytes()
    folder = tmp_path / "raw" / "swisstlm3d" / "2026-02"
    folder.mkdir(parents=True)
    (folder / ZIP_NAME).write_bytes(data)
    entry = {
        "collection": "ch.swisstopo.swisstlm3d",
        "edition": "2026-02",
        "file": ZIP_NAME,
        "sha256": _sha(data),
    }
    provenance = {
        **entry,
        "attribution": "© swisstopo",
        "dataset": "swisstlm3d",
        "item": "swisstlm3d_2026-02",
        "schema": 1,
        "size_bytes": len(data),
        "url": f"https://data.geo.admin.ch/ch.swisstopo.swisstlm3d/swisstlm3d_2026-02/{ZIP_NAME}",
    }
    (folder / "provenance.json").write_text(json.dumps(provenance), encoding="utf-8")
    lock = {"schema": 1, "datasets": {"swisstlm3d": entry}}
    datasets = json.loads((FIXTURE / "datasets.json").read_text(encoding="utf-8"))["datasets"]
    config = recorded(load_surfaces_config(FIXTURE / "surfaces.json"), world, lock, "swisstlm3d")
    return SimpleNamespace(
        world=world,
        datasets=datasets,
        lock=lock,
        config=config,
        raw=tmp_path / "raw",
        out=tmp_path / "out",
    )


def _build(case, **keywords) -> dict:
    return build_surfaces(
        case.world, case.datasets, case.lock, case.config, case.raw, case.out, **keywords
    )


def test_the_step_writes_the_designed_flow(tmp_path):
    case = _case(tmp_path)
    block = _build(case)
    designed = json.loads((GENERATED / "surfaces" / "fixture.json").read_text(encoding="utf-8"))
    assert block["flow"] == designed["flow"]
    assert block["flow"] == {
        "cell_m": 2.0,
        "columns": 20,
        "encoding": ENCODING,
        "file": "surfaces/fixture-flow.png",
        "pixels_sha256": FLOW["pixels_sha256"],
        "rows": 15,
        "sha256": FLOW["png_sha256"],
    }, "s11, 11 m west of the area, is read by the step (MARGIN_M 12) and paints column 0"
    folder = case.out / "surfaces"
    assert (folder / "fixture-flow.png.import").exists(), "the flow's keep file (brain.md H24)"
    assert (folder / "fixture-flow.png.import").read_bytes() == KEEP
    png = (folder / "fixture-flow.png").read_bytes()
    assert png == (GENERATED / "surfaces" / "fixture-flow.png").read_bytes()
    assert _sha(surfaces.read_png_l8(png).tobytes()) == FLOW["pixels_sha256"]


def test_another_flow_is_refused_after_the_classes_and_before_anything_is_written(tmp_path):
    case = _case(tmp_path)
    case.config["areas"]["fixture"]["expected_flow_pixels_sha256"] = "0" * 64
    said: list[str] = []
    with pytest.raises(SurfacesError) as refusal:
        _build(case, progress=said.append)
    text = str(refusal.value)
    for part in (
        "0" * 64,
        FLOW["pixels_sha256"],
        "config/surfaces.json",
        "expected_flow_pixels_sha256",
        "nothing was written",
    ):
        assert part in text, (part, text)
    assert said[-1].startswith("the PNG has the SHA-256"), "the classes and their PNG first"
    assert not case.out.exists(), "compared before writing: not a folder, not a .part"


def test_the_flow_is_compared_before_its_png_is_encoded(tmp_path, monkeypatch):
    case = _case(tmp_path)
    case.config["areas"]["fixture"]["expected_flow_pixels_sha256"] = "0" * 64
    case.config["areas"]["fixture"]["expected_flow_png_sha256"] = "1" * 64
    real, values = surfaces.png_l8, []
    monkeypatch.setattr(
        surfaces,
        "png_l8",
        lambda pixels, *a: (values.append(int(pixels.max())), real(pixels, *a))[1],
    )
    with pytest.raises(SurfacesError, match="expected_flow_pixels_sha256") as refusal:
        _build(case)
    assert "expected_flow_png_sha256" not in str(refusal.value)
    assert values == [4], "only the classes' PNG was encoded"
    assert not case.out.exists()


ZLIB_HERE = "9.8.7-test"


def test_a_flow_png_of_other_bytes_is_refused_naming_zlib_before_anything_is_written(
    tmp_path, monkeypatch
):
    case = _case(tmp_path)
    case.config["areas"]["fixture"]["expected_flow_png_sha256"] = "0" * 64
    monkeypatch.setattr(surfaces.zlib, "ZLIB_RUNTIME_VERSION", ZLIB_HERE)
    said: list[str] = []
    with pytest.raises(SurfacesError) as refusal:
        _build(case, progress=said.append)
    text = str(refusal.value)
    for part in (
        "0" * 64,
        FLOW["png_sha256"],
        "expected_flow_png_sha256",
        f"zlib {ZLIB_HERE}",
        "uv python install 3.13 --managed-python",
        "nothing was written",
    ):
        assert part in text, (part, text)
    assert said[-1].startswith("the flow has the SHA-256"), "the flow's pixels matched first"
    assert not case.out.exists()


# ---------------------------------------------------------------------- the built flow


def _built(tmp_path: Path) -> Path:
    shutil.copytree(GENERATED / "surfaces", tmp_path / "surfaces")
    return tmp_path


def _check(out: Path, config: dict | None = None):
    world_path = FIXTURE / "world.json"
    lock = json.loads((FIXTURE / "datasets.lock.json").read_text(encoding="utf-8"))
    datasets = json.loads((FIXTURE / "datasets.json").read_text(encoding="utf-8"))["datasets"]
    return built_surfaces_block(
        out,
        config or load_surfaces_config(FIXTURE / "surfaces.json"),
        load_world(world_path),
        _sha(world_path.read_bytes()),
        datasets,
        lock,
    )


def _rewrite(out: Path, change) -> None:
    path = out / "surfaces" / "fixture.json"
    block = json.loads(path.read_text(encoding="utf-8"))
    change(block)
    path.write_text(json.dumps(block, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _png(pixels: np.ndarray) -> bytes:
    """An 8-bit grey PNG written here, filter 0, one IDAT."""
    rows, columns = pixels.shape
    raw = b"".join(b"\x00" + pixels[r].tobytes() for r in range(rows))

    def chunk(kind: bytes, body: bytes) -> bytes:
        return (
            struct.pack(">I", len(body)) + kind + body + struct.pack(">I", zlib.crc32(kind + body))
        )

    header = struct.pack(">IIBBBBB", columns, rows, 8, 0, 0, 0, 0)
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", header)
        + chunk(b"IDAT", zlib.compress(raw, 9))
        + chunk(b"IEND", b"")
    )


def test_the_built_flow_gives_its_block(tmp_path):
    block = _check(_built(tmp_path))
    assert set(block["flow"]) == FLOW_KEYS
    assert block["flow"]["pixels_sha256"] == FLOW["pixels_sha256"]


@pytest.mark.parametrize(
    ("change", "pattern"),
    [
        (lambda b: b.pop("flow"), "keys"),
        (lambda b: b["flow"].pop("encoding"), "flow must be an object with exactly the keys"),
        (lambda b: b["flow"].update(file="surfaces/fixture.png"), "flow.file"),
        (lambda b: b["flow"].update(cell_m=0.2), "flow.cell_m"),
        (lambda b: b["flow"].update(columns=200), "flow.columns"),
        (lambda b: b["flow"].update(encoding="bearing-degrees"), "flow.encoding"),
        (lambda b: b["flow"].update(sha256="0" * 64), "fixture-flow.png has SHA-256"),
    ],
    ids=[
        "no-flow",
        "a-key-missing",
        "another-file",
        "another-cell",
        "other-columns",
        "another-encoding",
        "another-png",
    ],
)
def test_a_built_flow_that_does_not_fit_is_refused_naming_the_rebuild(tmp_path, change, pattern):
    out = _built(tmp_path)
    _rewrite(out, change)
    with pytest.raises(SurfacesError, match=pattern) as refusal:
        _check(out)
    assert REBUILD in str(refusal.value)


@pytest.mark.parametrize("keep", [None, b'[remap]\n\nimporter="texture"\n'])
def test_a_flow_png_without_its_keep_file_is_refused(tmp_path, keep):
    out = _built(tmp_path)
    path = out / "surfaces" / "fixture-flow.png.import"
    if keep is None:
        path.unlink()
    else:
        path.write_bytes(keep)
    with pytest.raises(SurfacesError) as refusal:
        _check(out)
    assert REBUILD in str(refusal.value)


def test_a_flow_of_other_codes_is_refused_naming_the_expected_value(tmp_path):
    out = _built(tmp_path)
    flow = surfaces.read_png_l8((out / "surfaces" / "fixture-flow.png").read_bytes())
    flow[0, 0] = SOUTH  # s11's north at the 12 m tie, turned
    png = _png(flow)
    (out / "surfaces" / "fixture-flow.png").write_bytes(png)

    def change(block):
        block["flow"].update(sha256=_sha(png), pixels_sha256=_sha(flow.tobytes()))

    _rewrite(out, change)
    with pytest.raises(SurfacesError, match="expected_flow_pixels_sha256") as refusal:
        _check(out)
    assert REBUILD in str(refusal.value)


def test_a_flow_png_that_is_not_the_configs_is_refused_whatever_it_holds(tmp_path):
    config = load_surfaces_config(FIXTURE / "surfaces.json")
    config["areas"]["fixture"]["expected_flow_png_sha256"] = "0" * 64
    with pytest.raises(SurfacesError, match="expected_flow_png_sha256") as refusal:
        _check(_built(tmp_path), config)
    assert REBUILD in str(refusal.value)


# ---------------------------------------------------------------------------- the config


@pytest.mark.parametrize(
    ("key", "value", "pattern"),
    [
        ("flow_cell_m", None, "exactly the keys"),
        ("expected_flow_pixels_sha256", None, "exactly the keys"),
        ("expected_flow_png_sha256", None, "exactly the keys"),
        ("flow_cell_m", 1, "flow_cell_m"),
        ("flow_cell_m", "2", "flow_cell_m"),
        ("expected_flow_pixels_sha256", {"2": "0" * 64}, "expected_flow_pixels_sha256"),
        ("expected_flow_png_sha256", "0" * 63, "expected_flow_png_sha256"),
        ("expected_flow_png_sha256", "A" * 64, "expected_flow_png_sha256"),
    ],
)
def test_a_config_without_well_formed_flow_values_is_refused(key, value, pattern):
    config = load_surfaces_config(FIXTURE / "surfaces.json")
    area = config["areas"]["fixture"]
    if value is None:
        area.pop(key)
    else:
        area[key] = value
    with pytest.raises(SurfacesError, match=pattern):
        check_surfaces_config(config)


def test_the_fixture_s_config_expects_its_designed_flow():
    area = load_surfaces_config(FIXTURE / "surfaces.json")["areas"]["fixture"]
    assert area["flow_cell_m"] == 2
    assert area["expected_flow_pixels_sha256"] == FLOW["pixels_sha256"]
    assert area["expected_flow_png_sha256"] == FLOW["png_sha256"]
    assert _sha((GENERATED / "surfaces" / "fixture-flow.png").read_bytes()) == FLOW["png_sha256"]
