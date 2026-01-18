"""
Practice Tracking Module
Logs practice sessions for dummy work and live training
"""

import json
from datetime import datetime, timedelta


class PracticeLog:
    def __init__(self, technique_name, practice_type, duration_minutes, notes="", video_url=""):
        self.technique_name = technique_name
        self.practice_type = practice_type  # "dummy" or "live"
        self.duration_minutes = duration_minutes
        self.notes = notes
        self.video_url = video_url
        self.timestamp = datetime.now().isoformat()
        self.quality_rating = 0  # 1-5 scale

    def to_dict(self):
        return {
            "technique_name": self.technique_name,
            "practice_type": self.practice_type,
            "duration_minutes": self.duration_minutes,
            "notes": self.notes,
            "video_url": self.video_url,
            "timestamp": self.timestamp,
            "quality_rating": self.quality_rating
        }


class PracticeTracker:
    def __init__(self):
        self.practice_logs = []
        self.daily_goals = {}
        self.technique_stats = {}

    def log_practice(self, technique_name, practice_type, duration_minutes, notes="", quality=0):
        """Log a practice session"""
        log = PracticeLog(technique_name, practice_type, duration_minutes, notes)
        log.quality_rating = quality
        self.practice_logs.append(log)

        # Update stats
        if technique_name not in self.technique_stats:
            self.technique_stats[technique_name] = {
                "total_sessions": 0,
                "total_minutes": 0,
                "dummy_sessions": 0,
                "live_sessions": 0,
                "last_practiced": None,
                "average_quality": 0,
                "quality_ratings": []
            }

        stats = self.technique_stats[technique_name]
        stats["total_sessions"] += 1
        stats["total_minutes"] += duration_minutes
        stats["last_practiced"] = datetime.now().isoformat()

        if practice_type == "dummy":
            stats["dummy_sessions"] += 1
        else:
            stats["live_sessions"] += 1

        if quality > 0:
            stats["quality_ratings"].append(quality)
            stats["average_quality"] = sum(stats["quality_ratings"]) / len(stats["quality_ratings"])

        return log

    def get_technique_stats(self, technique_name):
        """Get statistics for a specific technique"""
        return self.technique_stats.get(technique_name, None)

    def get_recent_practice(self, days=7):
        """Get practice logs from recent days"""
        cutoff = datetime.now() - timedelta(days=days)
        recent = []

        for log in self.practice_logs:
            log_time = datetime.fromisoformat(log.timestamp)
            if log_time >= cutoff:
                recent.append(log)

        return sorted(recent, key=lambda x: x.timestamp, reverse=True)

    def get_practice_by_date(self, date_str):
        """Get all practice for a specific date (YYYY-MM-DD)"""
        target_date = datetime.fromisoformat(date_str).date()
        date_logs = []

        for log in self.practice_logs:
            log_date = datetime.fromisoformat(log.timestamp).date()
            if log_date == target_date:
                date_logs.append(log)

        return date_logs

    def get_weekly_summary(self):
        """Get summary of this week's training"""
        recent = self.get_recent_practice(7)

        summary = {
            "total_sessions": len(recent),
            "total_minutes": sum(log.duration_minutes for log in recent),
            "dummy_sessions": len([log for log in recent if log.practice_type == "dummy"]),
            "live_sessions": len([log for log in recent if log.practice_type == "live"]),
            "techniques_practiced": len(set(log.technique_name for log in recent)),
            "average_session_length": 0
        }

        if summary["total_sessions"] > 0:
            summary["average_session_length"] = summary["total_minutes"] / summary["total_sessions"]

        return summary

    def get_techniques_needing_practice(self, threshold_days=7):
        """Get techniques that haven't been practiced recently"""
        cutoff = datetime.now() - timedelta(days=threshold_days)
        needing_practice = []

        for tech_name, stats in self.technique_stats.items():
            if stats["last_practiced"]:
                last_practice = datetime.fromisoformat(stats["last_practiced"])
                if last_practice < cutoff:
                    days_since = (datetime.now() - last_practice).days
                    needing_practice.append({
                        "technique": tech_name,
                        "days_since_practice": days_since,
                        "total_sessions": stats["total_sessions"]
                    })

        return sorted(needing_practice, key=lambda x: x["days_since_practice"], reverse=True)

    def set_daily_goal(self, technique_name, goal_type="practice"):
        """Set a daily practice goal for a technique"""
        today = datetime.now().date().isoformat()
        if today not in self.daily_goals:
            self.daily_goals[today] = []

        self.daily_goals[today].append({
            "technique": technique_name,
            "goal_type": goal_type,
            "completed": False
        })

    def complete_daily_goal(self, technique_name):
        """Mark a daily goal as completed"""
        today = datetime.now().date().isoformat()
        if today in self.daily_goals:
            for goal in self.daily_goals[today]:
                if goal["technique"] == technique_name:
                    goal["completed"] = True

    def get_todays_goals(self):
        """Get today's practice goals"""
        today = datetime.now().date().isoformat()
        return self.daily_goals.get(today, [])

    def get_mastery_level(self, technique_name):
        """Calculate mastery level for a technique"""
        stats = self.technique_stats.get(technique_name)
        if not stats:
            return "Not Started"

        sessions = stats["total_sessions"]
        avg_quality = stats["average_quality"]
        live_sessions = stats["live_sessions"]

        # Mastery calculation
        if sessions < 5 or avg_quality < 2:
            return "Beginner"
        elif sessions < 15 or avg_quality < 3 or live_sessions < 3:
            return "Learning"
        elif sessions < 30 or avg_quality < 4 or live_sessions < 10:
            return "Competent"
        elif sessions < 50 or avg_quality < 4.5 or live_sessions < 20:
            return "Proficient"
        else:
            return "Mastery"

    def to_dict(self):
        """Convert tracker to dictionary for persistence"""
        return {
            "practice_logs": [log.to_dict() for log in self.practice_logs],
            "daily_goals": self.daily_goals,
            "technique_stats": self.technique_stats
        }

    def from_dict(self, data):
        """Load tracker from dictionary"""
        self.practice_logs = []
        for log_data in data.get("practice_logs", []):
            log = PracticeLog(
                log_data["technique_name"],
                log_data["practice_type"],
                log_data["duration_minutes"],
                log_data.get("notes", ""),
                log_data.get("video_url", "")
            )
            log.timestamp = log_data["timestamp"]
            log.quality_rating = log_data.get("quality_rating", 0)
            self.practice_logs.append(log)

        self.daily_goals = data.get("daily_goals", {})
        self.technique_stats = data.get("technique_stats", {})


class DailyPracticeScheduler:
    def __init__(self, technique_db, curriculum, practice_tracker):
        self.technique_db = technique_db
        self.curriculum = curriculum
        self.practice_tracker = practice_tracker

    def generate_daily_practice_plan(self, current_belt, focus_areas=None, duration_minutes=60):
        """Generate a personalized daily practice plan"""
        plan = {
            "date": datetime.now().date().isoformat(),
            "total_duration": duration_minutes,
            "warm_up": [],
            "technique_drilling": [],
            "live_practice": [],
            "cool_down": []
        }

        # Warm up (10 minutes)
        plan["warm_up"] = [
            {"activity": "Shrimping (hip escapes)", "duration": 3, "type": "fundamental"},
            {"activity": "Granby rolls", "duration": 3, "type": "wrestling_movement"},
            {"activity": "Technical stand-ups", "duration": 2, "type": "fundamental"},
            {"activity": "Break falls", "duration": 2, "type": "fundamental"}
        ]

        # Get techniques that need practice
        needing_practice = self.practice_tracker.get_techniques_needing_practice(threshold_days=5)

        # Get optimal techniques for body type
        optimal_techniques = self.technique_db.get_optimal_techniques()

        # Get belt-appropriate techniques
        belt_techniques = self.technique_db.get_techniques_by_belt(current_belt)

        # Create drilling plan (40 minutes for 60-minute session)
        drill_time = duration_minutes - 20  # Minus warm-up and cool-down

        # Priority 1: Techniques needing practice
        for tech_data in needing_practice[:2]:
            tech = self.technique_db.get_technique_by_name(tech_data["technique"])
            if tech:
                plan["technique_drilling"].append({
                    "technique": tech.name,
                    "duration": 10,
                    "type": "review",
                    "practice_mode": "dummy",
                    "focus": f"Haven't practiced in {tech_data['days_since_practice']} days"
                })

        # Priority 2: New optimal techniques
        learned_techs = set(self.practice_tracker.technique_stats.keys())
        for tech in optimal_techniques:
            if tech.name not in learned_techs and tech.belt_level == current_belt:
                plan["technique_drilling"].append({
                    "technique": tech.name,
                    "duration": 15,
                    "type": "learning",
                    "practice_mode": "dummy",
                    "focus": "OPTIMAL for your body type - watch video and drill slowly"
                })
                break  # Just one new technique per session

        # Priority 3: Random technique from current belt
        import random
        random_tech = random.choice([t for t in belt_techniques if t.optimal_for_user])
        if random_tech:
            plan["technique_drilling"].append({
                "technique": random_tech.name,
                "duration": 10,
                "type": "maintenance",
                "practice_mode": "dummy",
                "focus": "Keep sharp on fundamentals"
            })

        # Live practice recommendations (10 minutes)
        plan["live_practice"] = [
            {
                "activity": "Positional sparring from guard",
                "duration": 5,
                "focus": "Work on guard retention and sweeps"
            },
            {
                "activity": "Situational rolling - start from worst position",
                "duration": 5,
                "focus": "Escape and survival practice"
            }
        ]

        return plan

    def create_weekly_training_schedule(self, current_belt, training_days_per_week=4):
        """Create a full week training schedule"""
        week_schedule = {}

        focus_rotation = [
            {"name": "Guard Day", "focus": ["Guard positions", "Sweeps", "Guard submissions"]},
            {"name": "Top Game Day", "focus": ["Passes", "Top control", "Submissions from top"]},
            {"name": "Takedowns & Wrestling", "focus": ["Takedowns", "Front headlock", "Scrambles"]},
            {"name": "Legs & Back", "focus": ["Leg locks", "Back attacks", "Turtle attacks"]},
            {"name": "Competition Simulation", "focus": ["Full rounds", "Strategy", "Cardio"]},
        ]

        for day in range(training_days_per_week):
            focus = focus_rotation[day % len(focus_rotation)]
            week_schedule[f"Day {day + 1} - {focus['name']}"] = {
                "focus_areas": focus["focus"],
                "practice_plan": self.generate_daily_practice_plan(current_belt)
            }

        return week_schedule
