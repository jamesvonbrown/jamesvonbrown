# BJJ Grappling Training App - Wrestler Edition

A comprehensive submission grappling practice application specifically designed for:
- **Height**: 5'5" (65 inches)
- **Wingspan**: 5'7.5" (67.5 inches)
- **Body Type**: Short torso, relatively longer legs
- **Background**: Wrestling experience

## Features

### 1. Personalized Technique Database
- **60+ techniques** organized hierarchically by:
  - Positions (Guard, Top Control, Transitions)
  - Takedowns (Wrestling-adapted for BJJ)
  - Submissions (Chokes, Joint Locks, Leg Locks)
  - Sweeps
  - Escapes
  - Guard Passes

- **Body-Type Optimization**: Techniques marked as OPTIMAL for your specific build
  - Long legs = Excellent for guards (DLR, X-Guard, Spider, Triangle chokes)
  - Short torso + Wrestling = Front headlock game, pressure passing
  - Leg entanglements and distance management

- **🆕 Research-Based Competition Statistics**
  - Success rates and finish rates from elite BJJ competitions (2024-2025 data)
  - ADCC, IBJJF Worlds, CJI, EBI statistics integrated
  - Specific data for body-type advantages
  - 7+ key techniques include detailed competition analysis:
    - Rear Naked Choke: 78% finish rate from back control
    - Triangle Choke: 62% success (better with long legs - confirmed by research!)
    - X-Guard: 63% sweep success rate
    - Wrestling takedowns: 41% in no-gi vs 14% in gi
    - Inside Heel Hook: 20 finishes at 2025 IBJJF No-Gi Worlds (2nd most common)
    - And more!

### 2. Wrestling-Specific Adaptations
- Front headlock series (Darce, Anaconda, Guillotine)
- Pressure passing techniques (Smash pass, Stack pass)
- Turtle position awareness (critical for wrestlers to avoid)
- Takedown adaptations for gi/no-gi BJJ
- Scrambling and guard retention using wrestling agility
- Granby rolls for modern guard retention

### 3. Belt Progression Curriculum
Comprehensive curriculum for each belt level:
- **White Belt**: Fundamentals + Wrestling integration, submission defense
- **Blue Belt**: Guard development (leg-based systems), front headlock attacks
- **Purple Belt**: Specialized game (Berimbolo, deep half, leg drags)
- **Brown Belt**: Leg locks, competition mastery
- **Black Belt**: Complete mastery and teaching

Each belt includes:
- Essential techniques to learn
- Priority areas
- Wrestler-specific goals
- Common mistakes to avoid
- Progress tracking

### 4. Daily Practice Planning
- Automated practice plan generation
- Warm-up routines
- Technique drilling schedules
- Live practice recommendations
- Focuses on techniques needing work
- Prioritizes optimal techniques for your body type

### 5. Practice Logging & Tracking
- **Dummy Practice**: Solo drilling on grappling dummy
- **Live Practice**: Sparring and positional work
- Quality ratings (1-5 scale)
- Session notes
- Video attachments (YouTube URLs)

### 6. Progress Analytics
- Mastery levels (Beginner → Learning → Competent → Proficient → Mastery)
- Practice statistics per technique
- Weekly training summaries
- Techniques needing practice alerts
- Belt progression percentage

### 7. YouTube Video Integration
All techniques include curated YouTube tutorial links from top instructors.

### 8. 🆕 Mobile Web Interface
Access the full app on your phone!
- **Mobile-optimized web interface** - responsive design for phones/tablets
- Touch-friendly navigation with bottom menu bar
- Log practice sessions on-the-go
- View daily practice plans with one tap
- Watch YouTube tutorials directly
- See competition statistics for each technique
- Dark mode design (easy on the eyes)
- Works on same WiFi network as your computer
- **See MOBILE_ACCESS.md for setup instructions**

## Installation

### CLI Version (No dependencies)

```bash
# Navigate to the directory
cd /home/user/jamesvonbrown/grappling_app

# Run the CLI app
python3 main.py
```

### Mobile Web Version (Requires Flask)

```bash
# Install Flask (one-time)
pip3 install Flask

# Start the web server
python3 web_app.py

# Access from your phone at http://YOUR_COMPUTER_IP:5000
# See MOBILE_ACCESS.md for detailed instructions
```

## Usage

### Quick Start

1. **Run the application**:
   ```bash
   python3 main.py
   ```

2. **View Today's Practice Plan** (Option 1):
   - Get personalized 60-minute practice session
   - Includes warm-up, drilling, and live practice
   - Watch YouTube videos for techniques
   - Practice on your BJJ dummy or with partner

3. **Log Your Practice** (Option 5):
   - After each session, log what you practiced
   - Rate your performance (1-5)
   - Add notes about what worked/didn't work

4. **Track Your Progress** (Options 4, 6, 7):
   - See belt progression percentage
   - View mastery levels for techniques
   - Check weekly training summary

### Main Menu Options

```
1.  View Today's Practice Plan - Personalized daily workout
2.  Browse Techniques - Explore by category
3.  View Optimal Techniques - See techniques perfect for your body
4.  View Belt Curriculum & Progress - Track belt advancement
5.  Log Practice Session - Record dummy or live training
6.  View Practice Statistics - See technique mastery levels
7.  View Weekly Training Summary - Training metrics
8.  Search Technique - Find specific technique
9.  View Technique Hierarchy - Full technique tree
10. View Wrestling-Specific Advantages - Wrestler game plan
11. View Techniques Needing Practice - What to work on
12. Generate Weekly Training Schedule - Full week plan
13. Export Training Report - Create markdown report
14. Backup Data - Save your progress
```

## Typical Weekly Workflow

### Monday - Guard Day
- Practice plan focuses on guard positions, sweeps, and guard submissions
- Dummy work: 30 min drilling DLR entries, X-guard sweeps
- Live work: 30 min positional sparring from guard

### Wednesday - Top Game Day
- Focus on passes, top control, submissions from top
- Dummy work: Pressure passing, front headlock attacks
- Live work: Passing drills, mount maintenance

### Friday - Takedowns & Wrestling
- Leverage your wrestling background
- Dummy work: Darce/Anaconda setups, shot entries
- Live work: Takedowns with guillotine defense

### Saturday - Legs & Back
- Leg locks, back attacks, turtle attacks
- Study leg lock defense (common wrestler weakness)
- Practice heel hooks safely (if brown/black belt)

## Data Storage

All data stored locally in `data/` directory:
- `user_profile.json` - Your profile and settings
- `practice_data.json` - All practice logs and statistics
- `progress.json` - Belt progress and learned techniques
- `backups/` - Automatic backups

## Key Techniques for Your Body Type

### Essential Guards (Long Legs Advantage)
- ⭐ De La Riva Guard - Long legs = superior control
- ⭐ X-Guard - Leg length dominates
- ⭐ Single Leg X - Entry to leg attacks
- ⭐ Spider Guard - Maximum distance control
- ⭐ Triangle Choke - Tighter with long legs

### Wrestling Transitions
- ⭐ Darce Choke - Natural from front headlock
- ⭐ Anaconda Choke - Wrestling position
- ⭐ Front Headlock to Back Take
- ⭐ Pressure Passing - Use wrestling base

### Important Adaptations for Wrestlers

**CRITICAL - Avoid Turtling!**
- In wrestling: turtle = defensive position
- In BJJ: turtle = gives up back and chokes
- **Solution**: Learn to go to guard instead

**Submission Defense**
- Biggest gap for wrestlers
- Focus heavily on recognizing submission threats
- Tap early and often in training

**Guard Development**
- Wrestlers often neglect guard (always want top)
- Your long legs make you naturally good at guard
- Embrace guard as an attacking position

**Gi Grip Fighting**
- Different from wrestling hand fighting
- Learn to use collar and sleeve grips
- Understand grip breaks

## Tips for Success

1. **Practice Dummy Work Daily** (even 10-15 minutes)
   - Build muscle memory
   - Perfect technique slowly
   - Watch videos while drilling

2. **Log Everything**
   - Helps identify what needs work
   - Tracks progression over time
   - Motivating to see improvement

3. **Focus on Optimal Techniques**
   - These are marked ⭐ in the database
   - Designed for your exact body type
   - Will develop faster than non-optimal techniques

4. **Use Wrestling Strengths**
   - Takedowns
   - Top pressure
   - Scrambling
   - Mental toughness

5. **Develop Wrestling Weaknesses**
   - Guard game
   - Submission defense
   - Patience and technical precision

6. **Watch the Videos**
   - All techniques include YouTube links
   - Watch before drilling
   - Watch again after practicing to refine

## Belt Progression Timeline (Approximate)

- **White → Blue**: 6-12 months (faster with wrestling)
- **Blue → Purple**: 1.5-3 years
- **Purple → Brown**: 2-4 years
- **Brown → Black**: 2-4+ years

Your wrestling background accelerates early progression but BJJ-specific skills (guard, submissions) take time to develop.

## Wrestler's Game Plan

### Phase 1 (White/Blue Belt)
- Adapt wrestling takedowns for BJJ
- Learn submission defense
- Develop basic guard game
- **STOP TURTLING**

### Phase 2 (Blue/Purple Belt)
- Build leg-based guard system
- Integrate front headlock submissions
- Develop well-rounded game
- Compete regularly

### Phase 3 (Purple+ Belt)
- Master leg entanglements
- Combine wrestling + BJJ seamlessly
- Develop signature style
- Become example of hybrid grappling

## Support

This is a standalone application with no external dependencies. All technique data, progression tracking, and practice logs are stored locally.

## License

Personal use application designed specifically for your training journey.

---

**Train hard, stay technical, and see you on the mats!** 🥋
