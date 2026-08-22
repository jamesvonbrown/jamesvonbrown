# Legends of the Forgotten Realm

A classic text-based RPG adventure game written in Python.

## Features

- **3 Character Classes**: Choose between Warrior, Mage, or Rogue, each with unique stats
- **Turn-based Combat**: Strategic battle system with attack, defense, and healing
- **Leveling System**: Gain experience and level up to become stronger
- **Inventory Management**: Collect weapons, potions, and equipment
- **Multiple Locations**: Explore 5 different areas with varying difficulty
- **Enemies**: Fight goblins, trolls, skeletons, and even a dragon!
- **Items & Equipment**: Find and equip weapons to increase your power

## Character Classes

### Warrior
- HP: 120
- Attack: 15
- Defense: 8
- Best for: Beginners, survivability

### Mage
- HP: 80
- Attack: 20
- Defense: 3
- Best for: High damage output, risky gameplay

### Rogue
- HP: 100
- Attack: 18
- Defense: 5
- Best for: Balanced playstyle

## Locations

1. **Village of Eldoria** - Safe haven for resting and preparing
2. **Dark Forest** - Easy difficulty, goblins and wolves
3. **Ancient Cave** - Medium difficulty, trolls and spiders
4. **Cursed Ruins** - Hard difficulty, skeleton warriors and dark mages
5. **Dragon's Lair** - Boss battle against the Ancient Dragon

## How to Play

### Installation

Requires Python 3.6 or higher.

```bash
python3 rpg_game.py
```

### Gameplay

1. **Character Creation**: Choose your name and class
2. **Exploration**: Navigate through different locations
3. **Combat**: Encounter enemies and fight them in turn-based battles
4. **Inventory**: Collect and use items to aid your journey
5. **Leveling**: Defeat enemies to gain experience and level up
6. **Goal**: Defeat the Ancient Dragon to win the game!

### Combat Controls

- **Attack**: Deal damage to the enemy
- **Use Potion**: Heal yourself during battle
- **Run Away**: 50% chance to escape from combat

### Main Menu Options

1. **Look for enemies**: Search for battles in your current location
2. **Check inventory**: View your items and equipment
3. **Travel**: Move to different locations
4. **Rest**: Pay gold to restore HP at an inn (20 gold)
5. **View stats**: Check your character's detailed statistics
6. **Quit game**: Exit the game

## Tips

- Start in the Dark Forest to gain experience before tackling harder areas
- Keep healing potions in your inventory for tough battles
- Rest at the village when your HP is low
- Equip better weapons as you find them
- The Dragon's Lair is the final challenge - prepare well!

## Game Mechanics

### Combat System
- Damage dealt = (Your Attack ± random variance) - Enemy Defense
- Minimum damage is always 1
- Turn-based: You attack, then the enemy attacks

### Leveling
- Gain experience by defeating enemies
- Each level increases your max HP, attack, and defense
- Experience required increases by 50% each level

### Gold
- Earned by defeating enemies
- Used to rest at inns (20 gold per rest)
- Different enemies drop different amounts

## License

This is a free, open-source game. Feel free to modify and share!

## Credits

Created as a classic text-based RPG adventure.

Enjoy your adventure in the Forgotten Realm!

---

# Receipt Chat -- Expense Tracker

A small conversational CLI for logging expenses, with a parser that pulls
vendor, date, category, and amount out of pasted receipt text. No external
dependencies -- just the Python standard library.

## Usage

```bash
python3 receipt_chat.py
```

```
you> paste
Paste the receipt text below. Type '.' on its own line when done.
<paste your receipt text, then type . on its own line>
Parsed: 13939 SE McLoughlin, H&S 3096 Oakgrove Ch, Milwaukie, OR on 2026-08-21 -- $35.00 (Fuel)
Details: 7.849 gal, $4.459/gal, Pump #7
Save this expense? [Y/n]: y
Saved as expense #1.

you> how much did I spend on fuel this month
Total for Fuel in 2026-08: $35.00 (1 expense(s))
  Fuel         $35.00

you> list
ID  Date       Category       Amount  Vendor
#1   2026-08-21 Fuel       $   35.00  13939 SE McLoughlin, H&S 3096 Oakgrove Ch, Milwaukie, OR
#2   2026-08-22 Home & Garden $   31.98  ACE HARDWARE #11075 (m), (503) 653-2223
#3   2026-08-22 Fuel       $   25.00  VP Racing, 17873 McLoughlin, Portland OR 97267

3 expense(s), total $91.98
```

Expense #3 is a fuel pump preauth hold rather than a final "FUEL TOTAL" --
when a receipt says `PREAUTH`/`PRE-AUTHORIZED`, the description is flagged
`preauth hold -- actual charge may differ`, since the amount actually
charged for the fuel pumped can come in lower than the hold.

The `.` terminator (rather than a blank line) is deliberate -- real receipts
routinely have blank lines between the header, line items, and totals, so a
blank line can't be used to mean "done pasting".

### Commands

| Command | Description |
| --- | --- |
| `add` | Log an expense by answering a few prompts |
| `paste` | Paste raw receipt text; vendor/date/category/amount are extracted automatically |
| `list [filters]` | List expenses (`category:`, `vendor:`, `month:YYYY-MM`, `year:YYYY`, `date:YYYY-MM-DD`) |
| `total [filters]` | Show total spent, with a per-category breakdown |
| `delete <id>` | Remove an expense |
| `help` | Show the command list |
| `exit` / `quit` | Leave the chat |

You can also just type things like `"show my dining expenses"` or `"how much
did I spend on fuel this month"` and it'll figure out the filters.

### How receipt parsing works

`paste` (and the underlying `parse_receipt_text()` function) looks for a
date (2- or 4-digit year), a `TOTAL`/`FUEL TOTAL` line, and keyword hints
(fuel brands like `Chevron`/`Shell`/`VP Racing`, or words like `PUMP#`,
`UNLEAD`, `hardware`, `grocery`, `restaurant`) to guess the category. It's
tuned against three real receipts in `examples/` -- a gas station total, a
hardware store sale, and a fuel pump preauth hold -- run
`python3 receipt_chat.py --demo` to see the first one parsed without saving
anything.

There's no image/OCR step built in (no OCR library is bundled), so receipts
need to be provided as text -- either typed by hand or transcribed from a
photo.

Expenses are stored in `expenses.json` (override with `--store <path>`).

### Tests

```bash
python3 -m unittest test_receipt_chat -v
```
