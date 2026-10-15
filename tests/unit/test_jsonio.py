import pytest
from hermes_modernisation.jsonio import ContractError, dumps, loads


def test_valid_round_trip_is_canonical():
    assert (
        dumps(loads(b'{"b":[1,true,null],"a":"x"}')) == b'{"a":"x","b":[1,true,null]}'
    )


@pytest.mark.parametrize(
    "raw",
    [
        b'{"a":1,"a":2}',
        b'{"a":NaN}',
        b"[]",
        b"null",
        b'{"x":Infinity}',
        b'{"x":1e9999}',
        b'{"x":1} garbage',
        b'{"x":"\xff"}',
        b"[" * 40 + b"]" * 40,
        b'{"huge":"' + b"x" * 1048576 + b'"}',
    ],
)
def test_invalid_ambiguous_or_unbounded_input_refused(raw):
    with pytest.raises(ContractError):
        loads(raw)


@pytest.mark.parametrize(
    "value",
    [
        {"x": float("nan")},
        {"x": float("inf")},
        {1: "ambiguous"},
        {"x": b"bytes"},
        {"x": 2**100},
        {"x": "\ud800"},
    ],
)
def test_invalid_serialisation_refused(value):
    with pytest.raises(ContractError):
        dumps(value)


def test_nested_duplicate_rejected():
    with pytest.raises(ContractError):
        loads('{"x":{"a":1,"a":2}}')
