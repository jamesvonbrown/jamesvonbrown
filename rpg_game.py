#!/usr/bin/env python3
"""
Fantasy RPG Text Adventure Game
A classic text-based RPG with character classes, combat, inventory, and exploration.
"""

import random
import sys
from typing import List, Dict, Optional


class Item:
    """Base class for all items in the game."""

    def __init__(self, name: str, description: str, item_type: str):
        self.name = name
        self.description = description
        self.item_type = item_type


class Weapon(Item):
    """Weapon item that increases attack damage."""

    def __init__(self, name: str, description: str, damage: int):
        super().__init__(name, description, "weapon")
        self.damage = damage


class Potion(Item):
    """Healing potion item."""

    def __init__(self, name: str, description: str, heal_amount: int):
        super().__init__(name, description, "potion")
        self.heal_amount = heal_amount


class Character:
    """Base class for all characters (player and enemies)."""

    def __init__(self, name: str, hp: int, max_hp: int, attack: int, defense: int):
        self.name = name
        self.hp = hp
        self.max_hp = max_hp
        self.attack = attack
        self.defense = defense
        self.is_alive = True

    def take_damage(self, damage: int):
        """Apply damage to the character."""
        actual_damage = max(1, damage - self.defense)
        self.hp -= actual_damage
        if self.hp <= 0:
            self.hp = 0
            self.is_alive = False
        return actual_damage

    def heal(self, amount: int):
        """Heal the character."""
        self.hp = min(self.hp + amount, self.max_hp)

    def attack_enemy(self, target: 'Character') -> int:
        """Attack another character."""
        damage = random.randint(self.attack - 2, self.attack + 2)
        return target.take_damage(damage)


class Player(Character):
    """Player character with inventory and experience."""

    def __init__(self, name: str, character_class: str):
        self.character_class = character_class
        self.level = 1
        self.exp = 0
        self.exp_to_next_level = 100
        self.inventory: List[Item] = []
        self.equipped_weapon: Optional[Weapon] = None
        self.gold = 50

        if character_class == "Warrior":
            super().__init__(name, 120, 120, 15, 8)
        elif character_class == "Mage":
            super().__init__(name, 80, 80, 20, 3)
        elif character_class == "Rogue":
            super().__init__(name, 100, 100, 18, 5)

    def add_item(self, item: Item):
        """Add an item to inventory."""
        self.inventory.append(item)

    def use_potion(self, potion: Potion):
        """Use a healing potion."""
        if potion in self.inventory:
            self.heal(potion.heal_amount)
            self.inventory.remove(potion)
            return True
        return False

    def equip_weapon(self, weapon: Weapon):
        """Equip a weapon."""
        if self.equipped_weapon:
            self.attack -= self.equipped_weapon.damage
        self.equipped_weapon = weapon
        self.attack += weapon.damage

    def gain_exp(self, amount: int):
        """Gain experience points and possibly level up."""
        self.exp += amount
        if self.exp >= self.exp_to_next_level:
            self.level_up()

    def level_up(self):
        """Level up the character."""
        self.level += 1
        self.exp = 0
        self.exp_to_next_level = int(self.exp_to_next_level * 1.5)

        hp_gain = 20
        attack_gain = 3
        defense_gain = 2

        self.max_hp += hp_gain
        self.hp = self.max_hp
        self.attack += attack_gain
        self.defense += defense_gain

        return hp_gain, attack_gain, defense_gain


class Enemy(Character):
    """Enemy character."""

    def __init__(self, name: str, hp: int, attack: int, defense: int, exp_reward: int, gold_reward: int):
        super().__init__(name, hp, hp, attack, defense)
        self.exp_reward = exp_reward
        self.gold_reward = gold_reward


class Location:
    """A location in the game world."""

    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description
        self.enemies: List[Enemy] = []
        self.items: List[Item] = []
        self.visited = False


class Game:
    """Main game engine."""

    def __init__(self):
        self.player: Optional[Player] = None
        self.current_location: Optional[Location] = None
        self.locations: Dict[str, Location] = {}
        self.game_over = False
        self.initialize_game_world()

    def initialize_game_world(self):
        """Initialize all locations, items, and enemies."""

        village = Location(
            "Village of Eldoria",
            "A peaceful village with cobblestone streets. You see a tavern and a blacksmith shop."
        )

        forest = Location(
            "Dark Forest",
            "A dense, ominous forest. Strange sounds echo through the trees."
        )
        forest.enemies = [
            Enemy("Goblin Scout", 30, 8, 2, 50, 20),
            Enemy("Wild Wolf", 25, 10, 1, 40, 15)
        ]
        forest.items = [
            Potion("Health Potion", "Restores 50 HP", 50)
        ]

        cave = Location(
            "Ancient Cave",
            "A mysterious cave with glowing crystals on the walls."
        )
        cave.enemies = [
            Enemy("Cave Troll", 60, 12, 5, 100, 50),
            Enemy("Giant Spider", 40, 15, 3, 80, 30)
        ]
        cave.items = [
            Weapon("Iron Sword", "A sturdy iron blade", 8),
            Potion("Health Potion", "Restores 50 HP", 50)
        ]

        ruins = Location(
            "Cursed Ruins",
            "Ancient ruins filled with dark magic and danger."
        )
        ruins.enemies = [
            Enemy("Skeleton Warrior", 70, 18, 6, 150, 75),
            Enemy("Dark Mage", 50, 22, 4, 180, 100)
        ]
        ruins.items = [
            Weapon("Enchanted Staff", "A magical staff crackling with energy", 15),
            Potion("Greater Health Potion", "Restores 100 HP", 100)
        ]

        dragon_lair = Location(
            "Dragon's Lair",
            "A massive cavern filled with treasure and the overwhelming presence of a dragon."
        )
        dragon_lair.enemies = [
            Enemy("Ancient Dragon", 200, 25, 10, 500, 1000)
        ]

        self.locations = {
            "village": village,
            "forest": forest,
            "cave": cave,
            "ruins": ruins,
            "dragon_lair": dragon_lair
        }

        self.current_location = village

    def print_slow(self, text: str, delay: float = 0.03):
        """Print text character by character for dramatic effect."""
        for char in text:
            print(char, end='', flush=True)
        print()

    def clear_screen(self):
        """Clear the screen."""
        print("\n" * 2)

    def display_title(self):
        """Display the game title."""
        print("=" * 60)
        print("           LEGENDS OF THE FORGOTTEN REALM")
        print("                 A Text RPG Adventure")
        print("=" * 60)
        print()

    def create_character(self):
        """Character creation process."""
        print("Welcome, brave adventurer!")
        print()

        name = input("What is your name? ").strip()
        if not name:
            name = "Hero"

        print(f"\nWelcome, {name}!")
        print("\nChoose your class:")
        print("1. Warrior - High HP and Defense (HP: 120, ATK: 15, DEF: 8)")
        print("2. Mage - High Attack, Low Defense (HP: 80, ATK: 20, DEF: 3)")
        print("3. Rogue - Balanced Stats (HP: 100, ATK: 18, DEF: 5)")

        while True:
            choice = input("\nEnter 1, 2, or 3: ").strip()
            if choice == "1":
                character_class = "Warrior"
                break
            elif choice == "2":
                character_class = "Mage"
                break
            elif choice == "3":
                character_class = "Rogue"
                break
            else:
                print("Invalid choice. Please enter 1, 2, or 3.")

        self.player = Player(name, character_class)

        starting_weapon = Weapon("Rusty Sword", "A weathered but functional blade", 5)
        self.player.add_item(starting_weapon)
        self.player.equip_weapon(starting_weapon)

        starting_potion = Potion("Health Potion", "Restores 50 HP", 50)
        self.player.add_item(starting_potion)

        print(f"\n{name} the {character_class} has been created!")
        print(f"HP: {self.player.hp}/{self.player.max_hp}")
        print(f"Attack: {self.player.attack} | Defense: {self.player.defense}")
        print(f"Starting Gold: {self.player.gold}")
        input("\nPress Enter to begin your adventure...")

    def display_status(self):
        """Display player status."""
        print("\n" + "=" * 60)
        print(f"[{self.player.name} - Level {self.player.level} {self.player.character_class}]")
        print(f"HP: {self.player.hp}/{self.player.max_hp} | "
              f"ATK: {self.player.attack} | DEF: {self.player.defense}")
        print(f"EXP: {self.player.exp}/{self.player.exp_to_next_level} | Gold: {self.player.gold}")
        print(f"Location: {self.current_location.name}")
        print("=" * 60)

    def display_location(self):
        """Display current location details."""
        print(f"\n{self.current_location.name}")
        print("-" * 60)
        print(self.current_location.description)

        if not self.current_location.visited:
            self.current_location.visited = True
            if self.current_location.items:
                print(f"\nYou found: {', '.join(item.name for item in self.current_location.items)}")
                for item in self.current_location.items:
                    self.player.add_item(item)
                self.current_location.items = []

    def combat(self, enemy: Enemy):
        """Combat system."""
        print(f"\n{'!' * 60}")
        print(f"A wild {enemy.name} appears!")
        print(f"{enemy.name} - HP: {enemy.hp} | ATK: {enemy.attack} | DEF: {enemy.defense}")
        print('!' * 60)

        while enemy.is_alive and self.player.is_alive:
            print(f"\n[Your HP: {self.player.hp}/{self.player.max_hp}] | [{enemy.name} HP: {enemy.hp}]")
            print("\nWhat will you do?")
            print("1. Attack")
            print("2. Use Potion")
            print("3. Run Away")

            choice = input("\nChoice: ").strip()

            if choice == "1":
                damage = self.player.attack_enemy(enemy)
                print(f"\nYou attack {enemy.name} for {damage} damage!")

                if not enemy.is_alive:
                    print(f"\n{enemy.name} has been defeated!")
                    self.player.gain_exp(enemy.exp_reward)
                    self.player.gold += enemy.gold_reward
                    print(f"You gained {enemy.exp_reward} EXP and {enemy.gold_reward} gold!")

                    if self.player.exp >= self.player.exp_to_next_level:
                        print(f"\nCongratulations! You reached Level {self.player.level}!")

                    return True

                enemy_damage = enemy.attack_enemy(self.player)
                print(f"{enemy.name} attacks you for {enemy_damage} damage!")

                if not self.player.is_alive:
                    self.game_over = True
                    return False

            elif choice == "2":
                potions = [item for item in self.player.inventory if isinstance(item, Potion)]
                if not potions:
                    print("\nYou have no potions!")
                    continue

                print("\nPotions:")
                for i, potion in enumerate(potions, 1):
                    print(f"{i}. {potion.name} (Heals {potion.heal_amount} HP)")

                try:
                    potion_choice = int(input("Choose potion (0 to cancel): ")) - 1
                    if potion_choice == -1:
                        continue
                    if 0 <= potion_choice < len(potions):
                        old_hp = self.player.hp
                        self.player.use_potion(potions[potion_choice])
                        heal_amount = self.player.hp - old_hp
                        print(f"\nYou used {potions[potion_choice].name} and restored {heal_amount} HP!")

                        enemy_damage = enemy.attack_enemy(self.player)
                        print(f"{enemy.name} attacks you for {enemy_damage} damage!")

                        if not self.player.is_alive:
                            self.game_over = True
                            return False
                    else:
                        print("Invalid choice!")
                except ValueError:
                    print("Invalid input!")

            elif choice == "3":
                if random.random() < 0.5:
                    print("\nYou successfully ran away!")
                    return False
                else:
                    print("\nYou couldn't escape!")
                    enemy_damage = enemy.attack_enemy(self.player)
                    print(f"{enemy.name} attacks you for {enemy_damage} damage!")

                    if not self.player.is_alive:
                        self.game_over = True
                        return False
            else:
                print("Invalid choice!")

    def show_inventory(self):
        """Display player inventory."""
        print("\n" + "=" * 60)
        print("INVENTORY")
        print("=" * 60)

        if not self.player.inventory:
            print("Your inventory is empty.")
        else:
            weapons = [item for item in self.player.inventory if isinstance(item, Weapon)]
            potions = [item for item in self.player.inventory if isinstance(item, Potion)]

            if weapons:
                print("\nWeapons:")
                for weapon in weapons:
                    equipped = " (Equipped)" if weapon == self.player.equipped_weapon else ""
                    print(f"  - {weapon.name}{equipped}: {weapon.description} (+{weapon.damage} ATK)")

            if potions:
                print("\nPotions:")
                for potion in potions:
                    print(f"  - {potion.name}: {potion.description}")

    def explore_menu(self):
        """Exploration menu."""
        while not self.game_over:
            self.display_status()
            self.display_location()

            print("\n" + "-" * 60)
            print("What would you like to do?")
            print("1. Look for enemies")
            print("2. Check inventory")
            print("3. Travel to another location")
            print("4. Rest (Restore HP)")
            print("5. View stats")
            print("6. Quit game")

            choice = input("\nChoice: ").strip()

            if choice == "1":
                if self.current_location.enemies:
                    enemy = random.choice(self.current_location.enemies)
                    self.combat(enemy)
                    if self.game_over:
                        break
                else:
                    print("\nNo enemies found in this area.")
                    input("Press Enter to continue...")

            elif choice == "2":
                self.show_inventory()
                input("\nPress Enter to continue...")

            elif choice == "3":
                self.travel_menu()

            elif choice == "4":
                cost = 20
                if self.player.gold >= cost:
                    self.player.gold -= cost
                    self.player.hp = self.player.max_hp
                    print(f"\nYou rest at an inn for {cost} gold. HP fully restored!")
                else:
                    print(f"\nYou don't have enough gold. Need {cost} gold.")
                input("Press Enter to continue...")

            elif choice == "5":
                self.display_status()
                print(f"\nClass: {self.player.character_class}")
                print(f"Equipped Weapon: {self.player.equipped_weapon.name if self.player.equipped_weapon else 'None'}")
                input("\nPress Enter to continue...")

            elif choice == "6":
                confirm = input("\nAre you sure you want to quit? (y/n): ").strip().lower()
                if confirm == 'y':
                    print("\nThanks for playing!")
                    sys.exit(0)

            else:
                print("Invalid choice!")
                input("Press Enter to continue...")

    def travel_menu(self):
        """Travel to different locations."""
        print("\n" + "=" * 60)
        print("TRAVEL")
        print("=" * 60)
        print("Where would you like to go?")
        print("1. Village of Eldoria (Safe Haven)")
        print("2. Dark Forest (Easy)")
        print("3. Ancient Cave (Medium)")
        print("4. Cursed Ruins (Hard)")
        print("5. Dragon's Lair (Boss)")
        print("0. Stay here")

        choice = input("\nChoice: ").strip()

        location_map = {
            "1": "village",
            "2": "forest",
            "3": "cave",
            "4": "ruins",
            "5": "dragon_lair"
        }

        if choice in location_map:
            self.current_location = self.locations[location_map[choice]]
            print(f"\nYou travel to {self.current_location.name}...")
            input("Press Enter to continue...")
        elif choice == "0":
            print("\nYou decide to stay here.")
        else:
            print("Invalid choice!")
            input("Press Enter to continue...")

    def game_over_screen(self):
        """Display game over screen."""
        print("\n" + "=" * 60)
        print("              GAME OVER")
        print("=" * 60)
        print(f"\n{self.player.name} the {self.player.character_class} has fallen in battle.")
        print(f"You reached Level {self.player.level}")
        print(f"Total Gold Earned: {self.player.gold}")
        print("\nBetter luck next time, adventurer!")
        print("=" * 60)

    def run(self):
        """Main game loop."""
        self.display_title()
        self.create_character()

        print("\n" + "=" * 60)
        print("Your quest begins in the Village of Eldoria.")
        print("Defeat the Ancient Dragon to win the game!")
        print("=" * 60)
        input("\nPress Enter to continue...")

        self.explore_menu()

        if self.game_over:
            self.game_over_screen()


def main():
    """Main entry point."""
    game = Game()
    game.run()


if __name__ == "__main__":
    main()
