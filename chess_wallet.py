"""Encode 12-word English BIP39 mnemonic entropy as a chessboard.

This module is an experimental encoding, not encryption. Anyone who knows the
complete board arrangement can recover the mnemonic.
"""

from functools import lru_cache
import hashlib
import math
import re
from typing import Sequence

from deck_wallet import entropy_to_mnemonic, mnemonic_to_entropy


BOARD_SIZE = 64
CHESS_MAGIC = 0x43  # ASCII "C"
CHESS_FORMAT_VERSION = 1
CHESS_TAG_BITS = 16
CHESS_MAGIC_BITS = 8
CHESS_VERSION_BITS = 8
CHESS_AUXILIARY_BITS = CHESS_TAG_BITS + CHESS_MAGIC_BITS + CHESS_VERSION_BITS
CHESS_PAYLOAD_BITS = 160
CHESS_INTEGRITY_DOMAIN = b"chess-wallet:v1\0"

# Duplicate pieces of the same color and type are physically indistinguishable.
# Orientations are canonical equivalence classes, not individual piece labels.
PIECE_SPECS = (
    ("WP", 8, ("",)),
    ("WR", 2, ("",)),
    ("WN", 2, ("N", "E", "S", "W")),
    ("WB", 2, ("N", "E", "S", "W")),
    ("WQ", 1, ("",)),
    ("WK", 1, ("N", "E")),
    ("BP", 8, ("",)),
    ("BR", 2, ("",)),
    ("BN", 2, ("N", "E", "S", "W")),
    ("BB", 2, ("N", "E", "S", "W")),
    ("BQ", 1, ("",)),
    ("BK", 1, ("N", "E")),
)
PIECE_SPEC_BY_TOKEN = {
    token: (limit, orientations)
    for token, limit, orientations in PIECE_SPECS
}


def _integrity_tag(entropy: bytes) -> int:
    digest = hashlib.sha256(CHESS_INTEGRITY_DOMAIN + entropy).digest()
    return int.from_bytes(digest[:2], "big")


def _pack_payload(entropy: bytes) -> int:
    if not isinstance(entropy, bytes):
        raise TypeError("Entropy must be bytes")
    if len(entropy) != 16:
        raise ValueError("Entropy must contain exactly 16 bytes (128 bits)")

    return (
        (int.from_bytes(entropy, "big") << CHESS_AUXILIARY_BITS)
        | (CHESS_MAGIC << (CHESS_VERSION_BITS + CHESS_TAG_BITS))
        | (CHESS_FORMAT_VERSION << CHESS_TAG_BITS)
        | _integrity_tag(entropy)
    )


def _unpack_payload(payload: int) -> bytes:
    if payload < 0 or payload >= 1 << CHESS_PAYLOAD_BITS:
        raise ValueError("Board does not contain a valid 160-bit chess-wallet payload")

    tag = payload & ((1 << CHESS_TAG_BITS) - 1)
    version = (payload >> CHESS_TAG_BITS) & ((1 << CHESS_VERSION_BITS) - 1)
    magic = (
        payload >> (CHESS_TAG_BITS + CHESS_VERSION_BITS)
    ) & ((1 << CHESS_MAGIC_BITS) - 1)
    entropy_value = payload >> CHESS_AUXILIARY_BITS

    if magic != CHESS_MAGIC:
        raise ValueError("Board does not contain the chess-wallet magic marker")
    if version != CHESS_FORMAT_VERSION:
        raise ValueError(f"Unsupported chess-wallet format version: {version}")

    entropy = entropy_value.to_bytes(16, "big")
    if tag != _integrity_tag(entropy):
        raise ValueError("Board integrity checksum does not match")
    return entropy


@lru_cache(maxsize=None)
def _count_states(spec_index: int, free_squares: int) -> int:
    """Count suffix configurations for the remaining piece types."""
    if spec_index == len(PIECE_SPECS):
        return 1

    _, limit, orientations = PIECE_SPECS[spec_index]
    orientation_count = len(orientations)
    return sum(
        math.comb(free_squares, count)
        * orientation_count**count
        * _count_states(spec_index + 1, free_squares - count)
        for count in range(limit + 1)
    )


CHESS_STATE_COUNT = _count_states(0, BOARD_SIZE)
CHESS_PAYLOAD_COUNT = 1 << CHESS_PAYLOAD_BITS


def _combination_rank(selected: Sequence[int], population: int) -> int:
    """Return the lexicographic rank of a sorted fixed-size combination."""
    rank = 0
    previous = -1
    selection_size = len(selected)
    for offset, value in enumerate(selected):
        for candidate in range(previous + 1, value):
            rank += math.comb(
                population - candidate - 1,
                selection_size - offset - 1,
            )
        previous = value
    return rank


def _unrank_combination(rank: int, population: int, selection_size: int) -> list[int]:
    """Return the sorted combination at a zero-based lexicographic rank."""
    selected: list[int] = []
    candidate = 0
    for offset in range(selection_size):
        while True:
            block = math.comb(
                population - candidate - 1,
                selection_size - offset - 1,
            )
            if rank < block:
                selected.append(candidate)
                candidate += 1
                break
            rank -= block
            candidate += 1
    return selected


def _normalize_cell(cell: str) -> str:
    if not isinstance(cell, str):
        raise TypeError("Board cells must be text tokens")

    normalized = cell.strip().upper()
    if normalized == ".":
        return normalized

    parts = normalized.split(":")
    if len(parts) > 2 or parts[0] not in PIECE_SPEC_BY_TOKEN:
        raise ValueError(f"Unknown chess cell token: {cell}")

    base = parts[0]
    orientations = PIECE_SPEC_BY_TOKEN[base][1]
    supplied_orientation = parts[1] if len(parts) == 2 else ""
    if orientations != ("",) and len(parts) == 1:
        allowed = ", ".join(orientations)
        raise ValueError(f"{base} requires an orientation: {allowed}")
    if supplied_orientation not in orientations:
        if orientations == ("",):
            raise ValueError(f"{base} does not accept an orientation")
        allowed = ", ".join(orientations)
        raise ValueError(f"{base} orientation must be one of: {allowed}")
    return base if supplied_orientation == "" else f"{base}:{supplied_orientation}"


def _normalize_board(cells: Sequence[str]) -> list[str]:
    if isinstance(cells, (str, bytes)):
        raise TypeError("Board must be a sequence of 64 cell tokens, not text")
    if len(cells) != BOARD_SIZE:
        raise ValueError("Board must contain exactly 64 cell tokens")
    return [_normalize_cell(cell) for cell in cells]


def _board_to_integer(cells: Sequence[str]) -> int:
    """Rank a board in the canonical chess-wallet state ordering."""
    board = _normalize_board(cells)
    available = list(range(BOARD_SIZE))
    rank = 0

    for spec_index, (token, limit, orientations) in enumerate(PIECE_SPECS):
        occupied = [
            square
            for square in available
            if board[square].split(":", 1)[0] == token
        ]
        count = len(occupied)
        if count > limit:
            raise ValueError(f"Board contains more than {limit} {token} pieces")

        orientation_count = len(orientations)
        for earlier_count in range(limit, count, -1):
            rank += (
                math.comb(len(available), earlier_count)
                * orientation_count**earlier_count
                * _count_states(spec_index + 1, len(available) - earlier_count)
            )

        available_positions = {square: index for index, square in enumerate(available)}
        selected = [available_positions[square] for square in occupied]
        combination_rank = _combination_rank(selected, len(available))

        orientation_rank = 0
        for square in occupied:
            orientation = board[square].partition(":")[2]
            orientation_rank = (
                orientation_rank * orientation_count + orientations.index(orientation)
            )

        configuration_rank = (
            combination_rank * orientation_count**count + orientation_rank
        )
        suffix_count = _count_states(spec_index + 1, len(available) - count)
        rank += configuration_rank * suffix_count

        occupied_set = set(occupied)
        available = [square for square in available if square not in occupied_set]

    return rank


def _integer_to_board(rank: int) -> list[str]:
    """Unrank a canonical chess-wallet state into 64 cell tokens."""
    if rank < 0 or rank >= CHESS_STATE_COUNT:
        raise ValueError("Chessboard rank is outside the physical state space")

    board = ["."] * BOARD_SIZE
    available = list(range(BOARD_SIZE))

    for spec_index, (token, limit, orientations) in enumerate(PIECE_SPECS):
        orientation_count = len(orientations)
        for count in range(limit, -1, -1):
            suffix_count = _count_states(spec_index + 1, len(available) - count)
            block_size = (
                math.comb(len(available), count)
                * orientation_count**count
                * suffix_count
            )
            if rank < block_size:
                break
            rank -= block_size

        configuration_rank, rank = divmod(rank, suffix_count)
        orientation_space = orientation_count**count
        combination_rank, orientation_rank = divmod(
            configuration_rank,
            orientation_space,
        )
        selected = _unrank_combination(
            combination_rank,
            len(available),
            count,
        )

        orientation_digits = [0] * count
        for index in range(count - 1, -1, -1):
            orientation_rank, orientation_digits[index] = divmod(
                orientation_rank,
                orientation_count,
            )

        occupied = [available[position] for position in selected]
        for square, orientation_index in zip(occupied, orientation_digits):
            orientation = orientations[orientation_index]
            board[square] = token if orientation == "" else f"{token}:{orientation}"

        occupied_set = set(occupied)
        available = [square for square in available if square not in occupied_set]

    if rank:
        raise AssertionError("Chessboard unranking left an unused suffix rank")
    return board


def _payload_to_board_rank(payload: int) -> int:
    if payload < 0 or payload >= CHESS_PAYLOAD_COUNT:
        raise ValueError("Payload must fit within 160 bits")
    return payload * CHESS_STATE_COUNT // CHESS_PAYLOAD_COUNT


def _board_rank_to_payload(rank: int) -> int:
    if rank < 0 or rank >= CHESS_STATE_COUNT:
        raise ValueError("Chessboard rank is outside the physical state space")

    payload = (
        rank * CHESS_PAYLOAD_COUNT + CHESS_STATE_COUNT - 1
    ) // CHESS_STATE_COUNT
    if (
        payload >= CHESS_PAYLOAD_COUNT
        or _payload_to_board_rank(payload) != rank
    ):
        raise ValueError("Board is not a chess-wallet v1 codeword")
    return payload


def encode_entropy(entropy: bytes) -> list[str]:
    """Encode exactly 128 bits of entropy as 64 chessboard cell tokens."""
    payload = _pack_payload(entropy)
    return _integer_to_board(_payload_to_board_rank(payload))


def decode_entropy(cells: Sequence[str]) -> bytes:
    """Decode and validate 64 chessboard cell tokens into 128-bit entropy."""
    rank = _board_to_integer(cells)
    return _unpack_payload(_board_rank_to_payload(rank))


def mnemonic_to_board(mnemonic: str) -> list[str]:
    """Encode a valid 12-word English BIP39 mnemonic as a chessboard."""
    return encode_entropy(mnemonic_to_entropy(mnemonic))


def board_to_mnemonic(cells: Sequence[str]) -> str:
    """Decode a v1 chessboard as a 12-word English BIP39 mnemonic."""
    return entropy_to_mnemonic(decode_entropy(cells))


def parse_board(text: str) -> list[str]:
    """Parse a whitespace- or comma-separated 64-cell chessboard grid."""
    if not isinstance(text, str):
        raise TypeError("Board input must be text")
    tokens = [token for token in re.split(r"[\s,]+", text.strip()) if token]
    return [_normalize_cell(token) for token in tokens]
