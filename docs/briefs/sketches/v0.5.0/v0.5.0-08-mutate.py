"""The mutation rows of brief v0.5.0-08, as the pin author ran them on the throwaway (2026-10-30).

python3 -I docs/briefs/sketches/v0.5.0/v0.5.0-08-mutate.py N   applies row N to the working tree
(run from the repository's root; each edit must match exactly once). The rows' meaning, the
tests that fail and the harm are in the brief and in v0.5.0-08-PINSPEC.md. A builder's code may
read otherwise: the brief's table names the mistake, not these lines.
"""

import sys
from pathlib import Path

CLOCK = "game/scripts/sky/sky_clock.gd"
MAIN = "game/scripts/main.gd"
FROM = "const VALID_FROM_UNIX := 1577836800.0\n"
TO = "const VALID_TO_UNIX := 2082758400.0\n"
CHECK = "\treturn unix >= VALID_FROM_UNIX and unix < VALID_TO_UNIX\n"
HEADER = (
    "## 2020 to 24 Dec 2035, UTC); nothing here claims more. VALID_FROM_UNIX and VALID_TO_UNIX"
    " bound\n"
    "## that range and in_validated_range says whether a time lies in it. The game's keys and the\n"
)
OLD_HEADER = "## 2020 to 24 Dec 2035, UTC); nothing here claims more. The game's day keys can leave it.\n"
NOTE = "\tif not SkyClock.in_validated_range(time_unix):\n\t\ttext += CLOCK_NOTE\n"
HIDE = "\t\t\tif _clock_left <= 0.0 and SkyClock.in_validated_range(time_unix):\n"
SHOW = "\tif not SkyClock.in_validated_range(time_unix):\n\t\t_clock.show()\n"
KEY_END = "\telse:\n\t\treturn\n\tget_viewport().set_input_as_handled()\n"
RUN = "\t\ttime_unix += delta * SPEEDS[_speed]\n"
FRAME = "\tif not _pause_menu.visible:\n" + RUN

ROWS = {
    1: [(CLOCK, FROM, FROM.replace("1577836800.0", "1546300800.0"))],
    2: [(CLOCK, TO, TO.replace("2082758400.0", "2114380800.0"))],
    3: [(CLOCK, CHECK, CHECK.replace(">=", ">"))],
    4: [(CLOCK, CHECK, CHECK.replace("< VALID_TO", "<= VALID_TO"))],
    5: [(CLOCK, CHECK, "\treturn unix < VALID_TO_UNIX\n")],
    6: [(CLOCK, CHECK, "\treturn unix >= VALID_FROM_UNIX\n")],
    7: [
        (
            CLOCK,
            CHECK,
            "\treturn not (unix < VALID_FROM_UNIX or unix >= VALID_TO_UNIX)\n",
        )
    ],
    8: [(MAIN, NOTE, "")],
    9: [(MAIN, NOTE, "\ttext += CLOCK_NOTE\n")],
    10: [(MAIN, SHOW, "")],
    11: [(MAIN, SHOW, ""), (MAIN, HIDE, "\t\t\tif _clock_left <= 0.0:\n")],
    12: [
        (
            MAIN,
            KEY_END,
            KEY_END.replace(
                "\tget_viewport()",
                "\ttime_unix = clampf(time_unix, SkyClock.VALID_FROM_UNIX,"
                " SkyClock.VALID_TO_UNIX - 1.0)\n\tget_viewport()",
            ),
        )
    ],
    13: [
        (
            MAIN,
            RUN,
            RUN + "\t\ttime_unix = minf(time_unix, SkyClock.VALID_TO_UNIX - 1.0)\n",
        )
    ],
    14: [
        (
            MAIN,
            NOTE,
            NOTE.replace(
                "SkyClock.in_validated_range(time_unix)",
                "(time_unix >= 1577836800.0 and time_unix < 2082758400.0)",
            ),
        )
    ],
    15: [(CLOCK, HEADER, OLD_HEADER)],
    # Rows 16 and 17 come from the checker's two surviving twins (added at the re-cut on main).
    16: [(MAIN, NOTE, NOTE.replace("\tif not", "\tif speed != 0.0 and not"))],
    17: [(MAIN, SHOW, ""), (MAIN, FRAME, SHOW + FRAME)],
}


def main() -> None:
    for path, old, new in ROWS[int(sys.argv[1])]:
        text = Path(path).read_text(encoding="utf-8")
        if text.count(old) != 1:
            sys.exit(f"{path}: {old!r} found {text.count(old)} times")
        Path(path).write_text(text.replace(old, new), encoding="utf-8")


if __name__ == "__main__":
    main()
