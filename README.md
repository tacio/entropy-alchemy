# Entropy Alchemy

*Experimental transformations of BIP39 entropy into physical forms.*

Entropy Alchemy explores reversible ways to turn the abstract information
behind a BIP39 mnemonic into tangible arrangements of familiar objects: card
decks today, and potentially chessboards, quipus, knots, tiles, or other media
in the future.

The first implemented experiment is the original **Deck Wallet** codec. It
encodes the 128 bits of entropy behind a 12-word English BIP39 mnemonic into
the ordering of a standard 52-card deck, then decodes that exact ordering back
into the original mnemonic.

> [!CAUTION]
> This project is unaudited experimental software. Its representations are
> **not encryption** and should not be trusted with real funds. Anyone who can
> copy a complete representation may be able to recover the mnemonic and spend
> the wallet's funds. Test only with a disposable wallet that holds no value.

## Experiments

| Medium | Status | Idea |
| --- | --- | --- |
| Standard card deck | Implemented | Encode entropy in a permutation of 52 cards |
| Chessboard | Concept | Encode entropy through a defined arrangement of pieces |
| Quipu or knots | Concept | Encode entropy through discrete knot types and positions |

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
.venv/bin/python main.py encode
```

The terminal prompt hides the mnemonic. The command prints 52 card tokens such
as `7S`, `3C`, and `AD`, ordered from the top of the deck to the bottom. Suits
are clubs (`C`), diamonds (`D`), hearts (`H`), and spades (`S`); ten is `10`
and ace is `A`.

Recover the mnemonic from a deck:

```bash
.venv/bin/python main.py decode
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

## Physical handling

Before relying on any experimental backup, perform a complete recovery using a
second environment and verify wallet addresses. Document the representation's
orientation and reading order, and protect it from viewing, photography, loss,
damage, and accidental rearrangement.

For cards, record which end of the deck is the top and never shuffle it. The
ordered deck is equivalent to the mnemonic; future physical codecs must make
the same risk explicit for their respective artifacts.

## Development

```bash
.venv/bin/python -m pytest -q
.venv/bin/python -m compileall -q deck_wallet.py main.py tests
```

The English 2,048-word list is vendored from the MIT-licensed
[BIP39 specification](https://github.com/bitcoin/bips/blob/master/bip-0039.mediawiki)
and its [official wordlist](https://github.com/bitcoin/bips/blob/master/bip-0039/english.txt).
The fixed deck test vector makes accidental format changes visible.

## Roadmap

1. Establish a shared codec interface and format registry so every experiment
   follows the same encode, decode, validation, and versioning conventions.
2. Prototype chessboard and quipu representations with explicit reading order,
   capacity calculations, and realistic handling constraints.
3. Search for checksum-valid card repair candidates after one swapped or
   misplaced card, without applying a repair automatically.
4. Explore multi-artifact formats for 24-word mnemonics and separately
   versioned threshold shares that require multiple artifacts for recovery.
5. Create offline worksheets and handling instructions tailored to each medium.
6. Publish independent implementations and test vectors, obtain a security and
   format review, and produce reproducible signed releases.
