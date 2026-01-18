#!/usr/bin/env python3
"""
BJJ Grappling Training App
Personalized submission grappling practice app with technique database,
belt progression curriculum, and practice tracking optimized for:
- 5'5" height, 5'7.5" wingspan
- Short torso, long legs
- Wrestling background
"""

import sys
import os
from datetime import datetime

from user_profile import UserProfile
from technique_database import TechniqueDatabase
from curriculum import BeltCurriculum
from practice_tracker import PracticeTracker, DailyPracticeScheduler
from data_manager import DataManager


class GrapplingApp:
    def __init__(self):
        self.user_profile = UserProfile()
        self.technique_db = TechniqueDatabase()
        self.practice_tracker = PracticeTracker()
        self.data_manager = DataManager()
        self.curriculum = BeltCurriculum(self.technique_db)
        self.scheduler = DailyPracticeScheduler(
            self.technique_db,
            self.curriculum,
            self.practice_tracker
        )

        # Load saved data
        self._load_data()

    def _load_data(self):
        """Load all saved data"""
        # Load user profile
        profile_data = self.data_manager.load_user_profile()
        if profile_data:
            self.user_profile.current_belt = profile_data.get("current_belt", "white")

        # Load practice data
        practice_data = self.data_manager.load_practice_data()
        if practice_data:
            self.practice_tracker.from_dict(practice_data)

        # Load progress
        self.progress = self.data_manager.load_progress()

    def _save_data(self):
        """Save all data"""
        self.data_manager.save_user_profile(self.user_profile)
        self.data_manager.save_practice_data(self.practice_tracker)
        self.data_manager.save_progress(self.progress)

    def display_menu(self):
        """Display main menu"""
        print("\n" + "="*60)
        print("   BJJ GRAPPLING TRAINING APP")
        print("   Wrestler Edition - Optimized for Your Body Type")
        print("="*60)
        print(f"\nCurrent Belt: {self.user_profile.current_belt.upper()}")
        print(f"Profile: 5'5\", 5'7.5\" wingspan, Wrestling background")
        print("\n--- MAIN MENU ---")
        print("1.  View Today's Practice Plan")
        print("2.  Browse Techniques (by category)")
        print("3.  View Optimal Techniques for Your Body")
        print("4.  View Belt Curriculum & Progress")
        print("5.  Log Practice Session")
        print("6.  View Practice Statistics")
        print("7.  View Weekly Training Summary")
        print("8.  Search Technique by Name")
        print("9.  View Technique Hierarchy")
        print("10. View Wrestling-Specific Advantages")
        print("11. View Techniques Needing Practice")
        print("12. Generate Weekly Training Schedule")
        print("13. Export Training Report")
        print("14. Backup Data")
        print("0.  Exit")
        print("\n" + "="*60)

    def run(self):
        """Main application loop"""
        while True:
            self.display_menu()
            choice = input("\nSelect option: ").strip()

            if choice == "0":
                print("\nSaving data...")
                self._save_data()
                print("Data saved. See you on the mats!")
                break
            elif choice == "1":
                self.show_todays_practice()
            elif choice == "2":
                self.browse_techniques()
            elif choice == "3":
                self.show_optimal_techniques()
            elif choice == "4":
                self.show_curriculum_progress()
            elif choice == "5":
                self.log_practice()
            elif choice == "6":
                self.show_practice_stats()
            elif choice == "7":
                self.show_weekly_summary()
            elif choice == "8":
                self.search_technique()
            elif choice == "9":
                self.show_hierarchy()
            elif choice == "10":
                self.show_wrestling_advantages()
            elif choice == "11":
                self.show_techniques_needing_practice()
            elif choice == "12":
                self.show_weekly_schedule()
            elif choice == "13":
                self.export_report()
            elif choice == "14":
                self.backup_data()
            else:
                print("\nInvalid option. Please try again.")

            input("\nPress Enter to continue...")

    def show_todays_practice(self):
        """Display today's practice plan"""
        print("\n" + "="*60)
        print("   TODAY'S PRACTICE PLAN")
        print("="*60)

        plan = self.scheduler.generate_daily_practice_plan(
            self.user_profile.current_belt,
            duration_minutes=60
        )

        print(f"\nDate: {plan['date']}")
        print(f"Total Duration: {plan['total_duration']} minutes")

        print("\n--- WARM UP (10 min) ---")
        for item in plan["warm_up"]:
            print(f"  • {item['activity']} - {item['duration']} min")

        print("\n--- TECHNIQUE DRILLING (40 min) ---")
        for item in plan["technique_drilling"]:
            print(f"\n  • {item['technique']} ({item['duration']} min)")
            print(f"    Type: {item['type'].upper()}")
            print(f"    Practice: {item['practice_mode']}")
            print(f"    Focus: {item['focus']}")

            # Get YouTube link
            tech = self.technique_db.get_technique_by_name(item['technique'])
            if tech and tech.youtube_url:
                print(f"    Video: {tech.youtube_url}")

        print("\n--- LIVE PRACTICE (10 min) ---")
        for item in plan["live_practice"]:
            print(f"  • {item['activity']} - {item['duration']} min")
            print(f"    Focus: {item['focus']}")

    def browse_techniques(self):
        """Browse techniques by category"""
        print("\n" + "="*60)
        print("   BROWSE TECHNIQUES BY CATEGORY")
        print("="*60)

        categories = self.technique_db.get_categories()
        for i, cat in enumerate(sorted(categories), 1):
            print(f"{i}. {cat}")

        choice = input("\nSelect category (or 0 to go back): ").strip()

        try:
            idx = int(choice) - 1
            if 0 <= idx < len(categories):
                selected_cat = sorted(categories)[idx]
                techs = self.technique_db.get_techniques_by_category(selected_cat)

                print(f"\n--- {selected_cat.upper()} ---")
                for tech in techs:
                    optimal = " ⭐ OPTIMAL" if tech.optimal_for_user else ""
                    print(f"\n• {tech.name}{optimal} [{tech.belt_level.upper()} belt]")
                    print(f"  {tech.description}")
                    if tech.youtube_url:
                        print(f"  Video: {tech.youtube_url}")
                    print(f"  Key Details:")
                    for detail in tech.key_details:
                        print(f"    - {detail}")
        except (ValueError, IndexError):
            print("Invalid selection.")

    def show_optimal_techniques(self):
        """Show techniques optimal for user's body type"""
        print("\n" + "="*60)
        print("   ⭐ TECHNIQUES OPTIMAL FOR YOUR BODY TYPE ⭐")
        print("   (Short torso + Long legs + Wrestling background)")
        print("="*60)

        optimal = self.technique_db.get_optimal_techniques()

        # Group by category
        by_category = {}
        for tech in optimal:
            if tech.category not in by_category:
                by_category[tech.category] = []
            by_category[tech.category].append(tech)

        for category, techs in sorted(by_category.items()):
            print(f"\n--- {category.upper()} ---")
            for tech in techs:
                print(f"\n• {tech.name} [{tech.belt_level.upper()} belt]")
                print(f"  {tech.description}")
                if tech.youtube_url:
                    print(f"  Video: {tech.youtube_url}")

    def show_curriculum_progress(self):
        """Show belt curriculum and progression"""
        print("\n" + "="*60)
        print(f"   BELT CURRICULUM & PROGRESS - {self.user_profile.current_belt.upper()} BELT")
        print("="*60)

        belt_req = self.curriculum.get_belt_requirements(self.user_profile.current_belt)

        print(f"\nFocus: {belt_req.get('focus', 'N/A')}")
        print(f"\nEstimated Time: {belt_req.get('time_estimate', 'N/A')}")

        print("\n--- PRIORITY AREAS ---")
        for area in belt_req.get('priority_areas', []):
            print(f"  • {area}")

        print("\n--- WRESTLER-SPECIFIC GOALS ---")
        for goal in belt_req.get('wrestler_specific_goals', []):
            print(f"  • {goal}")

        if "essential_techniques" in belt_req:
            print("\n--- ESSENTIAL TECHNIQUES ---")
            learned = set(self.practice_tracker.technique_stats.keys())

            for category, tech_list in belt_req["essential_techniques"].items():
                print(f"\n{category.upper().replace('_', ' ')}:")
                for tech_name in tech_list:
                    status = "✓" if tech_name in learned else "○"
                    mastery = ""
                    if tech_name in learned:
                        mastery = f" [{self.practice_tracker.get_mastery_level(tech_name)}]"
                    print(f"  {status} {tech_name}{mastery}")

        # Show progression percentage
        learned_list = list(self.practice_tracker.technique_stats.keys())
        progress_pct = self.curriculum.get_progression_percentage(
            self.user_profile.current_belt,
            learned_list
        )
        print(f"\n--- BELT PROGRESSION ---")
        print(f"Progress: {progress_pct}% complete")
        bar_length = 40
        filled = int(bar_length * progress_pct / 100)
        bar = "█" * filled + "░" * (bar_length - filled)
        print(f"[{bar}] {progress_pct}%")

    def log_practice(self):
        """Log a practice session"""
        print("\n" + "="*60)
        print("   LOG PRACTICE SESSION")
        print("="*60)

        technique_name = input("\nTechnique name: ").strip()

        # Check if technique exists
        tech = self.technique_db.get_technique_by_name(technique_name)
        if not tech:
            print(f"\nTechnique '{technique_name}' not found in database.")
            create = input("Log it anyway? (y/n): ").strip().lower()
            if create != 'y':
                return

        print("\nPractice type:")
        print("1. Dummy/Solo drilling")
        print("2. Live training/Rolling")

        practice_type_choice = input("Select (1 or 2): ").strip()
        practice_type = "dummy" if practice_type_choice == "1" else "live"

        duration = input("Duration (minutes): ").strip()
        try:
            duration = int(duration)
        except ValueError:
            print("Invalid duration")
            return

        quality = input("Quality rating (1-5, or 0 to skip): ").strip()
        try:
            quality = int(quality)
            if quality < 0 or quality > 5:
                quality = 0
        except ValueError:
            quality = 0

        notes = input("Notes (optional): ").strip()

        # Log the practice
        self.practice_tracker.log_practice(
            technique_name,
            practice_type,
            duration,
            notes,
            quality
        )

        print(f"\n✓ Practice logged: {technique_name} ({duration} min, {practice_type})")

        # Auto-save
        self._save_data()

    def show_practice_stats(self):
        """Show practice statistics"""
        print("\n" + "="*60)
        print("   PRACTICE STATISTICS")
        print("="*60)

        if not self.practice_tracker.technique_stats:
            print("\nNo practice data yet. Start logging your sessions!")
            return

        print("\n--- TECHNIQUE MASTERY LEVELS ---\n")

        for tech_name in sorted(self.practice_tracker.technique_stats.keys()):
            stats = self.practice_tracker.technique_stats[tech_name]
            mastery = self.practice_tracker.get_mastery_level(tech_name)

            print(f"• {tech_name}")
            print(f"  Mastery: {mastery}")
            print(f"  Total Sessions: {stats['total_sessions']}")
            print(f"  Total Time: {stats['total_minutes']} minutes")
            print(f"  Dummy: {stats['dummy_sessions']} | Live: {stats['live_sessions']}")
            if stats['average_quality'] > 0:
                print(f"  Avg Quality: {stats['average_quality']:.1f}/5")
            print(f"  Last Practiced: {stats['last_practiced'][:10] if stats['last_practiced'] else 'Never'}")
            print()

    def show_weekly_summary(self):
        """Show weekly training summary"""
        print("\n" + "="*60)
        print("   WEEKLY TRAINING SUMMARY")
        print("="*60)

        summary = self.practice_tracker.get_weekly_summary()

        print(f"\nTotal Sessions: {summary['total_sessions']}")
        print(f"Total Training Time: {summary['total_minutes']} minutes")
        print(f"Dummy Sessions: {summary['dummy_sessions']}")
        print(f"Live Sessions: {summary['live_sessions']}")
        print(f"Techniques Practiced: {summary['techniques_practiced']}")
        print(f"Average Session Length: {summary['average_session_length']:.1f} minutes")

        recent = self.practice_tracker.get_recent_practice(7)
        if recent:
            print("\n--- RECENT SESSIONS ---")
            for log in recent[:10]:
                date = log.timestamp[:10]
                print(f"\n{date}: {log.technique_name}")
                print(f"  Type: {log.practice_type} | Duration: {log.duration_minutes} min")
                if log.quality_rating > 0:
                    print(f"  Quality: {'★' * log.quality_rating}{'☆' * (5 - log.quality_rating)}")
                if log.notes:
                    print(f"  Notes: {log.notes}")

    def search_technique(self):
        """Search for a technique"""
        print("\n" + "="*60)
        print("   SEARCH TECHNIQUE")
        print("="*60)

        query = input("\nEnter technique name: ").strip()

        tech = self.technique_db.get_technique_by_name(query)

        if tech:
            optimal = " ⭐ OPTIMAL FOR YOUR BODY TYPE" if tech.optimal_for_user else ""
            print(f"\n{tech.name}{optimal}")
            print(f"Belt Level: {tech.belt_level.upper()}")
            print(f"Category: {tech.category} - {tech.subcategory}")
            print(f"\nDescription: {tech.description}")
            print(f"\nKey Details:")
            for detail in tech.key_details:
                print(f"  • {detail}")
            if tech.youtube_url:
                print(f"\nVideo Tutorial: {tech.youtube_url}")

            # Show practice stats if available
            stats = self.practice_tracker.get_technique_stats(tech.name)
            if stats:
                mastery = self.practice_tracker.get_mastery_level(tech.name)
                print(f"\nYour Progress:")
                print(f"  Mastery Level: {mastery}")
                print(f"  Sessions: {stats['total_sessions']}")
                print(f"  Total Time: {stats['total_minutes']} min")
        else:
            print(f"\nTechnique '{query}' not found.")

    def show_hierarchy(self):
        """Show technique hierarchy"""
        print("\n" + "="*60)
        print("   TECHNIQUE HIERARCHY")
        print("="*60)

        hierarchy = self.technique_db.get_hierarchy()

        for category in sorted(hierarchy.keys()):
            print(f"\n{category.upper()}")
            for subcategory in sorted(hierarchy[category].keys()):
                print(f"  └─ {subcategory}")
                for tech in hierarchy[category][subcategory]:
                    optimal = " ⭐" if tech.optimal_for_user else ""
                    print(f"      • {tech.name} [{tech.belt_level}]{optimal}")

    def show_wrestling_advantages(self):
        """Show wrestling-specific advantages and adaptations"""
        print("\n" + "="*60)
        print("   WRESTLING ADVANTAGES IN BJJ")
        print("="*60)

        advantages = self.user_profile.get_wrestling_advantages()

        print("\n--- EXISTING STRENGTHS FROM WRESTLING ---")
        for strength in advantages["existing_strengths"]:
            print(f"  ✓ {strength}")

        print("\n--- BJJ ADAPTATIONS NEEDED ---")
        for adaptation in advantages["bjj_adaptations_needed"]:
            print(f"  • {adaptation}")

        print("\n--- IDEAL GAME PLAN ---")
        for phase in advantages["ideal_game_plan"]:
            print(f"  → {phase}")

        print("\n--- COMMON WRESTLER MISTAKES TO AVOID ---")
        for mistake in advantages["common_wrestler_mistakes_to_avoid"]:
            print(f"  ⚠ {mistake}")

        # Also show body type advantages
        body_advantages = self.user_profile.get_body_type_advantages()
        print("\n--- BODY TYPE ADVANTAGES (Short Torso + Long Legs) ---")
        print("\nFavorable Submissions:")
        for sub in body_advantages["favorable_submissions"]:
            print(f"  ✓ {sub}")

        print("\nFavorable Guards:")
        for guard in body_advantages["favorable_guards"]:
            print(f"  ✓ {guard}")

        print(f"\nNote: {body_advantages['notes']}")

    def show_techniques_needing_practice(self):
        """Show techniques that haven't been practiced recently"""
        print("\n" + "="*60)
        print("   TECHNIQUES NEEDING PRACTICE")
        print("="*60)

        needing = self.practice_tracker.get_techniques_needing_practice(threshold_days=7)

        if not needing:
            print("\n✓ All techniques have been practiced recently!")
        else:
            print("\nTechniques not practiced in the last 7 days:\n")
            for tech_data in needing:
                print(f"• {tech_data['technique']}")
                print(f"  Days since practice: {tech_data['days_since_practice']}")
                print(f"  Total sessions: {tech_data['total_sessions']}")
                print()

    def show_weekly_schedule(self):
        """Generate and show weekly training schedule"""
        print("\n" + "="*60)
        print("   WEEKLY TRAINING SCHEDULE")
        print("="*60)

        days = input("\nTraining days per week (3-6): ").strip()
        try:
            days = int(days)
            if days < 3 or days > 6:
                days = 4
        except ValueError:
            days = 4

        schedule = self.scheduler.create_weekly_training_schedule(
            self.user_profile.current_belt,
            training_days_per_week=days
        )

        for day_name, day_plan in schedule.items():
            print(f"\n{'='*60}")
            print(f"{day_name}")
            print(f"{'='*60}")
            print("\nFocus Areas:")
            for area in day_plan["focus_areas"]:
                print(f"  • {area}")

            plan = day_plan["practice_plan"]
            print("\nDrilling Plan:")
            for drill in plan["technique_drilling"]:
                print(f"  • {drill['technique']} ({drill['duration']} min)")

    def export_report(self):
        """Export training report"""
        print("\n" + "="*60)
        print("   EXPORT TRAINING REPORT")
        print("="*60)

        report_path = self.data_manager.export_report(
            self.practice_tracker,
            self.curriculum,
            self.user_profile
        )

        print(f"\n✓ Training report exported to:")
        print(f"  {report_path}")

    def backup_data(self):
        """Backup all data"""
        print("\n" + "="*60)
        print("   BACKUP DATA")
        print("="*60)

        backup_path = self.data_manager.backup_data()

        print(f"\n✓ Data backed up to:")
        print(f"  {backup_path}")


def main():
    """Main entry point"""
    app = GrapplingApp()
    app.run()


if __name__ == "__main__":
    main()
