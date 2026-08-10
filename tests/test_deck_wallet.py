import subprocess
import sys
from pathlib import Path

import pytest

from deck_wallet import (
    AUXILIARY_BITS,
    FORMAT_VERSION,
    MAGIC,
    RESERVED_BITS,
    STANDARD_DECK,
    TAG_BITS,
    VERSION_BITS,
    _integer_to_deck,
    _pack_payload,
    decode_entropy,
    deck_to_mnemonic,
    encode_entropy,
    entropy_to_mnemonic,
    mnemonic_to_deck,
    mnemonic_to_entropy,
    parse_cards,
)


ZERO_MNEMONIC = "abandon " * 11 + "about"
ZERO_DECK = (
    "7S 3C 9S AD 4D 7C JS 8C 6D AC 10D 6H 8S 10H 2D 6C KD JC 2C 4C "
    "5C 9C 10C QC KC 3D 5D 7D 8D 9D JD QD 2H 3H 4H 5H 7H 8H 9H JH "
    "QH KH AH 2S 3S 4S 5S 6S 10S QS KS AS"
).split()
PROJECT_ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize(
    ("entropy_hex", "mnemonic"),
    [
        ("00" * 16, ZERO_MNEMONIC),
        (
            "7f" * 16,
            "legal winner thank year wave sausage worth useful legal winner thank yellow",
        ),
        (
            "80" * 16,
            "letter advice cage absurd amount doctor acoustic avoid letter advice cage above",
        ),
        ("ff" * 16, "zoo " * 11 + "wrong"),
    ],
)
def test_official_bip39_vectors(entropy_hex, mnemonic):
    entropy = bytes.fromhex(entropy_hex)
    assert entropy_to_mnemonic(entropy) == mnemonic
    assert mnemonic_to_entropy(mnemonic) == entropy


def test_v1_golden_deck_vector():
    assert mnemonic_to_deck(ZERO_MNEMONIC) == ZERO_DECK
    assert deck_to_mnemonic(ZERO_DECK) == ZERO_MNEMONIC


@pytest.mark.parametrize(
    ("entropy",),
    [(bytes(16),), (bytes.fromhex("ff" * 16),), (bytes(range(16)),)],
)
def test_entropy_round_trip(entropy):
    deck = encode_entropy(entropy)
    assert len(deck) == 52
    assert len(set(deck)) == 52
    assert decode_entropy(deck) == entropy


def test_different_entropy_produces_different_deck():
    assert encode_entropy(bytes(16)) != encode_entropy(bytes.fromhex("00" * 15 + "01"))


@pytest.mark.parametrize(
    "mnemonic, message",
    [
        ("abandon " * 11, "exactly 12"),
        ("abandon " * 11 + "notaword", "Unknown"),
        ("abandon " * 12, "checksum"),
    ],
)
def test_invalid_mnemonics(mnemonic, message):
    with pytest.raises(ValueError, match=message):
        mnemonic_to_entropy(mnemonic)


def test_entropy_requires_exactly_128_bits():
    with pytest.raises(ValueError, match="16 bytes"):
        encode_entropy(bytes(15))


def test_card_parser_accepts_case_commas_and_newlines():
    text = ", ".join(card.lower() for card in ZERO_DECK[:26])
    text += "\n" + " ".join(card.lower() for card in ZERO_DECK[26:])
    assert parse_cards(text) == ZERO_DECK


def test_deck_rejects_wrong_card_count():
    with pytest.raises(ValueError, match="exactly 52"):
        decode_entropy(ZERO_DECK[:-1])


def test_deck_rejects_unknown_card():
    invalid = ["1C", *ZERO_DECK[1:]]
    with pytest.raises(ValueError, match="Unknown card"):
        decode_entropy(invalid)


def test_deck_rejects_duplicate_card():
    invalid = [ZERO_DECK[1], *ZERO_DECK[1:]]
    with pytest.raises(ValueError, match="duplicate"):
        decode_entropy(invalid)


def test_deck_rejects_swapped_cards():
    invalid = ZERO_DECK.copy()
    invalid[0], invalid[1] = invalid[1], invalid[0]
    with pytest.raises(ValueError):
        decode_entropy(invalid)


def _replace_field(payload, value, width, shift):
    mask = ((1 << width) - 1) << shift
    return (payload & ~mask) | (value << shift)


@pytest.mark.parametrize(
    ("mutate", "message"),
    [
        (lambda value: value | 1, "reserved"),
        (lambda value: value ^ (1 << RESERVED_BITS), "checksum"),
        (
            lambda value: _replace_field(
                value, FORMAT_VERSION + 1, VERSION_BITS, RESERVED_BITS + TAG_BITS
            ),
            "Unsupported",
        ),
        (
            lambda value: _replace_field(
                value,
                MAGIC ^ 1,
                16,
                RESERVED_BITS + TAG_BITS + VERSION_BITS,
            ),
            "magic",
        ),
    ],
)
def test_deck_rejects_invalid_v1_metadata(mutate, message):
    payload = mutate(_pack_payload(bytes(16)))
    with pytest.raises(ValueError, match=message):
        decode_entropy(_integer_to_deck(payload))


def test_deck_rejects_permutation_outside_v1_payload_range():
    with pytest.raises(ValueError, match="225-bit"):
        decode_entropy(list(reversed(STANDARD_DECK)))


def test_payload_uses_exactly_225_bits_at_most():
    assert AUXILIARY_BITS == 97
    assert _pack_payload(bytes.fromhex("ff" * 16)).bit_length() == 225


def test_cli_round_trip_over_stdin():
    encode = subprocess.run(
        [sys.executable, "main.py", "encode", "deck"],
        cwd=PROJECT_ROOT,
        input=ZERO_MNEMONIC,
        text=True,
        capture_output=True,
        check=True,
    )
    assert encode.stderr == ""
    assert encode.stdout.split() == ZERO_DECK

    decode = subprocess.run(
        [sys.executable, "main.py", "decode", "deck"],
        cwd=PROJECT_ROOT,
        input=encode.stdout,
        text=True,
        capture_output=True,
        check=True,
    )
    assert decode.stderr == ""
    assert decode.stdout.strip() == ZERO_MNEMONIC


def test_cli_reports_invalid_input_without_traceback():
    result = subprocess.run(
        [sys.executable, "main.py", "encode", "deck"],
        cwd=PROJECT_ROOT,
        input="not a mnemonic",
        text=True,
        capture_output=True,
    )
    assert result.returncode == 2
    assert result.stderr.startswith("error:")
    assert "Traceback" not in result.stderr
