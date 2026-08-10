"""Encode 12-word English BIP39 mnemonic entropy as quipu cord values.

This module defines a modern quipu-inspired format, not an authentic Inka
recording system. It is experimental encoding rather than encryption: anyone
who can read all cord values can recover the mnemonic.
"""

import hashlib
import re
from typing import Sequence

from deck_wallet import entropy_to_mnemonic, mnemonic_to_entropy


QUIPU_MAGIC = b"QW"
QUIPU_FORMAT_VERSION = 1
QUIPU_ENTROPY_BYTES = 16
QUIPU_TAG_BYTES = 4
QUIPU_HEADER_BYTES = len(QUIPU_MAGIC) + 1
QUIPU_CORD_COUNT = QUIPU_HEADER_BYTES + QUIPU_ENTROPY_BYTES + QUIPU_TAG_BYTES
QUIPU_BLOCK_SIZES = (3, 4, 4, 4, 4, 4)
QUIPU_INTEGRITY_DOMAIN = b"quipu-wallet:v1\0"


def _integrity_tag(entropy: bytes) -> bytes:
    digest = hashlib.sha256(QUIPU_INTEGRITY_DOMAIN + entropy).digest()
    return digest[:QUIPU_TAG_BYTES]


def _pack_payload(entropy: bytes) -> bytes:
    if not isinstance(entropy, bytes):
        raise TypeError("Entropy must be bytes")
    if len(entropy) != QUIPU_ENTROPY_BYTES:
        raise ValueError("Entropy must contain exactly 16 bytes (128 bits)")

    return (
        QUIPU_MAGIC
        + bytes((QUIPU_FORMAT_VERSION,))
        + entropy
        + _integrity_tag(entropy)
    )


def _normalize_cords(cords: Sequence[int]) -> bytes:
    if isinstance(cords, (str, bytes, bytearray)):
        raise TypeError("Quipu cords must be a sequence of integers, not text")
    if len(cords) != QUIPU_CORD_COUNT:
        raise ValueError(f"Quipu must contain exactly {QUIPU_CORD_COUNT} cord values")

    normalized: list[int] = []
    for value in cords:
        if isinstance(value, bool) or not isinstance(value, int):
            raise TypeError("Quipu cord values must be integers")
        if value < 0 or value > 255:
            raise ValueError("Quipu cord values must be between 0 and 255")
        normalized.append(value)
    return bytes(normalized)


def _unpack_payload(cords: Sequence[int]) -> bytes:
    payload = _normalize_cords(cords)
    if payload[: len(QUIPU_MAGIC)] != QUIPU_MAGIC:
        raise ValueError("Quipu does not contain the quipu-wallet magic marker")

    version = payload[len(QUIPU_MAGIC)]
    if version != QUIPU_FORMAT_VERSION:
        raise ValueError(f"Unsupported quipu-wallet format version: {version}")

    entropy_start = QUIPU_HEADER_BYTES
    entropy_end = entropy_start + QUIPU_ENTROPY_BYTES
    entropy = payload[entropy_start:entropy_end]
    tag = payload[entropy_end:]
    if tag != _integrity_tag(entropy):
        raise ValueError("Quipu integrity checksum does not match")
    return entropy


def encode_entropy(entropy: bytes) -> list[int]:
    """Encode exactly 128 bits of entropy as 23 byte-valued cords."""
    return list(_pack_payload(entropy))


def decode_entropy(cords: Sequence[int]) -> bytes:
    """Decode and validate 23 cord values into 128-bit entropy."""
    return _unpack_payload(cords)


def mnemonic_to_quipu(mnemonic: str) -> list[int]:
    """Encode a valid 12-word English BIP39 mnemonic as 23 cord values."""
    return encode_entropy(mnemonic_to_entropy(mnemonic))


def quipu_to_mnemonic(cords: Sequence[int]) -> str:
    """Decode a v1 quipu representation as a 12-word BIP39 mnemonic."""
    return entropy_to_mnemonic(decode_entropy(cords))


def parse_quipu(text: str) -> list[int]:
    """Parse whitespace- or comma-separated decimal cord values from 0 to 255."""
    if not isinstance(text, str):
        raise TypeError("Quipu input must be text")

    tokens = [token for token in re.split(r"[\s,]+", text.strip()) if token]
    values: list[int] = []
    for token in tokens:
        if re.fullmatch(r"[0-9]+", token) is None:
            raise ValueError(f"Invalid quipu cord value: {token}")
        value = int(token, 10)
        if value > 255:
            raise ValueError("Quipu cord values must be between 0 and 255")
        values.append(value)
    return values


def format_quipu(cords: Sequence[int]) -> str:
    """Format exactly 23 cord values as the six canonical physical blocks."""
    payload = _normalize_cords(cords)
    lines: list[str] = []
    offset = 0
    for block_size in QUIPU_BLOCK_SIZES:
        block = payload[offset : offset + block_size]
        lines.append(" ".join(f"{value:03d}" for value in block))
        offset += block_size
    return "\n".join(lines)
