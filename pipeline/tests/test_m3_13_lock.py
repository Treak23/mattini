"""Brief M3-13's own tests of the lock's two new helpers: `entries_sha256`'s refusal and
`shape_problem`.

Pinned decisions (brief M3-13, decision 4; SPEC §8): `lock.entries_sha256(lock, names)` over a
name the lock has no entry for is a LockError naming that dataset's lock command, never a
KeyError (a step then ends in one `mattini: error:` line, not a traceback). The digest itself
is pinned by test_lock_entries.py. `lock.shape_problem(lock)` is `validate_lock`'s refusal as
the whole text, or None for a well-formed lock: what the steps, given a lock in memory,
refuse in their own error class beside `fit_problem`'s question of fit.

Harm prevented: a lock that lacks a dataset's entry ending in a KeyError traceback in the
roofs or trees step's inputs check, and a malformed in-memory lock accepted by a step because
`fit_problem` (which compares collection, edition, resolution and ids) does not look at the
entries' key sets, file names or checksums.

Does NOT prove: that each step calls them (test_m3_13_step_fit.py).
"""

import copy
import json

import pytest

from mattini.lock import LOCK_COMMANDS, LockError, entries_sha256, load_lock, shape_problem
from mattini.world import REPO

COMMITTED = load_lock(REPO / "config" / "datasets.lock.json")
COMMAND = {
    "swissalti3d": "python -m mattini lock terrain",
    "swissbuildings3d": "python -m mattini lock buildings",
    "swissimage": "python -m mattini lock photo",
    "swisssurface3d": "python -m mattini lock surface",
    "swisstlm3d": "python -m mattini lock tlm",
}


@pytest.mark.parametrize("name", sorted(COMMAND))
def test_a_name_the_lock_has_no_entry_for_names_its_lock_command(name):
    lock = copy.deepcopy(COMMITTED)
    del lock["datasets"][name]
    others = sorted(set(COMMAND) - {name})
    with pytest.raises(LockError) as refused:
        entries_sha256(lock, [others[0], name])
    assert name in str(refused.value) and COMMAND[name] in str(refused.value)
    assert not isinstance(refused.value, KeyError)


def test_a_dataset_the_lock_does_not_know_is_refused_without_a_command():
    with pytest.raises(LockError, match="swissnothing3d"):
        entries_sha256(COMMITTED, ["swissnothing3d"])


@pytest.mark.parametrize("lock", [[], {}, {"schema": 1}, {"datasets": []}, None])
def test_something_that_is_not_a_lock_is_a_lock_error_not_a_type_error(lock):
    with pytest.raises(LockError):
        entries_sha256(lock, ["swissimage"])


def test_no_names_is_the_digest_of_the_empty_object():
    import hashlib

    assert entries_sha256(COMMITTED, []) == hashlib.sha256(b"{}").hexdigest()


def test_the_committed_lock_is_well_formed():
    assert shape_problem(COMMITTED) is None
    assert shape_problem(json.loads(json.dumps(COMMITTED))) is None


@pytest.mark.parametrize(
    ("change", "complaint"),
    [
        (lambda d: d["swissimage"].update(note="x"), "exactly the keys"),
        (lambda d: d["swisstlm3d"].update(file="../x.zip"), "plain file name"),
        (lambda d: d["swisstlm3d"].update(sha256="A" * 64), "lower-case hex"),
        (lambda d: next(iter(d["swissimage"]["tiles"].values())).pop("sha256"), "exactly the keys"),
        (
            lambda d: d["swisssurface3d"]["tiles"][min(d["swisssurface3d"]["tiles"])].update(
                edition="x"
            ),
            "edition",
        ),
    ],
)
def test_a_malformed_lock_is_the_whole_refusal_naming_all_five_commands(change, complaint):
    lock = copy.deepcopy(COMMITTED)
    change(lock["datasets"])
    message = shape_problem(lock)
    assert message and complaint in message and message.startswith("the lock: ")
    for command in LOCK_COMMANDS:
        assert command in message


@pytest.mark.parametrize("lock", [[], None, {"schema": 1}, {"schema": 1, "datasets": {}}])
def test_something_that_is_not_a_lock_has_a_shape_problem(lock):
    assert shape_problem(lock)
