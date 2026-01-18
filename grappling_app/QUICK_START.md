# Quick Start Guide

## First Time Setup (30 seconds)

1. **Navigate to the app directory**:
   ```bash
   cd /home/user/jamesvonbrown/grappling_app
   ```

2. **Run the app**:
   ```bash
   python3 main.py
   ```

3. **You're ready to go!** No installation needed.

## Your First Session

### Step 1: Get Today's Practice Plan
- Select option **1** from the menu
- You'll get a complete 60-minute practice plan including:
  - Warm-up routine
  - 2-3 techniques to drill (with YouTube links!)
  - Live practice focus areas
- Write down the techniques or keep terminal open

### Step 2: Watch & Practice
- Click the YouTube links to watch instruction videos
- Practice on your BJJ dummy
- Focus on techniques marked as "OPTIMAL" for your body

### Step 3: Log Your Session
- After practice, select option **5**
- Enter technique name, duration, practice type
- Rate your performance 1-5
- Add any notes about what worked

## Daily Workflow (5 minutes)

```bash
# Morning: Check today's plan
python3 main.py
# Select option 1, note the techniques

# After practice: Log your session
python3 main.py
# Select option 5, log what you did

# Weekly: Review progress
python3 main.py
# Select option 7 for weekly summary
```

## Key Features to Explore

### View Optimal Techniques (Option 3)
See all 45+ techniques perfect for your body type:
- Long legs → DLR, X-Guard, Triangle chokes
- Wrestling background → Darce, Anaconda, Pressure passing

### Belt Curriculum (Option 4)
Track your progression toward next belt:
- See all required techniques
- Check what you've learned
- View progression percentage

### Wrestling Advantages (Option 10)
Your custom wrestler's game plan:
- Strengths to leverage
- Weaknesses to address
- Common mistakes to avoid

## Example Session

```
1. Run app, get today's plan:
   - Warm up: Shrimping, Granby rolls (10 min)
   - Drill: De La Riva Guard (15 min)
   - Drill: Triangle Choke (15 min)
   - Live: Guard retention practice (10 min)

2. Watch YouTube videos for DLR and Triangle

3. Practice on dummy for 40 minutes

4. Log session:
   - De La Riva Guard, dummy, 20 min, quality: 3/5
   - Triangle Choke, dummy, 20 min, quality: 4/5

5. Check stats to see progress!
```

## Pro Tips

**Dummy Training Every Day**
- Even 10-15 minutes helps
- Build muscle memory
- Perfect technique slowly

**Focus on Optimal Techniques**
- Marked with ⭐
- Work best for your body
- Faster progression

**Use Your Wrestling**
- Takedowns are your strength
- Front headlock game is natural
- But also develop guard!

**STOP Turtling**
- Critical BJJ adaptation
- Turtling gives up back
- Go to guard instead

## Common Questions

**Q: Do I need internet?**
A: Only to watch YouTube videos. The app runs offline.

**Q: Where is my data stored?**
A: In `grappling_app/data/` folder. Use option 14 to backup.

**Q: How do I change my belt level?**
A: Edit `data/user_profile.json` and change `"current_belt"` value.

**Q: Can I add custom techniques?**
A: Yes! When logging practice, you can enter any technique name.

**Q: What's the difference between dummy and live practice?**
A:
- Dummy = solo drilling on grappling dummy
- Live = sparring/rolling with partner

## Need Help?

- Read full README.md for detailed documentation
- All 56 techniques include YouTube tutorial links
- Practice logs help identify what needs work

---

**Now get on that dummy and start drilling!** 🥋
