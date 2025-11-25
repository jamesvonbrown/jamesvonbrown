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
