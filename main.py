"""Command-line interface for the deck-wallet experiment."""

import argparse
import getpass
import sys

from deck_wallet import deck_to_mnemonic, mnemonic_to_deck, parse_cards


def _read_secret(prompt: str) -> str:
    if sys.stdin.isatty():
        return getpass.getpass(prompt)
    return sys.stdin.read().strip()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Encode 12-word English BIP39 entropy as an ordered deck."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("encode", help="read a mnemonic and print 52 card tokens")
    subparsers.add_parser("decode", help="read 52 card tokens and print a mnemonic")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        if args.command == "encode":
            mnemonic = _read_secret("12-word English BIP39 mnemonic: ")
            print(" ".join(mnemonic_to_deck(mnemonic)))
        else:
            card_text = _read_secret("52 cards in order: ")
            print(deck_to_mnemonic(parse_cards(card_text)))
    except (TypeError, ValueError, RuntimeError) as exc:
        parser.exit(2, f"error: {exc}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
