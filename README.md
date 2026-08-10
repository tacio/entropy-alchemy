# Deck Wallet

Deck Wallet is an experiment that encodes the 128 bits of entropy behind a
12-word English BIP39 mnemonic into the ordering of a standard 52-card deck.
It can also decode that exact ordering back into the original mnemonic.

> [!CAUTION]
> This project is unaudited experimental software. It is **not encryption** and
> should not be trusted with real funds. Anyone who sees or copies the card
> order can recover the mnemonic and spend the wallet's funds. Test only with a
> disposable wallet that holds no value.

## Why a deck can hold a mnemonic

A deck has `52!` possible orderings, or about 225.58 bits of capacity. A
12-word BIP39 mnemonic represents 128 bits of entropy plus a four-bit checksum.
Deck Wallet stores the entropy in a versioned 225-bit payload and regenerates
the BIP39 checksum during recovery.

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

## Encode and decode

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

## Format v1

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
second environment and verify wallet addresses. Record which end of the deck is
the top, never shuffle it, and protect it from viewing, photography, loss,
moisture, and reordered cards. The physical deck is equivalent to the mnemonic.

## Development

```bash
.venv/bin/python -m pytest -q
.venv/bin/python -m compileall -q deck_wallet.py main.py tests
```

The English 2,048-word list is vendored from the MIT-licensed
[BIP39 specification](https://github.com/bitcoin/bips/blob/master/bip-0039.mediawiki)
and its [official wordlist](https://github.com/bitcoin/bips/blob/master/bip-0039/english.txt).
The fixed deck test vector makes accidental format changes visible.

## Possible improvements

1. Search for checksum-valid repair candidates after one swapped or misplaced
   card, while never applying a repair without explicit confirmation.
2. Define multi-deck formats for 24-word mnemonics or larger BIP32 seed values.
3. Add separately versioned threshold shares so recovery requires multiple decks.
4. Provide an offline printable worksheet and clearer tamper-evident storage guidance.
5. Publish independent implementations and test vectors, obtain a security and
   format review, and produce reproducible signed releases.
