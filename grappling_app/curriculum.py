"""
Belt Progression Curriculum Module
Maps techniques to belt levels and tracks progression
"""

class BeltCurriculum:
    def __init__(self, technique_db):
        self.technique_db = technique_db
        self.curriculum = self._build_curriculum()

    def _build_curriculum(self):
        """Build comprehensive belt curriculum with wrestler-specific path"""
        return {
            "white": {
                "focus": "Fundamentals + Wrestling Integration",
                "priority_areas": [
                    "Adapt wrestling takedowns for BJJ (avoid guillotines)",
                    "Basic positions and escapes",
                    "Survival and submission defense",
                    "Learn to use gi grips",
                    "Understand guard position (new concept for wrestlers)"
                ],
                "essential_techniques": {
                    "positions": [
                        "Closed Guard",
                        "Mount",
                        "Side Control",
                        "Back Control",
                        "Half Guard - Bottom"
                    ],
                    "submissions": [
                        "Rear Naked Choke",
                        "Armbar from Guard",
                        "Americana",
                        "Guillotine Choke"
                    ],
                    "takedowns": [
                        "Double Leg Takedown",
                        "Single Leg Takedown",
                        "Pull Guard",
                        "Blast Double Leg (adapt from wrestling)",
                        "High Crotch Takedown (adapt from wrestling)"
                    ],
                    "escapes": [
                        "Mount Escape (Elbow-Knee Escape)",
                        "Side Control Escape",
                        "Turtle Defense (CRITICAL - unlearn wrestling habit)"
                    ],
                    "guard_work": [
                        "Closed guard control and posture breaking",
                        "Basic guard retention concepts",
                        "Hip escapes (shrimping)"
                    ]
                },
                "wrestler_specific_goals": [
                    "Stop turtling when in danger - go to guard instead",
                    "Learn submission defense (biggest gap)",
                    "Develop comfort being on bottom",
                    "Adapt wrestling aggression to BJJ rule set",
                    "Learn when to use pressure vs technique"
                ],
                "time_estimate": "6-12 months with wrestling background"
            },
            "blue": {
                "focus": "Develop Guard Game + Refine Top Control",
                "priority_areas": [
                    "Build leg-based guard system (optimal for body type)",
                    "Develop front headlock attacks (wrestling strength)",
                    "Guard passing fundamentals",
                    "Submission chains and combinations",
                    "Start learning leg lock defense"
                ],
                "essential_techniques": {
                    "guards": [
                        "De La Riva Guard (OPTIMAL)",
                        "Reverse De La Riva (OPTIMAL)",
                        "X-Guard (OPTIMAL)",
                        "Single Leg X (OPTIMAL)",
                        "Spider Guard (OPTIMAL)",
                        "Lasso Guard (OPTIMAL)",
                        "Butterfly Guard"
                    ],
                    "submissions": [
                        "Triangle Choke from Guard (OPTIMAL)",
                        "Darce Choke (WRESTLING)",
                        "Anaconda Choke (WRESTLING)",
                        "Kimura",
                        "Straight Ankle Lock (intro to leg locks)"
                    ],
                    "takedowns": [
                        "Ankle Pick",
                        "Arm Drag to Back",
                        "Sacrifice Throws",
                        "Front Headlock to Back Take (WRESTLING)"
                    ],
                    "sweeps": [
                        "Scissor Sweep",
                        "Flower Sweep",
                        "X-Guard Sweep"
                    ],
                    "passes": [
                        "Toreando Pass",
                        "Knee Slice Pass",
                        "Smash Pass (WRESTLING)",
                        "Stack Pass (WRESTLING)"
                    ],
                    "positions": [
                        "Knee on Belly",
                        "Turtle Attack - Taking the Back"
                    ]
                },
                "wrestler_specific_goals": [
                    "Become comfortable playing guard (not just passing)",
                    "Develop guard that capitalizes on leg length",
                    "Integrate front headlock game with BJJ submissions",
                    "Learn to combine wrestling pressure with BJJ technique",
                    "Study leg lock defense (wrestlers often vulnerable)"
                ],
                "time_estimate": "1.5-3 years of consistent training"
            },
            "purple": {
                "focus": "Specialized Game Development + Advanced Techniques",
                "priority_areas": [
                    "Develop signature guard style (DLR/X-guard systems)",
                    "Advanced leg entanglements",
                    "Berimbolo and modern back takes",
                    "Advanced passing sequences",
                    "Begin competition strategy"
                ],
                "essential_techniques": {
                    "advanced_guards": [
                        "Deep Half Guard (OPTIMAL)",
                        "50/50 Guard",
                        "K-Guard"
                    ],
                    "submissions": [
                        "Omoplata (OPTIMAL)",
                        "Loop Choke",
                        "Advanced triangle setups",
                        "Leg drag to back attack"
                    ],
                    "sweeps": [
                        "De La Riva Sweep (Baby Bolo) (OPTIMAL)",
                        "Berimbolo (OPTIMAL)",
                        "Advanced X-guard sweeps"
                    ],
                    "passes": [
                        "Long Step Pass",
                        "Leg Drag",
                        "Advanced pressure sequences"
                    ],
                    "transitions": [
                        "Granby Roll guard retention (WRESTLING)"
                    ]
                },
                "wrestler_specific_goals": [
                    "Integrate wrestling scrambles with BJJ positions",
                    "Develop well-rounded top and bottom game",
                    "Use leg length + wrestling base = dominant style",
                    "Compete regularly to test skills",
                    "Begin teaching/mentoring white and blue belts"
                ],
                "time_estimate": "2-4 years at purple"
            },
            "brown": {
                "focus": "Mastery + Competition Excellence",
                "priority_areas": [
                    "Mastery of chosen positions",
                    "Advanced leg lock offense and defense",
                    "Competition game planning",
                    "Teaching and demonstrating techniques",
                    "Developing personal style"
                ],
                "essential_techniques": {
                    "leg_attacks": [
                        "Heel Hook (Outside) (OPTIMAL - DANGER)",
                        "Heel Hook (Inside) (OPTIMAL - DANGER)",
                        "Kneebar (OPTIMAL)"
                    ],
                    "advanced_concepts": [
                        "Matrix of positions and transitions",
                        "Reading opponents and adapting",
                        "Competition strategy and tactics",
                        "Combining wrestling + BJJ seamlessly"
                    ]
                },
                "wrestler_specific_goals": [
                    "Be example of wrestling-BJJ integration",
                    "Develop unstoppable takedown to pass to submit chain",
                    "Guard game that catches pure wrestlers",
                    "Top game that  catches pure BJJ players",
                    "Ready for black belt test and teaching responsibility"
                ],
                "time_estimate": "2-4+ years at brown"
            },
            "black": {
                "focus": "Mastery, Innovation, Teaching",
                "concepts": [
                    "Complete game in all positions",
                    "Ability to teach entire curriculum",
                    "Competition at highest levels (if desired)",
                    "Developing unique techniques and systems",
                    "Mentoring students through their journey"
                ]
            }
        }

    def get_belt_requirements(self, belt_level):
        """Get requirements for specific belt level"""
        return self.curriculum.get(belt_level, {})

    def get_next_techniques_to_learn(self, current_belt, learned_techniques):
        """Suggest next techniques to learn based on current progress"""
        belt_req = self.get_belt_requirements(current_belt)
        suggestions = []

        if "essential_techniques" in belt_req:
            for category, tech_list in belt_req["essential_techniques"].items():
                for tech_name in tech_list:
                    if tech_name not in learned_techniques:
                        tech = self.technique_db.get_technique_by_name(tech_name)
                        if tech:
                            suggestions.append({
                                "name": tech_name,
                                "category": category,
                                "optimal": tech.optimal_for_user,
                                "priority": "HIGH" if tech.optimal_for_user else "MEDIUM"
                            })

        # Prioritize optimal techniques
        suggestions.sort(key=lambda x: (x["priority"] != "HIGH", x["name"]))
        return suggestions

    def get_progression_percentage(self, current_belt, learned_techniques):
        """Calculate progression percentage for current belt"""
        belt_req = self.get_belt_requirements(current_belt)
        if "essential_techniques" not in belt_req:
            return 100

        total_techniques = 0
        learned_count = 0

        for tech_list in belt_req["essential_techniques"].values():
            total_techniques += len(tech_list)
            for tech_name in tech_list:
                if tech_name in learned_techniques:
                    learned_count += 1

        if total_techniques == 0:
            return 100

        return int((learned_count / total_techniques) * 100)

    def get_wrestler_specific_notes(self, belt_level):
        """Get wrestler-specific goals and notes for belt level"""
        belt_req = self.get_belt_requirements(belt_level)
        return {
            "goals": belt_req.get("wrestler_specific_goals", []),
            "focus": belt_req.get("focus", ""),
            "priority_areas": belt_req.get("priority_areas", [])
        }
