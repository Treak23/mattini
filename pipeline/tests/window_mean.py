"""An independent reference for the terrain rule, for tests that build synthetic tiles (M2-01).

Since M2-01 a terrain config carries the SHA-256 its heights must have (SPEC §8,
`expected_sha256`), so a test that builds a synthetic world needs that value for its own
source. It is computed here from the test's own source heights, not by the pipeline's
`resample`: SPEC §8's window rule written another way, as the NaN-padded window around
each vertex averaged by `np.nanmean`, rather than resample's zero padding, shifted sums
and pixel counts. Both give the same bits: every sum of up to 16 of a terrain's 32-bit
heights is exact in 64-bit (SPEC §8), the counts are powers of two, the offset the tests
use (0 m) subtracts exactly, and the one rounding is the cast to 32-bit. Measured against
design's values for the 2 x 2 tile build (test_terrain_build_tiles.py), at 2 m and 0.5 m:
identical.

Does NOT prove: anything about the real village (config/terrain.json holds design's
values, computed two independent ways); the rule itself (test_terrain_rules.py checks
resample against exact fractions).
"""

import hashlib

import numpy as np
from numpy.lib.stride_tricks import sliding_window_view

SOURCE_M = 0.5


def expected_heights(source: np.ndarray, spacing_m: float, offset_m: float = 0.0) -> np.ndarray:
    """The grid's 32-bit heights for a north-up 0.5 m source covering the area exactly."""
    step = round(spacing_m / SOURCE_M)  # pixels per spacing: 1, 2 or 4
    half = max(1, step // 2)  # the window reaches `half` pixels each way from the vertex
    padded = np.pad(source.astype(np.float64), half, constant_values=np.nan)
    windows = sliding_window_view(padded, (2 * half, 2 * half))[::step, ::step]
    return (np.nanmean(windows, axis=(2, 3)) - offset_m).astype(np.float32)


def expected_sha256(source: np.ndarray, spacing_m: float, offset_m: float = 0.0) -> str:
    """The SHA-256 of the heights file (little-endian float32, rows north to south)."""
    heights = expected_heights(source, spacing_m, offset_m)
    return hashlib.sha256(heights.astype("<f4").tobytes()).hexdigest()
