# Quipu-inspired wallet format v1

This document specifies a modern physical encoding for the 128 bits of entropy
behind a 12-word English BIP39 mnemonic. It borrows the primary-cord, pendant,
grouping, color, decimal-position, figure-eight, and long-knot ideas associated
with numerical khipus. It is not an authentic reconstruction of an Inka record
and makes no claim about still-undeciphered historical meanings.

The format is experimental encoding, not encryption. Anyone who can inspect
and transcribe the complete artifact can recover the mnemonic. Do not use this
unaudited experiment to protect real funds.

## Research basis

The National Museum of the American Indian describes Inka khipus as a
horizontal primary string with numerous hanging strings whose length, knots,
twine technology, and color contributed to the record:

- <https://americanindian.si.edu/exhibitions/infinityofnations/andes/143866.html>

The best-understood numeric grammar is decimal and positional. A figure-eight
knot represents one in the units position, long knots with two through nine
turns represent the corresponding units, and higher decimal positions
traditionally use clusters of overhand knots:

- <https://smarthistory.org/inka-khipu/>
- <https://www.khipufieldguide.com/guidebook/KhipuSigns.html>

Khipus also exhibit cord groups, multiple attachment forms, twist directions,
and several color treatments. V1 deliberately leaves attachment direction,
twist, and color outside the data alphabet so that they cannot silently change
wallet entropy.

Braided #15 or #18 mason line is readily available around 1.5 to 1.6 mm. Nylon
products are sold in many colors and UV-stabilized variants; braided polyester
has lower stretch and is also suitable:

- <https://ropeshop.com/shop/nylon-rope/braided-nylon-twine/>
- <https://sgtknots.com/products/braided-poly-mason-line>

## Logical payload

The artifact contains exactly 23 pendant cords, each carrying one byte as a
decimal value from `000` through `255`.

| Cord indexes | Count | Contents |
| --- | ---: | --- |
| 0–1 | 2 | ASCII magic `QW` (`081 087`) |
| 2 | 1 | Version `001` |
| 3–18 | 16 | BIP39 entropy bytes in order |
| 19–22 | 4 | Integrity tag |

The integrity tag is the first four bytes of:

```text
SHA-256("quipu-wallet:v1\0" || entropy)
```

The NUL after `v1` is one zero byte, not the two printed characters `\` and
`0`. The integrity tag detects accidental corruption with high probability.
It is not authentication and does not conceal the entropy.

Decoding must reject:

- a count other than 23 cords;
- a cord value outside `000–255`;
- magic other than `081 087`;
- a version other than `001`; or
- an integrity-tag mismatch.

V1 never repairs or guesses an invalid value.

## Physical layout

Use a dark primary cord approximately 70 cm long and 3–4 mm thick. Mark its
start with a closed loop and its finish with two stopper knots. With the start
at the left and the pendants hanging downward, attach the cords using identical
lark's-head hitches.

Divide the pendants into six blocks:

```text
header       entropy 0–3  entropy 4–7  entropy 8–11  entropy 12–15  tag
W  Y  O      W Y O P      W Y O P      W Y O P       W Y O P        W Y O P
081 087 001  byte values   byte values  byte values   byte values    checksum
```

Use attachment centers approximately 15 mm apart inside a block and 45 mm
between the last cord of one block and the first cord of the next. Reset the
color cycle `white, yellow, orange, pink` at every block.

Color is only a transcription aid. A physically complete artifact remains
decodable if colors fade or cannot be distinguished. Alternative high-contrast
colors are noncanonical but do not change the stored values.

## Encoding one cord

Write the byte as exactly three decimal digits. For example, byte 7 is `007`,
byte 42 is `042`, and byte 255 is `255`.

Measure down from the point where the pendant exits its attachment to the
primary cord. Place the midpoint of each data knot in its corresponding band:

| Digit | Center | Accepted band |
| --- | ---: | ---: |
| Hundreds | 8 cm | 6–10 cm |
| Tens | 18 cm | 16–20 cm |
| Ones | 28 cm | 26–30 cm |

Use this modern compact digit alphabet in all three bands:

| Digit | Physical mark |
| ---: | --- |
| 0 | No knot in the band |
| 1 | One figure-eight knot |
| 2–9 | One long/barrel knot with 2–9 visible turns |

Knot handedness does not carry data. Tie all knots consistently and firmly
enough that the turn count remains visible. Finish each pendant at least 6 cm
below the bottom of the ones band. Fused, whipped, or sewn end treatments must
remain outside every data band and carry no information.

The printable [knot-position template](quipu-template.svg) is 38 cm long. Print
it at 100% on A3 paper in landscape orientation or use tiled printing. Confirm
the included 10 cm scale before relying on it.

## Golden vector

For zero entropy, corresponding to `abandon` eleven times followed by `about`,
the canonical six blocks are:

```text
081 087 001
000 000 000 000
000 000 000 000
000 000 000 000
000 000 000 000
145 046 122 164
```

## Construction and recovery ceremony

1. Work offline with a disposable test mnemonic.
2. Generate the six blocks with `main.py encode quipu`.
3. Lay every pendant against the printed template and tie its three digits.
4. Recount the cords and verify each block's color cycle before decoding.
5. Have a second person transcribe the artifact without seeing the mnemonic.
6. Run `main.py decode quipu` on the transcription and compare the result.
7. Deliberately test a changed turn count, a swapped cord, and a missing cord;
   each damaged transcription must be rejected.

Store the completed artifact loosely rolled rather than sharply folded. Keep
it dry, dark, clean, and protected from heat, abrasion, photography, and
unauthorized inspection. Preserve an offline copy of this specification and
the decoder separately from the artifact.
