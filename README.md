# Entropy Alchemy

*Experimental transformations of BIP39 entropy into physical forms.*

Entropy Alchemy explores reversible ways to turn the abstract information
behind a BIP39 mnemonic into tangible arrangements of familiar objects: card
decks, chessboards, quipu-inspired knots, and potentially other media in the
future.

The implemented experiments encode the 128 bits of entropy behind a 12-word
English BIP39 mnemonic into the ordering of a standard 52-card deck, the
arrangement and orientation of pieces on a chessboard, or byte values tied on
colored pendant cords. Each codec decodes its exact physical representation
back into the original mnemonic.

> [!CAUTION]
> This project is unaudited experimental software. Its representations are
> **not encryption** and should not be trusted with real funds. Anyone who can
> copy a complete representation may be able to recover the mnemonic and spend
> the wallet's funds. Test only with a disposable wallet that holds no value.

## Experiments

| Medium | Status | Idea |
| --- | --- | --- |
| Standard card deck | Implemented | Encode entropy in a permutation of 52 cards |
| Chessboard | Implemented | Encode entropy in the placement and orientation of 32 pieces |
| Quipu-inspired knots | Implemented | Encode byte values through decimal knot types and positions |

Each experiment should define a deterministic, reversible, versioned format
with validation and published test vectors. The media are different; the
underlying goal is the same: preserve BIP39 entropy without pretending that an
unusual representation provides secrecy.

## Why a deck can hold a mnemonic

A deck has `52!` possible orderings, or about 225.58 bits of capacity. A
12-word BIP39 mnemonic represents 128 bits of entropy plus a four-bit checksum.
The card-deck codec stores the entropy in a versioned 225-bit payload and
regenerates the BIP39 checksum during recovery.

This project uses “mnemonic entropy” precisely. A BIP39-derived binary seed is
512 bits and does not fit in one deck. An optional BIP39 passphrase is also not
stored; it must be backed up separately.

## Why a chessboard can hold a mnemonic

One colored 16-piece chess set is not enough: even allowing missing pieces and
the specified orientations, ordinary indistinguishable pieces provide only
about 84.13 bits of state. The chess codec therefore uses both colored sides
of a standard 32-piece set.

Across an 8x8 board, allowing each piece type to range from absent through its
standard count gives
`2,682,210,745,960,470,404,760,802,361,093,493,020,497,436,168,745`
states, or about 160.876 bits. Chess format v1 uses 160 of those bits for
entropy, identification, versioning, and an integrity tag.

## Why a quipu-inspired format can hold a mnemonic

Quipu format v1 uses 23 pendant cords. Each cord stores one byte as a decimal
value from `000` through `255`, with separate hundreds, tens, and ones knot
zones. Three cords identify and version the format, sixteen store the BIP39
entropy, and four store an integrity tag. Color and spacing make missing or
reordered cords easier to notice but do not carry wallet data.

This is a new physical encoding inspired by the documented decimal structure
of numerical khipus. It is not an authentic reconstruction or a claim to have
decoded historical narrative khipus.

## Requirements and setup

Runtime use requires Python 3.10 or newer and no third-party packages. For
development, install pytest in a virtual environment:

```bash
python -m venv .venv
.venv/bin/python -m pip install -r requirements-dev.txt
```

## Encode and decode a card deck

Encode a valid 12-word English BIP39 mnemonic:

```bash
.venv/bin/python main.py encode deck
```

The terminal prompt hides the mnemonic. The command prints 52 card tokens such
as `7S`, `3C`, and `AD`, ordered from the top of the deck to the bottom. Suits
are clubs (`C`), diamonds (`D`), hearts (`H`), and spades (`S`); ten is `10`
and ace is `A`.

Recover the mnemonic from a deck:

```bash
.venv/bin/python main.py decode deck
```

Enter all cards in top-to-bottom order, separated by spaces, commas, or newlines.
Input is case-insensitive. Both commands also read stdin when piped, but be
careful: shell commands, temporary files, terminal logs, and clipboard history
can expose secrets.

Library callers can use the direct APIs:

```python
from deck_wallet import deck_to_mnemonic, mnemonic_to_deck

deck = mnemonic_to_deck(mnemonic)
recovered = deck_to_mnemonic(deck)
```

## Encode and decode a chessboard

Encode a valid mnemonic as an oriented chessboard:

```bash
.venv/bin/python main.py encode chess
```

The output is an eight-row grid in standard display order: `a8` through `h8`
on the first row, down to `a1` through `h1` on the last. A dot (`.`) is an
empty square. Pieces use a color and type, such as `WP` for a white pawn or
`BQ` for a black queen.

Knights and bishops require an orientation suffix chosen from `N`, `E`, `S`,
and `W`, for example `WN:N` or `BB:W`. Kings use `N` or `E` for their two
orientation axes: `N` represents the equivalent north/south orientations and
`E` represents east/west. Pawns, rooks, and queens have no orientation suffix.

Recover the mnemonic by entering all 64 cells in the same order:

```bash
.venv/bin/python main.py decode chess
```

Input is case-insensitive and may use spaces, commas, or newlines. Library
callers can use the direct APIs:

```python
from chess_wallet import board_to_mnemonic, mnemonic_to_board

board = mnemonic_to_board(mnemonic)
recovered = board_to_mnemonic(board)
```

## Encode and decode quipu cord values

Encode a valid mnemonic as 23 decimal cord values:

```bash
.venv/bin/python main.py encode quipu
```

The command prints six lines corresponding to the physical cord blocks:
the three-cord header, four groups of four entropy cords, and the four-cord
integrity tag. Values are padded to three decimal digits.

Recover the mnemonic by entering all 23 values in start-to-finish order:

```bash
.venv/bin/python main.py decode quipu
```

Input accepts padded or unpadded decimal values separated by spaces, commas,
or newlines. Library callers can use the direct APIs:

```python
from quipu_wallet import mnemonic_to_quipu, quipu_to_mnemonic

cords = mnemonic_to_quipu(mnemonic)
recovered = quipu_to_mnemonic(cords)
```

## Card-deck format v1

Cards use bridge order as the canonical starting deck: clubs, diamonds,
hearts, then spades, with ranks `2` through `A`. The payload is converted to a
permutation using a factoradic (mixed-radix) representation.

| Field | Bits | Purpose |
| --- | ---: | --- |
| BIP39 entropy | 128 | Original mnemonic entropy |
| Magic | 16 | `DW` format marker |
| Version | 8 | Currently `1` |
| Integrity tag | 32 | Truncated SHA-256 over a domain tag and entropy |
| Reserved | 41 | Must be zero |

The integrity tag detects accidental corruption with high probability; it does
not authenticate or conceal the deck. Decoding rejects missing, duplicate, or
unknown cards, unsupported versions, malformed metadata, and checksum failures.
Decks made by the earlier salt-based experiment are intentionally incompatible.

## Chessboard format v1

White and black pieces are distinct, but duplicate pieces of the same color
and type are not individually marked. Boards are ranked deterministically by
piece type, presence count, square combination, and orientation. The 160-bit
payload is mapped injectively across the slightly larger physical state space;
consequently, not every syntactically valid chess arrangement is a v1 codeword.

The canonical type order is `WP, WR, WN, WB, WQ, WK, BP, BR, BN, BB, BQ, BK`.
Counts are considered from the standard maximum down to zero; square
combinations are lexicographic in grid order; and orientation order is
`N, E, S, W` or `N, E` for kings. If `p` is the payload, `N` is the physical
state count above, and `M = 2^160`, its board rank is `floor(p * N / M)`.

| Field | Bits | Purpose |
| --- | ---: | --- |
| BIP39 entropy | 128 | Original mnemonic entropy |
| Magic | 8 | `C` chess-format marker |
| Version | 8 | Currently `1` |
| Integrity tag | 16 | Truncated SHA-256 over a domain tag and entropy |

The shorter chess integrity tag reflects the medium's tighter capacity. It
detects accidental corruption with high probability but does not authenticate
the board.

## Quipu format v1

Quipu cords are read from the loop-marked start of the primary cord toward its
double-stopper finish. The canonical block sizes are `3 | 4 | 4 | 4 | 4 | 4`.

| Field | Cords | Purpose |
| --- | ---: | --- |
| Magic | 2 | ASCII `QW`, decimal `081 087` |
| Version | 1 | Currently `001` |
| BIP39 entropy | 16 | Original mnemonic entropy, one byte per cord |
| Integrity tag | 4 | Truncated SHA-256 over a domain tag and entropy |

Within a cord, the hundreds, tens, and ones digit zones are 8, 18, and 28 cm
below the attachment. Zero is an empty zone, one is a figure-eight knot, and
digits two through nine are long knots with that many visible turns. This
compact use of digit knots in every zone is a deliberate modern adaptation.

The canonical color cycle is white, yellow, orange, and pink, reset at every
block. Colors are redundant: decoding depends only on cord order and knots.
See the complete [format and construction guide](docs/quipu-format-v1.md) and
the [printable knot-position template](docs/quipu-template.svg).

## Physical handling

Before relying on any experimental backup, perform a complete recovery using a
second environment and verify wallet addresses. Document the representation's
orientation and reading order, and protect it from viewing, photography, loss,
damage, and accidental rearrangement.

For cards, record which end of the deck is the top and never shuffle it. The
ordered deck is equivalent to the mnemonic; future physical codecs must make
the same risk explicit for their respective artifacts.

For chess, fix White's side at the bottom, use a standard board with `a1` dark,
and preserve every occupied square and required piece orientation. The grid is
not a legal chess position and must not be rearranged for play or display.

For quipu cords, preserve the start marker, six blocks, cord order, and all
knot positions and turn counts. Keep the artifact loosely rolled, dry, dark,
and away from heat: nylon and polyester can melt, and color is not a substitute
for the structural reading order.

## Development

```bash
.venv/bin/python -m pytest -q
.venv/bin/python -m compileall -q deck_wallet.py chess_wallet.py quipu_wallet.py main.py tests
```

The English 2,048-word list is vendored from the MIT-licensed
[BIP39 specification](https://github.com/bitcoin/bips/blob/master/bip-0039.mediawiki)
and its [official wordlist](https://github.com/bitcoin/bips/blob/master/bip-0039/english.txt).
The fixed golden vectors make accidental format changes visible.

## Roadmap

1. Establish a shared codec interface and format registry so every experiment
   follows the same encode, decode, validation, and versioning conventions.
2. Build and independently transcribe physical quipu prototypes to validate
   knot spacing, turn-count readability, and handling guidance.
3. Search for checksum-valid card repair candidates after one swapped or
   misplaced card, without applying a repair automatically.
4. Explore multi-artifact formats for 24-word mnemonics and separately
   versioned threshold shares that require multiple artifacts for recovery.
5. Create offline worksheets and handling instructions tailored to each medium.
6. Publish independent implementations and test vectors, obtain a security and
   format review, and produce reproducible signed releases.
