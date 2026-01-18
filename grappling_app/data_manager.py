"""
Data Persistence Module
Manages saving and loading user data, practice logs, and progress
"""

import json
import os
from pathlib import Path


class DataManager:
    def __init__(self, data_dir="data"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)

        self.user_profile_file = self.data_dir / "user_profile.json"
        self.practice_data_file = self.data_dir / "practice_data.json"
        self.progress_file = self.data_dir / "progress.json"

    def save_user_profile(self, user_profile):
        """Save user profile to JSON"""
        with open(self.user_profile_file, 'w') as f:
            json.dump(user_profile.to_dict(), f, indent=2)

    def load_user_profile(self):
        """Load user profile from JSON"""
        if self.user_profile_file.exists():
            with open(self.user_profile_file, 'r') as f:
                return json.load(f)
        return None

    def save_practice_data(self, practice_tracker):
        """Save practice tracker data"""
        with open(self.practice_data_file, 'w') as f:
            json.dump(practice_tracker.to_dict(), f, indent=2)

    def load_practice_data(self):
        """Load practice tracker data"""
        if self.practice_data_file.exists():
            with open(self.practice_data_file, 'r') as f:
                return json.load(f)
        return None

    def save_progress(self, progress_data):
        """Save belt progression and learned techniques"""
        with open(self.progress_file, 'w') as f:
            json.dump(progress_data, f, indent=2)

    def load_progress(self):
        """Load belt progression and learned techniques"""
        if self.progress_file.exists():
            with open(self.progress_file, 'r') as f:
                return json.load(f)
        return {"current_belt": "white", "learned_techniques": [], "completed_goals": []}

    def backup_data(self):
        """Create a backup of all data"""
        import shutil
        from datetime import datetime

        backup_dir = self.data_dir / "backups"
        backup_dir.mkdir(exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = backup_dir / f"backup_{timestamp}"
        backup_path.mkdir(exist_ok=True)

        # Copy all JSON files to backup
        for file in self.data_dir.glob("*.json"):
            shutil.copy(file, backup_path / file.name)

        return str(backup_path)

    def export_report(self, practice_tracker, curriculum, user_profile):
        """Export a training report in markdown format"""
        from datetime import datetime

        report_file = self.data_dir / f"training_report_{datetime.now().strftime('%Y%m%d')}.md"

        weekly_summary = practice_tracker.get_weekly_summary()

        with open(report_file, 'w') as f:
            f.write(f"# BJJ Training Report\n\n")
            f.write(f"**Date:** {datetime.now().strftime('%Y-%m-%d')}\n\n")

            # Profile
            f.write(f"## Profile\n\n")
            f.write(f"- Height: {user_profile.height}\" ({int(user_profile.height//12)}'{int(user_profile.height%12)}\")\n")
            f.write(f"- Wingspan: {user_profile.wingspan}\" ({int(user_profile.wingspan//12)}'{int(user_profile.wingspan%12)}\")\n")
            f.write(f"- Ape Index: +{user_profile.get_ape_index()}\"\n")
            f.write(f"- Body Type: Short torso, long legs\n")
            f.write(f"- Wrestling Experience: {'Yes' if user_profile.wrestling_experience else 'No'}\n")
            f.write(f"- Current Belt: {user_profile.current_belt.upper()}\n\n")

            # Weekly summary
            f.write(f"## This Week's Training\n\n")
            f.write(f"- Total Sessions: {weekly_summary['total_sessions']}\n")
            f.write(f"- Total Time: {weekly_summary['total_minutes']} minutes\n")
            f.write(f"- Dummy Training: {weekly_summary['dummy_sessions']} sessions\n")
            f.write(f"- Live Training: {weekly_summary['live_sessions']} sessions\n")
            f.write(f"- Techniques Practiced: {weekly_summary['techniques_practiced']}\n")
            f.write(f"- Average Session: {weekly_summary['average_session_length']:.1f} minutes\n\n")

            # Technique stats
            f.write(f"## Technique Mastery Levels\n\n")
            for tech_name, stats in sorted(practice_tracker.technique_stats.items()):
                mastery = practice_tracker.get_mastery_level(tech_name)
                f.write(f"- **{tech_name}**: {mastery} ")
                f.write(f"({stats['total_sessions']} sessions, {stats['total_minutes']} min, ")
                f.write(f"avg quality: {stats['average_quality']:.1f}/5)\n")

            f.write(f"\n## Techniques Needing Practice\n\n")
            needing = practice_tracker.get_techniques_needing_practice(7)
            for tech_data in needing[:10]:
                f.write(f"- {tech_data['technique']}: {tech_data['days_since_practice']} days since last practice\n")

        return str(report_file)
