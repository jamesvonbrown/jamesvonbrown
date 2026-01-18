# Mobile Access Guide

Access your BJJ Grappling App on your phone through a web interface!

## Quick Setup (5 minutes)

### Step 1: Install Flask (one-time setup)

```bash
cd /home/user/jamesvonbrown/grappling_app

# Install Flask
pip3 install -r requirements.txt

# Or install directly
pip3 install Flask
```

### Step 2: Find Your Computer's IP Address

**On Linux/Mac:**
```bash
hostname -I
# or
ifconfig | grep "inet "
```

**On Windows:**
```bash
ipconfig
```

Look for your local IP (usually starts with `192.168.` or `10.`)
Example: `192.168.1.100`

### Step 3: Start the Web Server

```bash
cd /home/user/jamesvonbrown/grappling_app
python3 web_app.py
```

You'll see output like:
```
====================================
BJJ GRAPPLING APP - MOBILE WEB INTERFACE
====================================

📱 Starting web server...

Access from your phone:
  1. Make sure phone and computer are on same WiFi
  2. Open browser on phone
  3. Go to: http://<YOUR_COMPUTER_IP>:5000

Access from this computer:
  http://localhost:5000

====================================
```

### Step 4: Access on Your Phone

1. **Make sure your phone and computer are on the same WiFi network**
2. Open a web browser on your phone (Chrome, Safari, Firefox, etc.)
3. Go to: `http://YOUR_COMPUTER_IP:5000`
   - Example: `http://192.168.1.100:5000`
4. Bookmark it for easy access!

## Features on Mobile Web

### Home Screen
- Weekly training summary
- Quick links to all features
- Your profile info (height, wingspan, belt)

### Today's Practice
- Full daily practice plan
- Click YouTube links to watch tutorials
- Mark techniques as you complete them

### Techniques Browser
- Browse all 56+ techniques
- Filter by category
- View optimal techniques for your build
- ⭐ **NEW**: See success rates and finish rates from competition data!

### Technique Details
- Full technique breakdown
- Key details and tips
- YouTube tutorial links
- **Competition statistics** with success/finish rates
- Your personal practice stats
- Mastery level tracking

### Log Practice
- Quick practice logging
- Dummy or live practice tracking
- Quality ratings (1-5)
- Notes for each session
- Quick-add buttons for common techniques

### Statistics Dashboard
- Weekly summary
- Recent training sessions
- Mastery levels for all techniques
- Total practice time breakdown

### Wrestling Advantages
- Your specific wrestling strengths
- BJJ adaptations needed
- Common wrestler mistakes to avoid
- Ideal game plan

### Curriculum & Progress
- Belt requirements
- Essential techniques
- Progress tracking
- Wrestler-specific goals

## Mobile-Optimized Design

- **Responsive layout** - works on any screen size
- **Touch-friendly** - large buttons and tap targets
- **Fast loading** - lightweight, no external dependencies
- **Works offline** - once loaded (YouTube links need internet)
- **Dark mode** - easy on the eyes
- **Bottom navigation** - easy thumb access

## Troubleshooting

### "Can't connect" or "Site can't be reached"

1. **Check WiFi**: Phone and computer must be on same network
2. **Check IP**: Make sure you're using the correct computer IP
3. **Check port**: The URL should end with `:5000`
4. **Firewall**: Your firewall might be blocking port 5000

**To allow through firewall (Linux):**
```bash
sudo ufw allow 5000
```

**To allow through firewall (Windows):**
- Search "Windows Defender Firewall"
- "Advanced settings"
- "Inbound Rules" → "New Rule"
- Port → TCP → 5000 → Allow

### "Connection refused" or "Port already in use"

Another app is using port 5000. Kill it or use a different port:

```bash
# Find what's using port 5000
lsof -i :5000

# Kill it
kill -9 <PID>

# Or run on different port
# Edit web_app.py, change line:
# app.run(host='0.0.0.0', port=5001, debug=True)
```

### Page loads but looks broken

Try clearing your phone's browser cache:
- iPhone Safari: Settings → Safari → Clear History and Website Data
- Android Chrome: Settings → Privacy → Clear browsing data

## Using on Tablet

Same instructions work for iPad, Android tablets, etc.!

## Desktop/Laptop Access

If you're on the same computer, just go to:
```
http://localhost:5000
```

## Advanced: Keep Server Running

To keep the server running even after you close the terminal:

```bash
nohup python3 web_app.py > web_app.log 2>&1 &
```

To stop it:
```bash
pkill -f web_app.py
```

## Alternative: Using CLI App

If you prefer the command-line interface:
```bash
python3 main.py
```

Both apps share the same data, so you can use both!

## Data Sync

All practice logs, stats, and progress are saved to:
- `/home/user/jamesvonbrown/grappling_app/data/`

Both the CLI and web app read/write to the same files, so your data is always in sync.

## Features Unique to Web Version

- ✅ Easier navigation on phone
- ✅ Touch-optimized interface
- ✅ Better for quick logging after training
- ✅ Easier to watch YouTube videos
- ✅ **Competition statistics visible on every technique**
- ✅ Better visualization of progress bars
- ✅ Mobile-friendly forms

## Features Unique to CLI Version

- ✅ Works without network
- ✅ Weekly schedule generator
- ✅ Export training reports
- ✅ Backup system
- ✅ More detailed curriculum views

---

**Pro Tip**: Start the web server before you go to training, then log your practice on your phone right after you finish!

**Battery Saver**: The web server uses very little resources. You can leave it running all day.

**Privacy**: Everything runs locally on your computer. No data leaves your network.
