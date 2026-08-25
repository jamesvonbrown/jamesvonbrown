# Setup

About twenty minutes end to end, most of it waiting on eBay's developer signup.

## 1. Install

```bash
git clone <this repo> && cd jamesvonbrown
python3 -m venv .venv && source .venv/bin/activate
pip install -e .
```

For the Facebook collector, also:

```bash
pip install -e ".[browser]"
playwright install chromium
```

## 2. Initialise

```bash
flipscan init
```

Writes `.env` with a generated API token and a random private ntfy topic, and
creates the database with 18 starter watchlists tuned for Portland (tools,
mid-century furniture, bikes, outdoor gear, baby gear, and a couple of broad
sweeps that catch the mispriced-because-they-just-want-it-gone listings).

Note the ntfy topic it prints — you need it in the next step.

## 3. Notifications on the phone

1. Install **ntfy** from the App Store (free, no account).
2. Tap **+**, and subscribe to the exact topic string from step 2.
3. Back on the server:

```bash
flipscan test-notify
```

The phone should buzz within a second or two. If it doesn't, check the topic
matches exactly — it's case-sensitive.

> The topic name is the only secret protecting your alerts on the public ntfy
> server. Don't shorten it to something memorable.

## 4. Try it without touching Facebook

```bash
flipscan scan --demo --no-notify
flipscan serve
```

Open `http://localhost:8000/app/` on your computer. You should see three scored
deals from fixture listings, each with full profit maths, a condition read, and
a safety brief.

Paste the `FLIPSCAN_API_TOKEN` from `.env` when it asks.

## 5. Install it on the phone

The server has to be reachable from the phone. On the same wi-fi, find the
computer's local IP:

```bash
ipconfig getifaddr en0        # macOS
hostname -I | awk '{print $1}'  # Linux
```

Then on the phone, in **Safari** (not Chrome — only Safari can install a PWA on
iOS), open `http://192.168.1.x:8000/app/` and:

1. Paste the token
2. Tap **Share** → **Add to Home Screen**

It now has its own icon and opens full screen with no browser chrome.

For access from anywhere, see [DEPLOY.md](DEPLOY.md).

## 6. eBay comps — do this one

This is the single biggest accuracy improvement available, and it's free.
Without it, every resale estimate is a category average and the app says so on
each affected deal.

1. Sign up at [developer.ebay.com](https://developer.ebay.com) (free)
2. Create a **Production** keyset
3. Add to `.env`:
   ```
   FLIPSCAN_SOURCES__EBAY_CLIENT_ID=YourApp-PRD-xxxx
   FLIPSCAN_SOURCES__EBAY_CLIENT_SECRET=PRD-xxxx
   ```

That gets you active-listing comps, discounted 22% to approximate real sale
prices.

**For actual sold prices**, apply for the **Marketplace Insights API** in the
same portal. Approval takes a few days and is worth it — sold data is the
difference between "what sellers hope for" and "what buyers paid." Once
approved:

```
FLIPSCAN_SOURCES__EBAY_HAS_INSIGHTS_ACCESS=true
```

## 7. Photo analysis

```
FLIPSCAN_ANTHROPIC_API_KEY=sk-ant-...
```

From [console.anthropic.com](https://console.anthropic.com). This turns on
condition grading from the listing photos, damage the seller didn't mention,
stock-photo and counterfeit detection, and the per-item inspection checklist.

Expect **$0.30–0.80/day** — the pipeline only spends on listings that survive
the free filters. `FLIPSCAN_AI__DAILY_BUDGET_USD` is a hard cap; past it, deals
are still found and scored, just graded from text alone.

## 8. Facebook

**Read [LEGAL.md](LEGAL.md) first.** Short version: this violates Meta's terms,
and you should point it at a secondary account, not the one the business sells
from.

```bash
flipscan login          # opens a browser; log in, then close the window
```

Then in `.env`:

```
FLIPSCAN_SOURCES__COLLECTORS=facebook
```

The session persists in `data/browser-profile/`. Re-run `flipscan login` if
scans start coming back empty — that usually means the session logged out.

## 9. Run it

```bash
flipscan serve
```

Scans hourly with randomised jitter. Check on it with:

```bash
flipscan status
```

For something permanent, see [DEPLOY.md](DEPLOY.md).

---

## Tuning

Everything is adjustable from the phone's Settings tab. The ones that matter:

| Setting | Default | What it does |
|---|---|---|
| Minimum profit | $60 | Won't alert below this after all costs |
| Minimum return | 45% | Return on cash actually at risk |
| Most I'll spend | $2,500 | Hard ceiling per item |
| Furthest I'll drive | 60 mi | Hard ceiling; the per-deal radius scales with profit |
| Share of profit spent driving | 0.25 | Raise to travel further for the same money |
| Your time per hour | $25 | Feeds the trip-cost maths |
| Quality bar | 55/100 | Catches deals that add up but look risky |

**Getting too many alerts?** Raise the minimum profit — it's the bluntest and
most effective lever.

**Getting none?** Lower it to $40, widen the categories in Settings →
Watchlists, and check `flipscan status` for warnings.

---

## Troubleshooting

**"Scans run but find nothing"** — usually the Facebook session logged out. Run
`flipscan login`. If the session is fine, Facebook may have changed its markup:
check `data/debug/` for saved unparseable pages.

**"Every deal says unverified"** — no eBay keys. See step 6.

**"Nothing arrives on the phone"** — `flipscan test-notify`. If that works but
scans are quiet, everything is being filtered out; lower the profit bar.

**"The app won't install to the Home Screen"** — must be Safari, and the page
must fully load first.

**"Distances look wrong"** — the geocoder resolves Portland-area place names
locally. Unrecognised places fall back to the market centre and are flagged
low-confidence. Add yours to `PORTLAND_PLACES` in `server/flipscan/geo.py`.
