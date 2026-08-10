"""Command-line interface for the physical entropy experiments."""

import argparse
import getpass
import sys

from chess_wallet import board_to_mnemonic, mnemonic_to_board, parse_board
from deck_wallet import deck_to_mnemonic, mnemonic_to_deck, parse_cards


def _read_secret(prompt: str) -> str:
    if sys.stdin.isatty():
        return getpass.getpass(prompt)
    return sys.stdin.read().strip()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Encode 12-word English BIP39 entropy in a physical medium."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    encode_parser = subparsers.add_parser("encode", help="encode a mnemonic")
    encode_media = encode_parser.add_subparsers(dest="medium", required=True)
    encode_media.add_parser("deck", help="print an ordered 52-card deck")
    encode_media.add_parser("chess", help="print an oriented 8x8 chessboard")

    decode_parser = subparsers.add_parser("decode", help="decode a physical medium")
    decode_media = decode_parser.add_subparsers(dest="medium", required=True)
    decode_media.add_parser("deck", help="read an ordered 52-card deck")
    decode_media.add_parser("chess", help="read an oriented 8x8 chessboard")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        if args.command == "encode":
            mnemonic = _read_secret("12-word English BIP39 mnemonic: ")
            if args.medium == "deck":
                print(" ".join(mnemonic_to_deck(mnemonic)))
            else:
                board = mnemonic_to_board(mnemonic)
                print(
                    "\n".join(
                        " ".join(board[start : start + 8])
                        for start in range(0, 64, 8)
                    )
                )
        elif args.medium == "deck":
            card_text = _read_secret("52 cards in order: ")
            print(deck_to_mnemonic(parse_cards(card_text)))
        else:
            board_text = _read_secret("64 chessboard cells, ranks 8 through 1: ")
            print(board_to_mnemonic(parse_board(board_text)))
    except (TypeError, ValueError, RuntimeError) as exc:
        parser.exit(2, f"error: {exc}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
