import subprocess
import sys
from pathlib import Path

import pytest

from quipu_wallet import (
    QUIPU_BLOCK_SIZES,
    QUIPU_CORD_COUNT,
    QUIPU_FORMAT_VERSION,
    QUIPU_MAGIC,
    decode_entropy,
    encode_entropy,
    format_quipu,
    mnemonic_to_quipu,
    parse_quipu,
    quipu_to_mnemonic,
)


ZERO_MNEMONIC = "abandon " * 11 + "about"
ZERO_QUIPU = [
    81,
    87,
    1,
    *([0] * 16),
    145,
    46,
    122,
    164,
]
PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_quipu_v1_golden_vector():
    assert mnemonic_to_quipu(ZERO_MNEMONIC) == ZERO_QUIPU
    assert quipu_to_mnemonic(ZERO_QUIPU) == ZERO_MNEMONIC


@pytest.mark.parametrize(
    "entropy",
    [bytes(16), bytes.fromhex("ff" * 16), bytes(range(16))],
)
def test_quipu_entropy_round_trip(entropy):
    cords = encode_entropy(entropy)
    assert len(cords) == QUIPU_CORD_COUNT == 23
    assert all(0 <= value <= 255 for value in cords)
    assert decode_entropy(cords) == entropy


def test_quipu_payload_layout():
    entropy = bytes(range(16))
    cords = encode_entropy(entropy)
    assert bytes(cords[:2]) == QUIPU_MAGIC == b"QW"
    assert cords[2] == QUIPU_FORMAT_VERSION == 1
    assert bytes(cords[3:19]) == entropy
    assert len(cords[19:]) == 4


def test_quipu_requires_exactly_128_bits():
    with pytest.raises(ValueError, match="16 bytes"):
        encode_entropy(bytes(15))


@pytest.mark.parametrize("cords", [ZERO_QUIPU[:-1], [*ZERO_QUIPU, 0]])
def test_quipu_rejects_wrong_cord_count(cords):
    with pytest.raises(ValueError, match="exactly 23"):
        decode_entropy(cords)


@pytest.mark.parametrize("value", [-1, 256, 999])
def test_quipu_rejects_out_of_range_cord_values(value):
    invalid = ZERO_QUIPU.copy()
    invalid[3] = value
    with pytest.raises(ValueError, match="between 0 and 255"):
        decode_entropy(invalid)


@pytest.mark.parametrize("value", [True, 1.5, "1", None])
def test_quipu_rejects_non_integer_cord_values(value):
    invalid = ZERO_QUIPU.copy()
    invalid[3] = value
    with pytest.raises(TypeError, match="integers"):
        decode_entropy(invalid)


def test_quipu_rejects_text_as_cord_sequence():
    with pytest.raises(TypeError, match="not text"):
        decode_entropy("081 087 001")


def test_quipu_rejects_invalid_magic():
    invalid = ZERO_QUIPU.copy()
    invalid[0] ^= 1
    with pytest.raises(ValueError, match="magic"):
        decode_entropy(invalid)


def test_quipu_rejects_unsupported_version():
    invalid = ZERO_QUIPU.copy()
    invalid[2] += 1
    with pytest.raises(ValueError, match="Unsupported"):
        decode_entropy(invalid)


@pytest.mark.parametrize("index", [3, 18, 19, 22])
def test_quipu_rejects_changed_entropy_or_tag(index):
    invalid = ZERO_QUIPU.copy()
    invalid[index] ^= 1
    with pytest.raises(ValueError, match="checksum"):
        decode_entropy(invalid)


def test_quipu_rejects_swapped_entropy_cords():
    cords = encode_entropy(bytes(range(16)))
    cords[3], cords[4] = cords[4], cords[3]
    with pytest.raises(ValueError, match="checksum"):
        decode_entropy(cords)


def test_quipu_parser_accepts_padding_commas_and_newlines():
    text = "081, 87, 001\n" + " ".join(str(value) for value in ZERO_QUIPU[3:])
    assert parse_quipu(text) == ZERO_QUIPU


@pytest.mark.parametrize("text", ["-1", "1.0", "one", "0x51"])
def test_quipu_parser_rejects_non_decimal_tokens(text):
    with pytest.raises(ValueError, match="Invalid"):
        parse_quipu(text)


def test_quipu_parser_rejects_out_of_range_value():
    with pytest.raises(ValueError, match="between 0 and 255"):
        parse_quipu("256")


def test_quipu_formatter_uses_canonical_blocks_and_padding():
    formatted = format_quipu(ZERO_QUIPU)
    lines = formatted.splitlines()
    assert tuple(len(line.split()) for line in lines) == QUIPU_BLOCK_SIZES
    assert all(len(token) == 3 for token in formatted.split())
    assert parse_quipu(formatted) == ZERO_QUIPU


def test_quipu_cli_round_trip_over_stdin():
    encode = subprocess.run(
        [sys.executable, "main.py", "encode", "quipu"],
        cwd=PROJECT_ROOT,
        input=ZERO_MNEMONIC,
        text=True,
        capture_output=True,
        check=True,
    )
    assert encode.stderr == ""
    assert len(encode.stdout.strip().splitlines()) == 6
    assert parse_quipu(encode.stdout) == ZERO_QUIPU

    decode = subprocess.run(
        [sys.executable, "main.py", "decode", "quipu"],
        cwd=PROJECT_ROOT,
        input=encode.stdout,
        text=True,
        capture_output=True,
        check=True,
    )
    assert decode.stderr == ""
    assert decode.stdout.strip() == ZERO_MNEMONIC


def test_quipu_cli_reports_invalid_input_without_traceback():
    result = subprocess.run(
        [sys.executable, "main.py", "decode", "quipu"],
        cwd=PROJECT_ROOT,
        input="081 087 001",
        text=True,
        capture_output=True,
    )
    assert result.returncode == 2
    assert result.stderr.startswith("error:")
    assert "Traceback" not in result.stderr
