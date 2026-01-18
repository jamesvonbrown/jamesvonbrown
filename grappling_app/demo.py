#!/usr/bin/env python3
"""
Demo Script - Shows key features of the app
"""

from user_profile import UserProfile
from technique_database import TechniqueDatabase
from curriculum import BeltCurriculum
from practice_tracker import PracticeTracker, DailyPracticeScheduler

def main():
    print("="*70)
    print("  BJJ GRAPPLING APP DEMO - WRESTLER EDITION")
    print("="*70)

    # Initialize
    profile = UserProfile()
    db = TechniqueDatabase()
    curriculum = BeltCurriculum(db)
    tracker = PracticeTracker()
    scheduler = DailyPracticeScheduler(db, curriculum, tracker)

    # Show profile
    print("\n📋 YOUR PROFILE")
    print("-" * 70)
    print(f"Height: {profile.height}\" (5'5\")")
    print(f"Wingspan: {profile.wingspan}\" (5'7.5\")")
    print(f"Ape Index: +{profile.get_ape_index()}\"")
    print(f"Body Type: Short torso, long legs")
    print(f"Wrestling Experience: {'Yes ✓' if profile.wrestling_experience else 'No'}")
    print(f"Current Belt: {profile.current_belt.upper()}")

    # Show optimal techniques
    print("\n⭐ OPTIMAL TECHNIQUES FOR YOUR BODY TYPE")
    print("-" * 70)
    optimal = db.get_optimal_techniques()
    print(f"Found {len(optimal)} techniques optimized for you!\n")

    # Show a few examples by category
    guards = [t for t in optimal if t.category == "Position" and "Guard" in t.subcategory][:3]
    print("Guards (Long legs advantage):")
    for tech in guards:
        print(f"  • {tech.name} - {tech.description}")

    subs = [t for t in optimal if t.category == "Submission"][:3]
    print("\nSubmissions:")
    for tech in subs:
        print(f"  • {tech.name} - {tech.description}")

    wrestling = [t for t in optimal if "WRESTLING" in str(tech.key_details)][:3]
    print("\nWrestling-Based:")
    for tech in wrestling:
        print(f"  • {tech.name} - {tech.description}")

    # Show wrestling advantages
    print("\n🤼 WRESTLING ADVANTAGES")
    print("-" * 70)
    advantages = profile.get_wrestling_advantages()
    print("Existing Strengths:")
    for strength in advantages["existing_strengths"][:5]:
        print(f"  ✓ {strength}")

    print("\nKey Adaptations Needed:")
    for adapt in advantages["bjj_adaptations_needed"][:3]:
        print(f"  • {adapt}")

    # Show curriculum
    print("\n📚 WHITE BELT CURRICULUM")
    print("-" * 70)
    white_belt = curriculum.get_belt_requirements("white")
    print(f"Focus: {white_belt['focus']}")
    print(f"Time Estimate: {white_belt['time_estimate']}")

    print("\nPriority Areas:")
    for area in white_belt["priority_areas"][:3]:
        print(f"  → {area}")

    # Generate practice plan
    print("\n📅 TODAY'S PRACTICE PLAN")
    print("-" * 70)
    plan = scheduler.generate_daily_practice_plan("white", duration_minutes=60)

    print("Warm-up (10 min):")
    for item in plan["warm_up"]:
        print(f"  • {item['activity']} - {item['duration']} min")

    print("\nTechnique Drilling (40 min):")
    for drill in plan["technique_drilling"]:
        print(f"\n  • {drill['technique']} ({drill['duration']} min)")
        print(f"    Focus: {drill['focus']}")

        # Get technique details
        tech = db.get_technique_by_name(drill['technique'])
        if tech:
            print(f"    Video: {tech.youtube_url}")

    print("\nLive Practice (10 min):")
    for item in plan["live_practice"]:
        print(f"  • {item['activity']} - {item['duration']} min")

    # Simulate some practice logging
    print("\n📊 DEMO: Logging Practice Sessions")
    print("-" * 70)

    # Log a few sessions
    tracker.log_practice("De La Riva Guard", "dummy", 20, "Good hook depth, need to work on off-balancing", 3)
    tracker.log_practice("Triangle Choke", "dummy", 15, "Angle is getting better", 4)
    tracker.log_practice("Darce Choke", "live", 30, "Hit it twice in rolling!", 4)

    print("Logged 3 practice sessions!")

    # Show stats
    weekly = tracker.get_weekly_summary()
    print(f"\nWeekly Summary:")
    print(f"  Sessions: {weekly['total_sessions']}")
    print(f"  Total Time: {weekly['total_minutes']} minutes")
    print(f"  Dummy: {weekly['dummy_sessions']} | Live: {weekly['live_sessions']}")

    print("\nTechnique Stats:")
    for tech_name in sorted(tracker.technique_stats.keys()):
        stats = tracker.technique_stats[tech_name]
        mastery = tracker.get_mastery_level(tech_name)
        print(f"  • {tech_name}: {mastery} ({stats['total_sessions']} sessions)")

    # Show hierarchy sample
    print("\n🗂️  TECHNIQUE HIERARCHY (Sample)")
    print("-" * 70)
    hierarchy = db.get_hierarchy()

    # Show just positions
    if "Position" in hierarchy:
        print("POSITION")
        for subcat in list(hierarchy["Position"].keys())[:2]:
            print(f"  └─ {subcat}")
            for tech in hierarchy["Position"][subcat][:2]:
                optimal_mark = " ⭐" if tech.optimal_for_user else ""
                print(f"      • {tech.name} [{tech.belt_level}]{optimal_mark}")

    print("\n" + "="*70)
    print("  DEMO COMPLETE!")
    print("  Run 'python3 main.py' to start the full application")
    print("="*70)

if __name__ == "__main__":
    main()
