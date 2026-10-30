"""Guard of brief v0.5.0-02 the pinned tests leave open (Decision 8): progress goes to stderr
and stdout holds the manifest's path alone, for every step that builds through `_build_step`.

The recorder of test_m4_09_commands never calls `progress`; here a stand-in does, so a progress
function that prints to stdout fails.

Does NOT prove: the real run's output (the brief's real run).
"""

import pytest

from mattini import __main__ as cli


@pytest.mark.parametrize("step", cli.STEPS)
def test_progress_goes_to_stderr_and_stdout_is_the_manifest_path_alone(
    step, tmp_path, monkeypatch, capsys
):
    module = getattr(cli, step)

    def stand_in(*args, progress=None, **kwargs):
        assert progress is not None
        progress(f"{step} progress line")

    monkeypatch.setattr(module, f"build_{step}", stand_in)
    out = tmp_path / "out"
    code = cli.main([step, "--raw", str(tmp_path / "raw"), "--out", str(out)])
    seen = capsys.readouterr()
    assert code == 0, seen.err
    assert seen.out == f"{out / 'manifest.json'}\n"
    assert f"{step} progress line" in seen.err
