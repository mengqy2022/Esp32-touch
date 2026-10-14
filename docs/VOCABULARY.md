# Vocab Lab and SD data

Vocab Lab is an existing offline-first study tool. The dashboard update places
it under **OTHER → VOCAB LAB** and preserves its study engine and SD format.

## Prepare the SD card

Copy the contents of `sdcard_template/` to the root of a FAT32 MicroSD card.
`/sdcard` below is the firmware mount point, not an extra folder to create on the card.

```text
/sdcard/
├── INVENTORY.CSV
├── BOM_IN/
├── BOM_OUT/
└── vocabulary/
    ├── books/          UTF-8 wordbook CSVs
    ├── progress/       Generated per-book study records
    └── cache/          Generated download/conversion temporary data
```

Insert the card and use SYSTEM → SD CHECK to verify it is mounted. Then open
OTHER → VOCAB LAB → BOOKS → starter. Generated progress/cache directories may be
created by the application; they contain local learning data, not public templates.

## Wordbook format

```csv
word,phonetic,meaning,example
ability,/əˈbɪləti/,能力；才能,Practice improves your ability.
```

Use UTF-8 and CSV quoting for fields containing commas. Keep `word` and `meaning`
populated. The converter accepts compatible column aliases and compatible JSON
word arrays, normalizes whitespace and writes the expected four columns:

```sh
python tools/vocab_convert.py input.json build/my_book.csv
```

Copy `my_book.csv` into SD `vocabulary/books/`. The firmware reads and indexes
wordbooks rather than keeping a complete book in RAM. Screen font coverage and
field sizes are limited; keep examples suitable for a 320×240 display.

## Study workflow

- **BOOKS** selects local books and retains network download entries. Downloading
  requires Wi-Fi, an SD card and availability of the upstream data source.
- **LEARN** displays cards, meanings and examples; AGAIN/SHOW/KNOWN drive review.
- **DICTATION** uses the existing touchscreen writing/input and spelling-check
  workflow. It is not a general-purpose handwriting OCR service.
- **PLAN** adjusts the daily study target; per-book progress lives on SD and the
  target setting is persisted in NVS.

Local study works without a PC or network. Back from study subpages returns to
Vocab Lab, then to OTHER. Commercial wordbooks, courses or user progress must not
be committed. See [third-party notices](THIRD_PARTY_NOTICES.md).
