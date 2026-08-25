# FlipScan

A resale deal scanner for Facebook Marketplace, built for one reseller working
the Portland metro.

Every hour it looks at what's newly listed, works out what each item actually
resells for, grades its condition from the photos, subtracts every real cost —
platform fees, gas, an hour of your life — and pushes the handful worth getting
in the car for.

> **Also in this repo:** `rpg_game.py`, an unrelated text adventure from an
> earlier session. Its docs are at [docs/rpg-game.md](docs/rpg-game.md).

---

## Start here

```bash
pip install -e .
flipscan init            # writes .env with generated secrets, sets up the DB
flipscan scan --demo     # runs the whole pipeline on fixture listings
flipscan serve           # API + phone app + hourly scanner
```

Open `http://localhost:8000/app/` on your phone, paste the token from `.env`,
and in Safari tap **Share → Add to Home Screen**. It gets its own icon and
opens full screen like a normal app.

Full walkthrough: **[docs/SETUP.md](docs/SETUP.md)**.

---

## What it actually does

**Finds listings.** Hourly, across the searches you care about, at a human pace
with hard per-scan ceilings.

**Works out what it's worth.** Blends eBay sold comps, your own past outcomes,
and — for odd items the APIs can't price — a web-research pass. Sources that
disagree widen the range and lower the confidence rather than averaging into a
confident wrong answer.

**Looks at the photos.** Claude grades condition A–F, identifies the specific
model, spots damage the seller didn't mention, flags stock photos and likely
counterfeits, and writes a per-item checklist of things to verify in person.

**Does the real arithmetic.** Fees, shipping, cleanup, and the cost of the
drive all come off before anything is called a profit.

**Decides whether it's worth the trip.** The radius scales with the money: a
$2,000 spread earns the full 60 miles, a $40 flip stays inside 11, and a
low-margin couch that needs a truck correctly comes back as *not worth it at
any distance*.

**Groups pickups into runs.** Several deals clustered together become one
drive, with the trip cost charged once instead of per item — which is where the
margin on small items actually comes from.

**Tells you how to stay safe.** Every deal carries a meetup brief sized to the
situation, because the app's whole job is sending someone to meet a stranger
with cash.

**Learns.** Record what you paid and what it sold for, and the estimates
recalibrate per category.

---

## What it looks like

The feed leads with profit, because that's the only number that decides whether
you open it:

```
  $511   74% ROI     Trek Domane SL5 56cm carbon road bike
  buy $650 → sells $1,203      [74] [B] [8.4 mi] [~18d to sell]
```

Tap through and every number is itemised and traceable — the comps it used, the
photos it graded, and why it scored what it did.

---

## Cost

Running Claude over every listing an hourly scan turns up would cost about
**$70/day**, which is absurd for a business built on margin. So the pipeline is
staged, and each stage is more expensive and sees far fewer listings:

| Stage | Cost | Listings |
|---|---|---|
| Collect | free | ~400 |
| Dedupe + text screen | free | ~400 → ~60 |
| Comps lookup | free | ~60 → ~15 |
| Photo analysis (Claude) | paid | ~15 |
| Score + notify | free | the ones worth alerting |

A listing that can't clear the profit bar even under generous assumptions is
dropped for nothing and never costs a model call. Real-world spend lands around
**$0.30–0.80/day**, with a hard daily cap you set.

---

## Layout

```
server/flipscan/
  collectors/   listing sources (Facebook, manual paste, demo fixtures)
  comps/        valuation: eBay, own history, web research, category priors
  enrich/       photo grading + description mining
  scoring/      fees, trip economics, the deal score, pickup runs
  notify/       ntfy, web push, APNs, SMS
  api/          REST API for the phone
  pipeline.py   the staged hourly scan
web/            installable PWA — no build step
ios/            SwiftUI app (written, never compiled — see ios/README.md)
docs/           setup, deployment, scoring maths, legal reality, playbook
```

---

## Documentation

| | |
|---|---|
| [SETUP.md](docs/SETUP.md) | Get it running, phone included |
| [HOW-IT-SCORES.md](docs/HOW-IT-SCORES.md) | The maths, in full |
| [LEGAL.md](docs/LEGAL.md) | **Read before scanning Facebook.** Honest risks |
| [DEPLOY.md](docs/DEPLOY.md) | Running it somewhere permanent |
| [RESELLER-GUIDE.md](docs/RESELLER-GUIDE.md) | Using it to actually make money |

---

## Honest status

**Working and tested:** the whole server pipeline, valuation, scoring, trip
economics, notifications, REST API, and the PWA. 159 tests pass.

**Written but never compiled:** the SwiftUI app. There's no Swift toolchain on
Linux, where this was built. Use the PWA today; the native app is ready for the
day there's a Mac.

**Needs your attention:** the Facebook collector depends on scraping a site
with no public API, which is against Meta's Terms of Service and carries real
account risk. [docs/LEGAL.md](docs/LEGAL.md) covers what that means and how to
limit the damage. The demo and manual collectors need none of it.

**Only as good as its comps:** without eBay keys, resale values are category
averages, and the app says so on every affected deal. The keys are free and
take about ten minutes.
