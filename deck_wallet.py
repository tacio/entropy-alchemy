"""Encode 12-word English BIP39 mnemonic entropy as a card permutation.

This module is an experimental encoding, not encryption. Anyone who knows the
deck order can recover the mnemonic.
"""

from functools import lru_cache
import hashlib
from pathlib import Path
import re
from typing import Sequence
import unicodedata


RANKS = ("2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K", "A")
SUITS = ("C", "D", "H", "S")
STANDARD_DECK = tuple(f"{rank}{suit}" for suit in SUITS for rank in RANKS)

MAGIC = 0x4457  # ASCII "DW"
FORMAT_VERSION = 1
ENTROPY_BYTES = 16
RESERVED_BITS = 41
TAG_BITS = 32
VERSION_BITS = 8
MAGIC_BITS = 16
AUXILIARY_BITS = RESERVED_BITS + TAG_BITS + VERSION_BITS + MAGIC_BITS
PAYLOAD_BITS = ENTROPY_BYTES * 8 + AUXILIARY_BITS
INTEGRITY_DOMAIN = b"deck-wallet:v1\0"
WORDLIST_PATH = Path(__file__).with_name("wordlists") / "english.txt"


@lru_cache(maxsize=1)
def _wordlist() -> tuple[str, ...]:
    """Load and validate the vendored English BIP39 wordlist."""
    try:
        words = tuple(WORDLIST_PATH.read_text(encoding="utf-8").splitlines())
    except OSError as exc:
        raise RuntimeError(f"Unable to load BIP39 wordlist: {exc}") from exc

    if len(words) != 2048 or len(set(words)) != 2048:
        raise RuntimeError("BIP39 wordlist must contain 2,048 unique words")
    return words


@lru_cache(maxsize=1)
def _word_indexes() -> dict[str, int]:
    return {word: index for index, word in enumerate(_wordlist())}


def mnemonic_to_entropy(mnemonic: str) -> bytes:
    """Validate a 12-word English BIP39 mnemonic and return its entropy."""
    if not isinstance(mnemonic, str):
        raise TypeError("Mnemonic must be text")

    normalized = unicodedata.normalize("NFKD", mnemonic).lower()
    words = normalized.split()
    if len(words) != 12:
        raise ValueError("Mnemonic must contain exactly 12 words")

    indexes = _word_indexes()
    value = 0
    for word in words:
        try:
            index = indexes[word]
        except KeyError as exc:
            raise ValueError(f"Unknown English BIP39 word: {word}") from exc
        value = (value << 11) | index

    entropy_value = value >> 4
    supplied_checksum = value & 0xF
    entropy = entropy_value.to_bytes(ENTROPY_BYTES, "big")
    expected_checksum = hashlib.sha256(entropy).digest()[0] >> 4
    if supplied_checksum != expected_checksum:
        raise ValueError("Mnemonic has an invalid BIP39 checksum")
    return entropy


def entropy_to_mnemonic(entropy: bytes) -> str:
    """Convert exactly 128 bits of entropy to an English BIP39 mnemonic."""
    if not isinstance(entropy, bytes):
        raise TypeError("Entropy must be bytes")
    if len(entropy) != ENTROPY_BYTES:
        raise ValueError("Entropy must contain exactly 16 bytes (128 bits)")

    entropy_value = int.from_bytes(entropy, "big")
    checksum = hashlib.sha256(entropy).digest()[0] >> 4
    value = (entropy_value << 4) | checksum
    words = _wordlist()
    return " ".join(words[(value >> shift) & 0x7FF] for shift in range(121, -1, -11))


def _integrity_tag(entropy: bytes) -> int:
    digest = hashlib.sha256(INTEGRITY_DOMAIN + entropy).digest()
    return int.from_bytes(digest[:4], "big")


def _pack_payload(entropy: bytes) -> int:
    if not isinstance(entropy, bytes):
        raise TypeError("Entropy must be bytes")
    if len(entropy) != ENTROPY_BYTES:
        raise ValueError("Entropy must contain exactly 16 bytes (128 bits)")

    return (
        (int.from_bytes(entropy, "big") << AUXILIARY_BITS)
        | (MAGIC << (VERSION_BITS + TAG_BITS + RESERVED_BITS))
        | (FORMAT_VERSION << (TAG_BITS + RESERVED_BITS))
        | (_integrity_tag(entropy) << RESERVED_BITS)
    )


def _unpack_payload(payload: int) -> bytes:
    if payload < 0 or payload >= 1 << PAYLOAD_BITS:
        raise ValueError("Deck does not contain a valid 225-bit deck-wallet payload")

    reserved_mask = (1 << RESERVED_BITS) - 1
    reserved = payload & reserved_mask
    tag = (payload >> RESERVED_BITS) & ((1 << TAG_BITS) - 1)
    version = (payload >> (RESERVED_BITS + TAG_BITS)) & 0xFF
    magic = (payload >> (RESERVED_BITS + TAG_BITS + VERSION_BITS)) & 0xFFFF
    entropy_value = payload >> AUXILIARY_BITS

    if magic != MAGIC:
        raise ValueError("Deck does not contain the deck-wallet magic marker")
    if version != FORMAT_VERSION:
        raise ValueError(f"Unsupported deck-wallet format version: {version}")
    if reserved != 0:
        raise ValueError("Deck has nonzero reserved bits")

    entropy = entropy_value.to_bytes(ENTROPY_BYTES, "big")
    if tag != _integrity_tag(entropy):
        raise ValueError("Deck integrity checksum does not match")
    return entropy


def _integer_to_deck(payload: int) -> list[str]:
    if payload < 0 or payload >= 1 << PAYLOAD_BITS:
        raise ValueError("Payload must fit within 225 bits")

    remaining = list(STANDARD_DECK)
    permutation: list[str] = []
    for base in range(len(remaining), 0, -1):
        payload, index = divmod(payload, base)
        permutation.append(remaining.pop(index))

    if payload:
        raise ValueError("Payload exceeds the capacity of a 52-card deck")
    return permutation


def _deck_to_integer(cards: Sequence[str]) -> int:
    if isinstance(cards, (str, bytes)):
        raise TypeError("Cards must be a sequence of card tokens, not text")
    if len(cards) != len(STANDARD_DECK):
        raise ValueError("Deck must contain exactly 52 cards")

    normalized = [card.strip().upper() for card in cards]
    unknown = sorted(set(normalized) - set(STANDARD_DECK))
    if unknown:
        raise ValueError(f"Unknown card token(s): {', '.join(unknown)}")
    if len(set(normalized)) != len(STANDARD_DECK):
        raise ValueError("Deck contains duplicate cards")

    remaining = list(STANDARD_DECK)
    digits: list[int] = []
    for card in normalized:
        index = remaining.index(card)
        digits.append(index)
        remaining.pop(index)

    payload = 0
    for base, digit in zip(range(1, len(STANDARD_DECK) + 1), reversed(digits)):
        payload = payload * base + digit
    return payload


def encode_entropy(entropy: bytes) -> list[str]:
    """Encode 128 bits of entropy as an ordered standard deck."""
    return _integer_to_deck(_pack_payload(entropy))


def decode_entropy(cards: Sequence[str]) -> bytes:
    """Decode and validate an ordered standard deck into 128-bit entropy."""
    return _unpack_payload(_deck_to_integer(cards))


def mnemonic_to_deck(mnemonic: str) -> list[str]:
    """Encode a valid 12-word English BIP39 mnemonic as a deck ordering."""
    return encode_entropy(mnemonic_to_entropy(mnemonic))


def deck_to_mnemonic(cards: Sequence[str]) -> str:
    """Decode a v1 deck ordering as a 12-word English BIP39 mnemonic."""
    return entropy_to_mnemonic(decode_entropy(cards))


def parse_cards(text: str) -> list[str]:
    """Parse whitespace- or comma-separated card tokens."""
    if not isinstance(text, str):
        raise TypeError("Card input must be text")
    return [token.upper() for token in re.split(r"[\s,]+", text.strip()) if token]
