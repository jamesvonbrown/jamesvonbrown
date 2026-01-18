"""
Mobile Web Interface for BJJ Grappling App
Flask-based web server for phone access
"""

from flask import Flask, render_template, request, jsonify, redirect, url_for
import json
from datetime import datetime

from user_profile import UserProfile
from technique_database import TechniqueDatabase
from curriculum import BeltCurriculum
from practice_tracker import PracticeTracker, DailyPracticeScheduler
from data_manager import DataManager

app = Flask(__name__)

# Initialize app components
user_profile = UserProfile()
technique_db = TechniqueDatabase()
practice_tracker = PracticeTracker()
data_manager = DataManager()
curriculum = BeltCurriculum(technique_db)
scheduler = DailyPracticeScheduler(technique_db, curriculum, practice_tracker)

# Load saved data
def load_data():
    global user_profile, practice_tracker

    profile_data = data_manager.load_user_profile()
    if profile_data:
        user_profile.current_belt = profile_data.get("current_belt", "white")

    practice_data = data_manager.load_practice_data()
    if practice_data:
        practice_tracker.from_dict(practice_data)

load_data()

@app.route('/')
def index():
    """Home page"""
    weekly_summary = practice_tracker.get_weekly_summary()
    optimal_count = len(technique_db.get_optimal_techniques())

    return render_template('index.html',
                         profile=user_profile,
                         weekly_summary=weekly_summary,
                         optimal_count=optimal_count)

@app.route('/today')
def today():
    """Today's practice plan"""
    plan = scheduler.generate_daily_practice_plan(
        user_profile.current_belt,
        duration_minutes=60
    )

    # Enrich plan with technique details
    for drill in plan['technique_drilling']:
        tech = technique_db.get_technique_by_name(drill['technique'])
        if tech:
            drill['tech_obj'] = tech

    return render_template('today.html', plan=plan)

@app.route('/techniques')
def techniques():
    """Browse all techniques"""
    category = request.args.get('category', None)

    if category:
        techs = technique_db.get_techniques_by_category(category)
        title = f"{category} Techniques"
    else:
        techs = technique_db.techniques
        title = "All Techniques"

    categories = technique_db.get_categories()

    return render_template('techniques.html',
                         techniques=techs,
                         categories=sorted(categories),
                         title=title,
                         selected_category=category)

@app.route('/technique/<technique_name>')
def technique_detail(technique_name):
    """Technique detail page"""
    tech = technique_db.get_technique_by_name(technique_name)
    if not tech:
        return "Technique not found", 404

    stats = practice_tracker.get_technique_stats(technique_name)
    mastery = practice_tracker.get_mastery_level(technique_name) if stats else "Not Started"

    return render_template('technique_detail.html',
                         technique=tech,
                         stats=stats,
                         mastery=mastery)

@app.route('/optimal')
def optimal():
    """Optimal techniques for body type"""
    techs = technique_db.get_optimal_techniques()

    # Group by category
    by_category = {}
    for tech in techs:
        if tech.category not in by_category:
            by_category[tech.category] = []
        by_category[tech.category].append(tech)

    return render_template('optimal.html', techniques_by_category=by_category)

@app.route('/curriculum')
def curriculum_page():
    """Belt curriculum and progress"""
    belt_req = curriculum.get_belt_requirements(user_profile.current_belt)

    learned = set(practice_tracker.technique_stats.keys())
    progress_pct = curriculum.get_progression_percentage(
        user_profile.current_belt,
        list(learned)
    )

    # Mark techniques as learned/not learned
    if "essential_techniques" in belt_req:
        for category, tech_list in belt_req["essential_techniques"].items():
            belt_req[f"{category}_status"] = []
            for tech_name in tech_list:
                status = {
                    "name": tech_name,
                    "learned": tech_name in learned,
                    "mastery": practice_tracker.get_mastery_level(tech_name) if tech_name in learned else "Not Started"
                }
                belt_req[f"{category}_status"].append(status)

    return render_template('curriculum.html',
                         belt_req=belt_req,
                         current_belt=user_profile.current_belt,
                         progress_pct=progress_pct)

@app.route('/log', methods=['GET', 'POST'])
def log_practice_page():
    """Log practice session"""
    if request.method == 'POST':
        technique_name = request.form.get('technique_name')
        practice_type = request.form.get('practice_type')
        duration = int(request.form.get('duration', 0))
        quality = int(request.form.get('quality', 0))
        notes = request.form.get('notes', '')

        practice_tracker.log_practice(
            technique_name,
            practice_type,
            duration,
            notes,
            quality
        )

        data_manager.save_practice_data(practice_tracker)

        return redirect(url_for('stats'))

    # GET request - show form
    return render_template('log.html')

@app.route('/stats')
def stats():
    """Practice statistics"""
    weekly = practice_tracker.get_weekly_summary()
    recent = practice_tracker.get_recent_practice(7)

    # Get all technique stats
    all_stats = []
    for tech_name in sorted(practice_tracker.technique_stats.keys()):
        tech_stats = practice_tracker.technique_stats[tech_name]
        all_stats.append({
            "name": tech_name,
            "mastery": practice_tracker.get_mastery_level(tech_name),
            "sessions": tech_stats['total_sessions'],
            "minutes": tech_stats['total_minutes'],
            "dummy": tech_stats['dummy_sessions'],
            "live": tech_stats['live_sessions'],
            "quality": tech_stats['average_quality']
        })

    return render_template('stats.html',
                         weekly=weekly,
                         recent=recent,
                         all_stats=all_stats)

@app.route('/wrestling')
def wrestling():
    """Wrestling advantages and adaptations"""
    advantages = user_profile.get_wrestling_advantages()
    body_advantages = user_profile.get_body_type_advantages()

    return render_template('wrestling.html',
                         advantages=advantages,
                         body_advantages=body_advantages)

@app.route('/api/techniques')
def api_techniques():
    """API endpoint for techniques"""
    techs = [t.to_dict() for t in technique_db.techniques]
    return jsonify(techs)

@app.route('/api/log', methods=['POST'])
def api_log():
    """API endpoint to log practice"""
    data = request.json

    practice_tracker.log_practice(
        data['technique_name'],
        data['practice_type'],
        data['duration'],
        data.get('notes', ''),
        data.get('quality', 0)
    )

    data_manager.save_practice_data(practice_tracker)

    return jsonify({"status": "success"})

if __name__ == '__main__':
    print("\n" + "="*60)
    print("  BJJ GRAPPLING APP - MOBILE WEB INTERFACE")
    print("="*60)
    print("\n📱 Starting web server...")
    print("\nAccess from your phone:")
    print("  1. Make sure phone and computer are on same WiFi")
    print("  2. Open browser on phone")
    print("  3. Go to: http://<YOUR_COMPUTER_IP>:5000")
    print("\nAccess from this computer:")
    print("  http://localhost:5000")
    print("\n" + "="*60 + "\n")

    app.run(host='0.0.0.0', port=5000, debug=True)
