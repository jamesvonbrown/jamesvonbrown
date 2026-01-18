"""
Technique Database Module
Hierarchical organization of BJJ techniques with body-type optimization
"""

class Technique:
    def __init__(self, name, category, subcategory, belt_level,
                 optimal_for_user=False, youtube_url="",
                 description="", key_details=None,
                 success_rate="", finish_rate="", stats_notes=""):
        self.name = name
        self.category = category  # Position, Takedown, Submission, Escape, Pass, Sweep
        self.subcategory = subcategory
        self.belt_level = belt_level
        self.optimal_for_user = optimal_for_user
        self.youtube_url = youtube_url
        self.description = description
        self.key_details = key_details or []
        self.prerequisites = []
        self.practice_log = []
        # Competition statistics (research-based)
        self.success_rate = success_rate  # e.g., "63% sweep success from X-guard"
        self.finish_rate = finish_rate    # e.g., "78% finish from back control"
        self.stats_notes = stats_notes    # Additional context about stats

    def to_dict(self):
        return {
            "name": self.name,
            "category": self.category,
            "subcategory": self.subcategory,
            "belt_level": self.belt_level,
            "optimal_for_user": self.optimal_for_user,
            "youtube_url": self.youtube_url,
            "description": self.description,
            "key_details": self.key_details,
            "prerequisites": self.prerequisites,
            "success_rate": self.success_rate,
            "finish_rate": self.finish_rate,
            "stats_notes": self.stats_notes
        }


class TechniqueDatabase:
    def __init__(self):
        self.techniques = []
        self._initialize_database()

    def _initialize_database(self):
        """Initialize with comprehensive BJJ curriculum optimized for user's body type"""

        # ===== POSITIONS =====

        # Guard Positions (Optimal for long legs)
        self.add_technique(Technique(
            "Closed Guard",
            "Position",
            "Guard - Bottom",
            "white",
            optimal_for_user=True,
            youtube_url="https://www.youtube.com/watch?v=6BQn774KbjE",
            description="Fundamental guard position with legs locked around opponent's waist",
            key_details=[
                "Break posture immediately",
                "Control sleeves or collar",
                "Use leg length to maintain tight lock",
                "Hip movement is key"
            ]
        ))

        self.add_technique(Technique(
            "De La Riva Guard",
            "Position",
            "Guard - Bottom",
            "blue",
            optimal_for_user=True,
            youtube_url="https://www.youtube.com/watch?v=jleDFGNQ6qI",
            description="Hook-based guard using leg on opponent's hip and foot wrapping leg",
            key_details=[
                "OPTIMAL: Long legs excel at this guard",
                "Hook deep behind knee",
                "Opposite foot on hip for distance",
                "Control same-side sleeve",
                "Off-balance opponent constantly"
            ]
        ))

        self.add_technique(Technique(
            "Reverse De La Riva (RDLR)",
            "Position",
            "Guard - Bottom",
            "blue",
            optimal_for_user=True,
            youtube_url="https://www.youtube.com/watch?v=S7R6BqBkj2s",
            description="Reverse hook guard with foot across body",
            key_details=[
                "OPTIMAL: Leg length provides superior control",
                "Deep hook outside opponent's leg",
                "Top foot on hip/bicep",
                "Excellent for smaller grapplers",
                "Creates distance and off-balancing"
            ]
        ))

        self.add_technique(Technique(
            "X-Guard",
            "Position",
            "Guard - Bottom",
            "blue",
            optimal_for_user=True,
            youtube_url="https://www.youtube.com/watch?v=zYKPBZx_m5A",
            description="Both legs controlling opponent's legs in X configuration",
            key_details=[
                "OPTIMAL: Long legs = better control",
                "One foot on hip, one behind knee",
                "Legs form X shape",
                "Elevate opponent",
                "Great for sweeps"
            ],
            success_rate="High-percentage sweep position (specific attempt data unavailable)",
            finish_rate="Primarily sweeping platform (submissions rare at elite level)",
            stats_notes="HIGH PERCENTAGE GUARD - Described as 'one of the most successful guards to sweep from' at elite levels. IBJJF 2022 recorded 252 sweeps in 190 matches (most common point-scoring action). Long legs (yours: 60.8%!) give superior elevation and control. Optimal for your build."
        ))

        self.add_technique(Technique(
            "Single Leg X (SLX)",
            "Position",
            "Guard - Bottom",
            "blue",
            optimal_for_user=True,
            youtube_url="https://www.youtube.com/watch?v=LVKLLNnDzs4",
            description="Both legs controlling single leg of opponent",
            key_details=[
                "OPTIMAL: Leg length dominates this position",
                "Both legs wrap one opponent leg",
                "Control ankle and behind knee",
                "Entry to leg attacks",
                "Excellent for smaller grapplers"
            ]
        ))

        self.add_technique(Technique(
            "Spider Guard",
            "Position",
            "Guard - Bottom",
            "blue",
            optimal_for_user=True,
            youtube_url="https://www.youtube.com/watch?v=rH3gQYc_5K8",
            description="Feet on biceps/forearms with sleeve control",
            key_details=[
                "OPTIMAL: Leg length creates maximum distance",
                "Grip sleeves, feet on biceps",
                "Control distance with legs",
                "Prevent passing",
                "Setup sweeps and triangles"
            ]
        ))

        self.add_technique(Technique(
            "Lasso Guard",
            "Position",
            "Guard - Bottom",
            "blue",
            optimal_for_user=True,
            youtube_url="https://www.youtube.com/watch?v=gHMx2fJn1W0",
            description="Foot threaded through arm with sleeve grip",
            key_details=[
                "OPTIMAL: Longer legs thread deeper",
                "Foot through armpit",
                "Tight sleeve control",
                "Other foot on hip/bicep",
                "Prevents posture and passing"
            ]
        ))

        self.add_technique(Technique(
            "Half Guard - Bottom",
            "Position",
            "Guard - Bottom",
            "white",
            optimal_for_user=False,
            youtube_url="https://www.youtube.com/watch?v=KBJb-9ErVPw",
            description="One leg trapped between yours",
            key_details=[
                "Get underhook",
                "Prevent crossface",
                "Work to deep half or sweep",
                "Frame with bottom arm"
            ]
        ))

        self.add_technique(Technique(
            "Deep Half Guard",
            "Position",
            "Guard - Bottom",
            "purple",
            optimal_for_user=True,
            youtube_url="https://www.youtube.com/watch?v=9JnjamjWCGk",
            description="Under opponent with leg control",
            key_details=[
                "OPTIMAL: Leverage-based for smaller grapplers",
                "Control far leg",
                "Head and shoulder under opponent",
                "Waiter sweep setup",
                "Safe position for smaller fighters"
            ]
        ))

        self.add_technique(Technique(
            "Butterfly Guard",
            "Position",
            "Guard - Bottom",
            "blue",
            optimal_for_user=False,
            youtube_url="https://www.youtube.com/watch?v=HHDLdYhWLqw",
            description="Hooks inside opponent's thighs while seated",
            key_details=[
                "Hooks inside thighs",
                "Upper body control (overhooks/underhooks)",
                "Elevate with hooks for sweeps",
                "Stay tight to opponent"
            ]
        ))

        # Top Positions
        self.add_technique(Technique(
            "Mount",
            "Position",
            "Top Control",
            "white",
            optimal_for_user=False,
            youtube_url="https://www.youtube.com/watch?v=7wFSdJCLp7A",
            description="Sitting on opponent's torso with legs around",
            key_details=[
                "Control hips",
                "Chest to chest pressure",
                "Grapevine legs if possible",
                "High mount for submissions"
            ]
        ))

        self.add_technique(Technique(
            "Side Control",
            "Position",
            "Top Control",
            "white",
            optimal_for_user=False,
            youtube_url="https://www.youtube.com/watch?v=gvfR5jRvc8c",
            description="Perpendicular control on opponent's side",
            key_details=[
                "Hip to hip pressure",
                "Control near arm",
                "Head position prevents escape",
                "Distribute weight effectively"
            ]
        ))

        self.add_technique(Technique(
            "Knee on Belly",
            "Position",
            "Top Control",
            "blue",
            optimal_for_user=True,
            youtube_url="https://www.youtube.com/watch?v=xRl0d-z1wuw",
            description="Knee placed on opponent's stomach/chest",
            key_details=[
                "GOOD: Less reliant on weight",
                "Knee on solar plexus",
                "Control opposite collar and pants",
                "Mobile position",
                "Submission entries"
            ]
        ))

        self.add_technique(Technique(
            "Back Control",
            "Position",
            "Top Control",
            "white",
            optimal_for_user=True,
            youtube_url="https://www.youtube.com/watch?v=8b-syr2B6mg",
            description="Behind opponent with hooks in",
            key_details=[
                "OPTIMAL: Leverage-based, not weight-based",
                "Both hooks in (feet inside thighs)",
                "Seatbelt grip (one over, one under)",
                "Control hips with legs",
                "Highest scoring position"
            ]
        ))

        # ===== TAKEDOWNS =====

        self.add_technique(Technique(
            "Double Leg Takedown",
            "Takedown",
            "Leg Attacks",
            "white",
            optimal_for_user=True,
            youtube_url="https://www.youtube.com/watch?v=Fmg3ZQqFPyM",
            description="Attack both legs, drive through",
            key_details=[
                "OPTIMAL: Lower level change favors shorter fighters",
                "Change levels explosively",
                "Head to outside",
                "Grab behind knees",
                "Drive through opponent"
            ],
            success_rate="~20% attempt success for leg-based takedowns",
            finish_rate="Significantly more effective in no-gi than gi",
            stats_notes="WRESTLING DOMINANCE - REAL DATA: Single leg variations show ~20% attempt success in competition. ADCC 2024 had 62 total takedowns (13 double legs, 15 single legs), far exceeding guard passes (26) and sweeps (31). No-gi matches feature takedowns 3x more often than gi (41% vs 14% match frequency). Your wrestling background provides massive advantage."
        ))

        self.add_technique(Technique(
            "Single Leg Takedown",
            "Takedown",
            "Leg Attacks",
            "white",
            optimal_for_user=True,
            youtube_url="https://www.youtube.com/watch?v=3gLgOqDUMr0",
            description="Attack one leg, various finishes",
            key_details=[
                "OPTIMAL: Leg length helps with ankle picks",
                "Multiple finishing options",
                "Control ankle and behind knee",
                "Run the pipe or dump",
                "Great for smaller grapplers"
            ]
        ))

        self.add_technique(Technique(
            "Ankle Pick",
            "Takedown",
            "Leg Attacks",
            "blue",
            optimal_for_user=True,
            youtube_url="https://www.youtube.com/watch?v=YAFyb0nXrhA",
            description="Pull ankle while pushing upper body",
            key_details=[
                "OPTIMAL: Uses opponent's height against them",
                "Snap head down",
                "Reach for ankle",
                "Push/pull simultaneously",
                "Excellent for shorter fighters"
            ]
        ))

        self.add_technique(Technique(
            "Arm Drag to Back",
            "Takedown",
            "Upper Body",
            "blue",
            optimal_for_user=True,
            youtube_url="https://www.youtube.com/watch?v=J-IyHhN9p7c",
            description="Pull arm across, take the back",
            key_details=[
                "OPTIMAL: Technique over strength",
                "Control wrist and tricep",
                "Pull across body",
                "Circle to back",
                "Works from standing or seated"
            ]
        ))

        self.add_technique(Technique(
            "Sacrifice Throws (Tomoe Nage, Sumi Gaeshi)",
            "Takedown",
            "Throws",
            "blue",
            optimal_for_user=True,
            youtube_url="https://www.youtube.com/watch?v=iKGNlqjXlKo",
            description="Fall backward while throwing opponent",
            key_details=[
                "OPTIMAL: Use opponent's weight/momentum",
                "Foot to hip/stomach",
                "Pull opponent forward",
                "Roll backward",
                "Great for smaller vs larger opponents"
            ]
        ))

        self.add_technique(Technique(
            "Pull Guard",
            "Takedown",
            "Guard Pulls",
            "white",
            optimal_for_user=True,
            youtube_url="https://www.youtube.com/watch?v=seBbA7MqZWo",
            description="Initiate guard position from standing",
            key_details=[
                "OPTIMAL: Plays to guard strength",
                "Grip before pulling",
                "Sit to guard",
                "Immediate guard retention",
                "Strategic for long-legged players"
            ]
        ))

        # ===== SUBMISSIONS =====

        # Chokes
        self.add_technique(Technique(
            "Rear Naked Choke",
            "Submission",
            "Choke - Back",
            "white",
            optimal_for_user=True,
            youtube_url="https://www.youtube.com/watch?v=rQZP9qQdN7o",
            description="Choke from back control",
            key_details=[
                "OPTIMAL: Technique-based, wingspan helps",
                "Under chin, not across face",
                "Lock figure-four",
                "Squeeze elbows together",
                "Expand chest"
            ],
            success_rate="42% attempt success (68 finishes from 132 attempts)",
            finish_rate="78% finish rate from fully locked back control",
            stats_notes="KING OF SUBMISSIONS - REAL DATA: 42% of RNC attempts finish the opponent (68/132). From fully locked back control, jumps to 78%. Most dominant at elite level: 26 finishes at 2025 IBJJF No-Gi Worlds, 45% of all IBJJF Worlds finishes."
        ))

        self.add_technique(Technique(
            "Triangle Choke from Guard",
            "Submission",
            "Choke - Guard",
            "blue",
            optimal_for_user=True,
            youtube_url="https://www.youtube.com/watch?v=kPyFPz9rI70",
            description="Legs around neck and arm",
            key_details=[
                "OPTIMAL: Long legs create tighter triangle",
                "One arm in, one arm out",
                "Lock triangle (foot behind knee)",
                "Angle off",
                "Pull head down, lift hips"
            ],
            success_rate="62% attempt success in gi (28 finishes from 45 attempts)",
            finish_rate="Top 3 submission at white-purple belts, declines at elite black belt",
            stats_notes="PERFECT FOR YOUR LEGS (60.8% leg ratio!) - REAL DATA: 62% success at IBJJF Worlds 2019 (28/45 attempts). Research confirms 'lanky guard players with exceptional hip flexibility' see better-than-average success. YOU are exactly this body type. 40% at white/blue/purple, 23% at brown/black."
        ))

        self.add_technique(Technique(
            "Guillotine Choke",
            "Submission",
            "Choke - Front",
            "white",
            optimal_for_user=True,
            youtube_url="https://www.youtube.com/watch?v=gLFRYJyhXDs",
            description="Front headlock choke",
            key_details=[
                "GOOD: Wingspan helps with grip",
                "Arm around neck",
                "Lock hands (various grips)",
                "Lift elbow, shrug shoulder",
                "Can finish from guard or standing"
            ]
        ))

        self.add_technique(Technique(
            "Ezekiel Choke",
            "Submission",
            "Choke - Top",
            "blue",
            optimal_for_user=False,
            youtube_url="https://www.youtube.com/watch?v=Tk_v7OiVD1c",
            description="Choke using gi sleeve from mount",
            key_details=[
                "One hand in sleeve",
                "Wrap around neck",
                "Other hand behind head",
                "Squeeze and pull"
            ]
        ))

        self.add_technique(Technique(
            "Loop Choke",
            "Submission",
            "Choke - Guard",
            "purple",
            optimal_for_user=False,
            youtube_url="https://www.youtube.com/watch?v=dQt_u7L4UKI",
            description="Collar choke from guard",
            key_details=[
                "Deep collar grip",
                "Feed to other hand",
                "Roll opponent",
                "Technical choke"
            ]
        ))

        # Joint Locks - Arms
        self.add_technique(Technique(
            "Armbar from Guard",
            "Submission",
            "Armlock - Guard",
            "white",
            optimal_for_user=True,
            youtube_url="https://www.youtube.com/watch?v=BCJvGPQ4E8s",
            description="Hyperextend elbow from guard",
            key_details=[
                "OPTIMAL: Leg length creates better angle",
                "Control arm with both hands",
                "Leg over head, leg across body",
                "Hips high, knees tight",
                "Thumbs up, extend hips"
            ],
            success_rate="50% attempt success overall (68 finishes from 137 attempts)",
            finish_rate="Varies by position: ~50% from mount, ~30% from guard",
            stats_notes="ELITE FUNDAMENTAL - REAL DATA: 50% of armbar attempts succeed (68/137). Success varies by position: mount (~50%) vs guard (~30%). Accounts for 20% of all submissions. 10 finishes at 2025 IBJJF No-Gi Worlds. Long legs (yours: 60.8% leg ratio!) provide superior angle and control."
        ))

        self.add_technique(Technique(
            "Kimura",
            "Submission",
            "Shoulder Lock",
            "blue",
            optimal_for_user=False,
            youtube_url="https://www.youtube.com/watch?v=jlhpSzS7dDM",
            description="Figure-four shoulder lock",
            key_details=[
                "Bend arm 90 degrees",
                "Figure-four grip",
                "Rotate away from opponent",
                "Works from many positions"
            ]
        ))

        self.add_technique(Technique(
            "Americana",
            "Submission",
            "Shoulder Lock",
            "white",
            optimal_for_user=False,
            youtube_url="https://www.youtube.com/watch?v=wZbM8uqsq8M",
            description="Reverse keylock from side/mount",
            key_details=[
                "Pin wrist to mat",
                "Figure-four grip",
                "Rotate toward head",
                "From side or mount"
            ]
        ))

        self.add_technique(Technique(
            "Omoplata",
            "Submission",
            "Shoulder Lock - Guard",
            "purple",
            optimal_for_user=True,
            youtube_url="https://www.youtube.com/watch?v=rWPr2opKyGo",
            description="Leg-based shoulder lock from guard",
            key_details=[
                "OPTIMAL: Long legs excel at this",
                "Leg over shoulder",
                "Control wrist",
                "Rotate body",
                "Break posture forward"
            ]
        ))

        # Leg Locks
        self.add_technique(Technique(
            "Straight Ankle Lock",
            "Submission",
            "Leg Lock",
            "blue",
            optimal_for_user=True,
            youtube_url="https://www.youtube.com/watch?v=F1Tr9WRhPzQ",
            description="Basic foot lock",
            key_details=[
                "OPTIMAL: Leg dexterity advantage",
                "Trap foot in armpit",
                "Lock hands across instep",
                "Extend hips",
                "Most basic legal leg lock"
            ]
        ))

        self.add_technique(Technique(
            "Heel Hook (Outside)",
            "Submission",
            "Leg Lock",
            "brown",
            optimal_for_user=True,
            youtube_url="https://www.youtube.com/watch?v=zx5HjYt5ka4",
            description="Rotational heel attack (DANGER)",
            key_details=[
                "OPTIMAL: Leg control with long legs",
                "WARNING: Causes severe injury quickly",
                "Only legal at brown/black (IBJJF)",
                "Control heel",
                "Rotate/extend",
                "TAP EARLY"
            ]
        ))

        self.add_technique(Technique(
            "Heel Hook (Inside)",
            "Submission",
            "Leg Lock",
            "brown",
            optimal_for_user=True,
            youtube_url="https://www.youtube.com/watch?v=zx5HjYt5ka4",
            description="Inside rotational heel attack (DANGER)",
            key_details=[
                "OPTIMAL: Entry from SLX and other guards",
                "WARNING: Extremely dangerous",
                "Only legal at brown/black (IBJJF)",
                "Inside position",
                "Control heel and rotate"
            ],
            success_rate="62% from saddle, 44% from ashi garami, 38% from 50/50 (position-dependent)",
            finish_rate="Declining at elite level: 4 finishes at ADCC 2024 vs 20 at IBJJF Worlds 2025",
            stats_notes="MODERN LEG LOCK GAME - REAL DATA: Position-dependent success: 62% from saddle position, 44% from ashi garami, 38% from 50/50 (ADCC 2017-2022). 20 finishes at 2025 IBJJF No-Gi Worlds but only 4 at ADCC 2024 (elite defense improving). Optimal for long-legged players (yours: 60.8%!) from SLX entries. Brown/Black only (IBJJF). TAP EARLY - severe damage instantly."
        ))

        self.add_technique(Technique(
            "Kneebar",
            "Submission",
            "Leg Lock",
            "brown",
            optimal_for_user=True,
            youtube_url="https://www.youtube.com/watch?v=gdZf4Xe5R94",
            description="Hyperextend knee joint",
            key_details=[
                "OPTIMAL: From X-guard and SLX entries",
                "Trap leg",
                "Hips to back of knee",
                "Extend hips",
                "Legal at brown+ (IBJJF)"
            ]
        ))

        # ===== SWEEPS =====

        self.add_technique(Technique(
            "Scissor Sweep",
            "Sweep",
            "Closed Guard",
            "white",
            optimal_for_user=True,
            youtube_url="https://www.youtube.com/watch?v=Zj9U0XBZPQE",
            description="Push-pull sweep from closed guard",
            key_details=[
                "OPTIMAL: Leg leverage",
                "One leg on bicep (push)",
                "One leg behind knee (pull)",
                "Collar/sleeve control",
                "Simultaneous push-pull"
            ]
        ))

        self.add_technique(Technique(
            "Flower Sweep (Pendulum)",
            "Sweep",
            "Closed Guard",
            "blue",
            optimal_for_user=True,
            youtube_url="https://www.youtube.com/watch?v=Wm6A4SJI8Hk",
            description="Hip movement sweep from closed guard",
            key_details=[
                "OPTIMAL: Uses momentum not strength",
                "Trap arm",
                "Hip out",
                "Foot on floor",
                "Pendulum motion with legs"
            ]
        ))

        self.add_technique(Technique(
            "X-Guard Sweep",
            "Sweep",
            "X-Guard",
            "blue",
            optimal_for_user=True,
            youtube_url="https://www.youtube.com/watch?v=YQPyQh-grnE",
            description="Elevate and dump from X-guard",
            key_details=[
                "OPTIMAL: Long legs control better",
                "Establish X-guard",
                "Lift with top hook",
                "Pull with bottom hook",
                "Technical stand or continue attack"
            ]
        ))

        self.add_technique(Technique(
            "De La Riva Sweep (Baby Bolo)",
            "Sweep",
            "De La Riva",
            "purple",
            optimal_for_user=True,
            youtube_url="https://www.youtube.com/watch?v=jjb-1lEXRwg",
            description="Back take from DLR",
            key_details=[
                "OPTIMAL: Designed for this body type",
                "DLR hook established",
                "Off-balance opponent",
                "Invert under",
                "Take the back"
            ]
        ))

        self.add_technique(Technique(
            "Berimbolo",
            "Sweep",
            "De La Riva",
            "purple",
            optimal_for_user=True,
            youtube_url="https://www.youtube.com/watch?v=yhk0MA3IUXU",
            description="Spinning back take from DLR/RDLR",
            key_details=[
                "OPTIMAL: Flexibility and leg length advantage",
                "From DLR/RDLR",
                "Invert and spin under",
                "Come up on back",
                "Technical and dynamic"
            ]
        ))

        # ===== ESCAPES =====

        self.add_technique(Technique(
            "Mount Escape (Elbow-Knee Escape)",
            "Escape",
            "Mount",
            "white",
            optimal_for_user=False,
            youtube_url="https://www.youtube.com/watch?v=K6Y8jAeezVY",
            description="Frame and shrimp out from mount",
            key_details=[
                "Frame on hip and neck/shoulder",
                "Shrimp hips out",
                "Bring knee inside",
                "Recover guard"
            ]
        ))

        self.add_technique(Technique(
            "Side Control Escape (Shrimp to Guard)",
            "Escape",
            "Side Control",
            "white",
            optimal_for_user=True,
            youtube_url="https://www.youtube.com/watch?v=Hzv9D9nOPpw",
            description="Create space and recover guard",
            key_details=[
                "GOOD: Long legs recover guard easier",
                "Frame on hip and neck",
                "Shrimp away",
                "Insert knee",
                "Recover closed or open guard"
            ]
        ))

        self.add_technique(Technique(
            "Back Escape",
            "Escape",
            "Back Control",
            "blue",
            optimal_for_user=False,
            youtube_url="https://www.youtube.com/watch?v=OKxJLFxhQ1o",
            description="Defend choke and escape back control",
            key_details=[
                "Defend neck first (hands protect)",
                "Remove one hook",
                "Turn into opponent",
                "Work to guard"
            ]
        ))

        # ===== GUARD PASSES =====

        self.add_technique(Technique(
            "Toreando Pass",
            "Pass",
            "Standing",
            "blue",
            optimal_for_user=True,
            youtube_url="https://www.youtube.com/watch?v=cOb6lF2U3_Q",
            description="Standing pass throwing legs aside",
            key_details=[
                "GOOD: Speed and movement over pressure",
                "Control pants/knees",
                "Throw legs to side",
                "Quick step around",
                "Mobile passing"
            ]
        ))

        self.add_technique(Technique(
            "Knee Slice Pass",
            "Pass",
            "Kneeling",
            "blue",
            optimal_for_user=False,
            youtube_url="https://www.youtube.com/watch?v=z8ZuJZTgHO4",
            description="Slice knee through guard",
            key_details=[
                "Control far hip and collar",
                "Slice knee across",
                "Drive shoulder forward",
                "Clear legs"
            ]
        ))

        self.add_technique(Technique(
            "Long Step Pass",
            "Pass",
            "Standing",
            "purple",
            optimal_for_user=True,
            youtube_url="https://www.youtube.com/watch?v=CKXPRUlkUfQ",
            description="Step leg far back to clear",
            key_details=[
                "GOOD: Speed-based passing",
                "Control collar and pants",
                "Step leg far back",
                "Walk around quickly",
                "Movement over pressure"
            ]
        ))

        self.add_technique(Technique(
            "Leg Drag",
            "Pass",
            "Standing/Kneeling",
            "purple",
            optimal_for_user=True,
            youtube_url="https://www.youtube.com/watch?v=Jgn6-TcWWPY",
            description="Drag leg across body to pass",
            key_details=[
                "GOOD: Technical, less pressure-dependent",
                "Control ankle and knee",
                "Drag across body",
                "Take back or pass to side",
                "Modern passing essential"
            ]
        ))

        # ===== WRESTLING-SPECIFIC TECHNIQUES =====

        # Front Headlock Series (Critical for wrestlers)
        self.add_technique(Technique(
            "Darce Choke",
            "Submission",
            "Choke - Front Headlock",
            "blue",
            optimal_for_user=True,
            youtube_url="https://www.youtube.com/watch?v=EQPRzhnCjiE",
            description="Arm-in choke from front headlock position",
            key_details=[
                "OPTIMAL: Wrestling front headlock transition",
                "One arm in guillotine position",
                "Thread other arm under armpit and neck",
                "Lock hands (various grips)",
                "Squeeze bicep to neck",
                "Natural for wrestlers"
            ],
            success_rate="12% of MMA submissions (BJJ competition attempt data limited)",
            finish_rate="60% of successful finishes occur from front headlock/turtle transitions",
            stats_notes="WRESTLER'S SUBMISSION - REAL DATA: 60% of successful Darce finishes come from front headlock or turtle transitions (your wrestling strength). 12% submission rate in professional MMA. Preferred in IBJJF no-gi divisions. Frequently used by elite no-gi competitors."
        ))

        self.add_technique(Technique(
            "Anaconda Choke",
            "Submission",
            "Choke - Front Headlock",
            "blue",
            optimal_for_user=True,
            youtube_url="https://www.youtube.com/watch?v=mNiAPpXH7WE",
            description="Arm-in choke, opposite of darce",
            key_details=[
                "OPTIMAL: Wrestling front headlock transition",
                "Opponent's arm trapped",
                "Your arm threads through from other side",
                "Lock figure-four under opponent",
                "Roll to finish",
                "Perfect for wrestlers"
            ]
        ))

        self.add_technique(Technique(
            "High Crotch Takedown",
            "Takedown",
            "Leg Attacks",
            "white",
            optimal_for_user=True,
            youtube_url="https://www.youtube.com/watch?v=Oao7OJ5RlMI",
            description="Single leg variation grabbing high on thigh",
            key_details=[
                "WRESTLING SKILL: Adapt for BJJ/gi",
                "Penetration step",
                "Head to outside",
                "Grab high on thigh",
                "Multiple finishes (lift, trip, drive)",
                "Watch for guillotine in BJJ"
            ]
        ))

        self.add_technique(Technique(
            "Front Headlock to Back Take",
            "Position",
            "Transition - Wrestling",
            "blue",
            optimal_for_user=True,
            youtube_url="https://www.youtube.com/watch?v=BWB9fF4cQ9Y",
            description="Wrestling front headlock control to back",
            key_details=[
                "WRESTLING ADVANTAGE: Use existing skill",
                "Snap down to front headlock",
                "Control head and arm",
                "Circle to back (careful not to turtle!)",
                "Insert hooks",
                "High percentage for wrestlers"
            ]
        ))

        # Turtle Position (Wrestlers often go here - need both attack and defense)
        self.add_technique(Technique(
            "Turtle Defense (CRITICAL FOR WRESTLERS)",
            "Escape",
            "Turtle Position",
            "white",
            optimal_for_user=True,
            youtube_url="https://www.youtube.com/watch?v=Lj0cqCYDG2I",
            description="Avoid giving back when in turtle",
            key_details=[
                "CRITICAL: Wrestlers instinctively turtle - BAD in BJJ!",
                "Protect neck from chokes",
                "Don't let them get hooks in",
                "Sit to guard OR stand up quickly",
                "NEVER stay in turtle in BJJ",
                "Unlearn wrestling habit"
            ]
        ))

        self.add_technique(Technique(
            "Turtle Attack - Taking the Back",
            "Position",
            "Turtle Attack",
            "white",
            optimal_for_user=True,
            youtube_url="https://www.youtube.com/watch?v=dXp03bYIY1Q",
            description="Take back from opponent's turtle",
            key_details=[
                "Seat belt grip",
                "Insert first hook",
                "Clear defensive arm",
                "Insert second hook",
                "Wrestlers often turtle - capitalize"
            ]
        ))

        # Pressure Passing (Wrestling strength)
        self.add_technique(Technique(
            "Smash Pass (Headquarters Position)",
            "Pass",
            "Pressure Passing",
            "blue",
            optimal_for_user=True,
            youtube_url="https://www.youtube.com/watch?v=s65hjSbq4e8",
            description="Heavy pressure pass controlling knee line",
            key_details=[
                "WRESTLING STRENGTH: Pressure + control",
                "Control both knees together",
                "Heavy crossface",
                "Drive shoulder pressure",
                "Slowly advance position",
                "Wrestle-style top game"
            ]
        ))

        self.add_technique(Technique(
            "Stack Pass",
            "Pass",
            "Pressure Passing",
            "blue",
            optimal_for_user=True,
            youtube_url="https://www.youtube.com/watch?v=3v2WlgCqp6w",
            description="Drive opponent's knees to chest and pass",
            key_details=[
                "WRESTLING STRENGTH: Use pressure",
                "Control pants near ankles",
                "Drive knees to chest",
                "Stack opponent on shoulders",
                "Walk around to side",
                "Heavy, wrestling-style pass"
            ]
        ))

        # Wrestling-style Guard Retention
        self.add_technique(Technique(
            "Granby Roll (Wrestling Guard Retention)",
            "Escape",
            "Guard Retention",
            "purple",
            optimal_for_user=True,
            youtube_url="https://www.youtube.com/watch?v=5Mn3Nhje9gQ",
            description="Wrestling roll adapted for guard recovery",
            key_details=[
                "WRESTLING SKILL: Adapt to BJJ",
                "Roll over shoulder",
                "Invert and recover guard",
                "Creates scrambles",
                "Uses wrestling agility",
                "Modern guard retention"
            ]
        ))

        # No-gi specific (important for wrestlers)
        self.add_technique(Technique(
            "Wrestling-style Mat Returns",
            "Takedown",
            "Wrestling Control",
            "white",
            optimal_for_user=True,
            youtube_url="https://www.youtube.com/watch?v=r7r8ZmRiKok",
            description="Bringing opponent back to mat from standing",
            key_details=[
                "WRESTLING SKILL: Direct transfer",
                "Wrist and waist control",
                "Multiple return techniques",
                "Adapt for gi grips",
                "Maintain top position"
            ]
        ))

        self.add_technique(Technique(
            "Blast Double Leg",
            "Takedown",
            "Leg Attacks",
            "white",
            optimal_for_user=True,
            youtube_url="https://www.youtube.com/watch?v=jq5nDf30wUM",
            description="Explosive double leg tackle",
            key_details=[
                "WRESTLING SKILL: Explosive entry",
                "Deep penetration step",
                "Drive through opponent",
                "Head outside or inside",
                "Use wrestling speed",
                "Watch for guillotine in BJJ"
            ]
        ))

    def add_technique(self, technique):
        """Add a technique to the database"""
        self.techniques.append(technique)

    def get_techniques_by_category(self, category):
        """Get all techniques in a category"""
        return [t for t in self.techniques if t.category == category]

    def get_techniques_by_belt(self, belt_level):
        """Get all techniques for a belt level"""
        belt_order = ["white", "blue", "purple", "brown", "black"]
        belt_index = belt_order.index(belt_level)
        return [t for t in self.techniques
                if belt_order.index(t.belt_level) <= belt_index]

    def get_optimal_techniques(self):
        """Get techniques optimal for user's body type"""
        return [t for t in self.techniques if t.optimal_for_user]

    def get_technique_by_name(self, name):
        """Find technique by name"""
        for t in self.techniques:
            if t.name.lower() == name.lower():
                return t
        return None

    def get_categories(self):
        """Get all unique categories"""
        return list(set(t.category for t in self.techniques))

    def get_hierarchy(self):
        """Get hierarchical structure of all techniques"""
        hierarchy = {}
        for tech in self.techniques:
            if tech.category not in hierarchy:
                hierarchy[tech.category] = {}
            if tech.subcategory not in hierarchy[tech.category]:
                hierarchy[tech.category][tech.subcategory] = []
            hierarchy[tech.category][tech.subcategory].append(tech)
        return hierarchy
