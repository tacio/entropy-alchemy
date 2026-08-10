import math
import subprocess
import sys
from pathlib import Path

import pytest

from chess_wallet import (
    CHESS_FORMAT_VERSION,
    CHESS_MAGIC,
    CHESS_PAYLOAD_BITS,
    CHESS_STATE_COUNT,
    CHESS_TAG_BITS,
    _board_rank_to_payload,
    _board_to_integer,
    _integer_to_board,
    _pack_payload,
    _payload_to_board_rank,
    board_to_mnemonic,
    decode_entropy,
    encode_entropy,
    mnemonic_to_board,
    parse_board,
)


ZERO_MNEMONIC = "abandon " * 11 + "about"
ZERO_BOARD = """
WP WP WP WP WP WP WP WP
WR WR WN:N WN:N WB:N WB:N WQ WK:N
BP BP BP BP BP BP BP BP
BR BR BN:E . . . . .
BN:E BK:E . . . . . .
. . . . . . . .
. . . . . BB:S BB:E .
. . . . . BQ . .
""".split()
PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_chess_v1_golden_board():
    assert mnemonic_to_board(ZERO_MNEMONIC) == ZERO_BOARD
    assert board_to_mnemonic(ZERO_BOARD) == ZERO_MNEMONIC


@pytest.mark.parametrize(
    "entropy",
    [bytes(16), bytes.fromhex("ff" * 16), bytes(range(16))],
)
def test_chess_entropy_round_trip(entropy):
    board = encode_entropy(entropy)
    assert len(board) == 64
    assert decode_entropy(board) == entropy


def test_chess_state_space_fits_exactly_160_payload_bits():
    assert CHESS_STATE_COUNT == int(
        "2682210745960470404760802361093493020497436168745"
    )
    assert 2**CHESS_PAYLOAD_BITS < CHESS_STATE_COUNT < 2**161
    assert math.log2(CHESS_STATE_COUNT) == pytest.approx(160.87597115134628)
    assert _pack_payload(bytes.fromhex("ff" * 16)).bit_length() == 160


@pytest.mark.parametrize(
    "payload",
    [0, 1, 2**80, 2**159, 2**160 - 1],
)
def test_payload_mapping_and_board_ranking_round_trip(payload):
    rank = _payload_to_board_rank(payload)
    board = _integer_to_board(rank)
    assert _board_to_integer(board) == rank
    assert _board_rank_to_payload(rank) == payload


def test_board_rank_rejects_non_codeword():
    with pytest.raises(ValueError, match="codeword"):
        _board_rank_to_payload(2)


def test_different_entropy_produces_different_boards():
    assert encode_entropy(bytes(16)) != encode_entropy(
        bytes.fromhex("00" * 15 + "01")
    )


def test_chess_entropy_requires_exactly_128_bits():
    with pytest.raises(ValueError, match="16 bytes"):
        encode_entropy(bytes(15))


def test_board_parser_accepts_case_commas_and_newlines():
    text = ", ".join(cell.lower() for cell in ZERO_BOARD[:32])
    text += "\n" + " ".join(cell.lower() for cell in ZERO_BOARD[32:])
    assert parse_board(text) == ZERO_BOARD


def test_board_rejects_wrong_cell_count():
    with pytest.raises(ValueError, match="exactly 64"):
        decode_entropy(ZERO_BOARD[:-1])


@pytest.mark.parametrize(
    ("cell", "message"),
    [
        ("XX", "Unknown"),
        ("WN", "requires an orientation"),
        ("WK:S", "one of: N, E"),
        ("WP:N", "does not accept"),
    ],
)
def test_board_rejects_invalid_cell_tokens(cell, message):
    invalid = [cell, *ZERO_BOARD[1:]]
    with pytest.raises(ValueError, match=message):
        decode_entropy(invalid)


def test_board_rejects_excess_piece_count():
    invalid = ["WP"] * 9 + ["."] * 55
    with pytest.raises(ValueError, match="more than 8 WP"):
        decode_entropy(invalid)


def _replace_field(payload, value, width, shift):
    mask = ((1 << width) - 1) << shift
    return (payload & ~mask) | (value << shift)


@pytest.mark.parametrize(
    ("mutate", "message"),
    [
        (lambda value: value ^ 1, "checksum"),
        (
            lambda value: _replace_field(
                value,
                CHESS_FORMAT_VERSION + 1,
                8,
                CHESS_TAG_BITS,
            ),
            "Unsupported",
        ),
        (
            lambda value: _replace_field(
                value,
                CHESS_MAGIC ^ 1,
                8,
                CHESS_TAG_BITS + 8,
            ),
            "magic",
        ),
    ],
)
def test_board_rejects_invalid_v1_metadata(mutate, message):
    payload = mutate(_pack_payload(bytes(16)))
    board = _integer_to_board(_payload_to_board_rank(payload))
    with pytest.raises(ValueError, match=message):
        decode_entropy(board)


def test_board_rejects_changed_orientation():
    invalid = ZERO_BOARD.copy()
    square = invalid.index("WN:N")
    invalid[square] = "WN:E"
    with pytest.raises(ValueError):
        decode_entropy(invalid)


def test_chess_cli_round_trip_over_stdin():
    encode = subprocess.run(
        [sys.executable, "main.py", "encode", "chess"],
        cwd=PROJECT_ROOT,
        input=ZERO_MNEMONIC,
        text=True,
        capture_output=True,
        check=True,
    )
    assert encode.stderr == ""
    assert len(encode.stdout.strip().splitlines()) == 8
    assert encode.stdout.split() == ZERO_BOARD

    decode = subprocess.run(
        [sys.executable, "main.py", "decode", "chess"],
        cwd=PROJECT_ROOT,
        input=encode.stdout,
        text=True,
        capture_output=True,
        check=True,
    )
    assert decode.stderr == ""
    assert decode.stdout.strip() == ZERO_MNEMONIC


@pytest.mark.parametrize("command", ["encode", "decode"])
def test_cli_requires_medium_subcommand(command):
    result = subprocess.run(
        [sys.executable, "main.py", command],
        cwd=PROJECT_ROOT,
        text=True,
        capture_output=True,
    )
    assert result.returncode == 2
    assert "required" in result.stderr
    assert "Traceback" not in result.stderr
