"""
User Profile Module
Manages user's physical attributes and training preferences
"""

class UserProfile:
    def __init__(self):
        self.height = 65  # 5'5" in inches
        self.wingspan = 67.5  # 5'7.5" in inches
        self.torso_length = "short"
        self.leg_length = "long"
        self.current_belt = "white"
        self.training_days = []
        self.wrestling_experience = True
        self.experience_notes = "Wrestling background provides strong base for top control, takedowns, and pressure passing"

    def get_body_type_advantages(self):
        """Returns techniques optimized for user's body type"""
        return {
            "favorable_guards": [
                "De La Riva Guard",
                "Reverse De La Riva",
                "X-Guard",
                "Single Leg X",
                "Spider Guard",
                "K-Guard (wrestling style)"
            ],
            "favorable_submissions": [
                "Triangle Choke",
                "Armbar from Guard",
                "Omoplata",
                "Leg Locks",
                "Heel Hooks",
                "Darce Choke (wrestling strength)",
                "Anaconda Choke (wrestling strength)",
                "Guillotine variations"
            ],
            "favorable_takedowns": [
                "Wrestling Singles/Doubles (EXISTING SKILL)",
                "Low Single Leg",
                "Ankle Pick",
                "High Crotch",
                "Blast Double",
                "Front Headlock Series"
            ],
            "favorable_top_game": [
                "Pressure passing (wrestling base)",
                "Knee slice with crossface",
                "Smash passing",
                "Leg drag (modern + wrestling)",
                "Front headlock attacks"
            ],
            "avoid_or_adapt": [
                "Don't neglect guard development (common wrestler mistake)",
                "Learn to be comfortable on bottom",
                "Adapt wrestling pressure with BJJ technique"
            ],
            "notes": "WRESTLING + LONG LEGS + SHORT TORSO = Unique hybrid game. Use wrestling for takedowns and top pressure, but develop guard game (especially leg-based guards) to become complete. Your scrambling ability will be a major asset."
        }

    def get_wrestling_advantages(self):
        """Returns specific advantages from wrestling background"""
        return {
            "existing_strengths": [
                "Takedown offense and defense",
                "Top pressure and control",
                "Scrambling ability",
                "Hand fighting and grip fighting",
                "Base and posture",
                "Mental toughness and conditioning",
                "Front headlock position"
            ],
            "bjj_adaptations_needed": [
                "Defend submissions (wrestling doesn't have these)",
                "Develop guard game (wrestlers often neglect)",
                "Learn to use gi grips effectively",
                "Adapt to slower, more technical pace",
                "Don't give up back (wrestling habit)",
                "Learn guard retention and recovery"
            ],
            "ideal_game_plan": [
                "Phase 1 (White/Blue): Leverage wrestling for takedowns, develop guard defense and basic guards",
                "Phase 2 (Blue/Purple): Build leg-based guard game (DLR, X-guard, SLX) while maintaining top game",
                "Phase 3 (Purple+): Integrate leg locks, develop complete top/bottom game",
                "Overall: Become wrestler who can't be submitted and has dangerous guard"
            ],
            "common_wrestler_mistakes_to_avoid": [
                "Turtling when in danger (gives up back in BJJ)",
                "Neglecting guard work (will get submitted)",
                "Over-relying on strength and pressure",
                "Poor submission defense awareness",
                "Giving up bottom position too easily"
            ]
        }

    def get_ape_index(self):
        """Calculate ape index (wingspan - height)"""
        return self.wingspan - self.height

    def to_dict(self):
        return {
            "height": self.height,
            "wingspan": self.wingspan,
            "torso_length": self.torso_length,
            "leg_length": self.leg_length,
            "current_belt": self.current_belt,
            "ape_index": self.get_ape_index(),
            "wrestling_experience": self.wrestling_experience,
            "experience_notes": self.experience_notes
        }
