# How it scores

Every number the app shows can be traced back to a line of code and a piece of
evidence. This document is that trace.

## The short version

```
score = 100 × (0.32·margin + 0.16·safety + 0.15·confidence
              + 0.15·condition + 0.11·velocity + 0.11·distance)
      − risk_penalty            (up to 45)
      + momentum_bonus          (up to 5)
```

Then five hard filters, any of which rejects the deal outright regardless of
score.

## The six signals

Each returns 0–1. Code: `server/flipscan/scoring/score.py`.

### margin (0.32) — how much money

Full marks at twice the profit bar and twice the ROI bar.

```
0.6 × min(1, net_profit / (2 × min_net_profit))
+ 0.4 × min(1, roi / (2 × min_roi_pct))
```

### safety (0.16) — how wrong can the comp be

Deliberately *not* the same as margin:

```
cushion = (resale_estimate − breakeven_sale) / resale_estimate
safety  = min(1, cushion / 0.40)
```

A $400 profit on a $2,000 item has a thin cushion — a 20% comp error wipes it
out. A $120 profit on a $200 item survives being badly wrong. Margin can't see
that difference; this can.

### confidence (0.15) — do we trust the estimate

Comes straight from the comps engine, built from sample size, how tightly the
comps agree, and how well their titles matched. Ten listings all saying $300 is
a number. Three saying $120, $300, and $700 is a guess wearing a number's
clothes.

### condition (0.15) — what shape is it in

`condition_score / 100`, then multiplied down for functional status:
`for_parts × 0.35`, `partial × 0.6`, `untested × 0.82`.

### velocity (0.11) — how fast does it turn

`exp(−(days − 7) / 60)`, floored at 0.08. A $200 margin on something that sits
for six months is worse than a $120 margin that turns in a week.

### distance (0.11) — how comfortably inside the radius

1.0 within a third of the worth-driving radius, sloping to 0.3 at the limit, 0
beyond it. Rewards deals that are comfortably worth the trip, not barely.

## The risk penalty (up to 45 points)

| Finding | Points |
|---|---|
| Scam signals in the text | up to 25 (scaled) |
| Possible counterfeit | 8 |
| Stock photos on a used listing | 6 |
| Sold for parts | 10 |
| Partially working | 6 |
| Untested | 3 |
| Each description red flag | 2 (cap 10) |
| Each missing part | 2 (cap 6) |
| Fewer than 3 comps | 5 |
| Location couldn't be resolved | 3 |

## The hard filters

Checked in order. Any one rejects the deal.

1. **Scam risk ≥ 70** — checked *first*, before any money test. No margin
   justifies driving to meet someone the listing itself says is a problem.
2. **Price outside `[min_buy_price, max_buy_price]`**
3. **Net profit below `min_net_profit`**
4. **Further away than the profit justifies** (below)
5. **ROI below the bar** — relaxed for high-value deals: a $900 profit at 30%
   is a very good day even though it fails the default 45% test
6. **Score below `min_deal_score`**

## How far is it worth driving

This is the piece the brief was most specific about, so it's worth explaining
properly. Code: `server/flipscan/scoring/radius.py`.

A tier table ("under $100 → 10 miles; over $1,000 → 50 miles") expresses the
idea but jumps at the boundaries and says nothing useful about the item that
lands between two tiers.

So instead the question is the one a business actually asks: **does this trip
pay for itself?**

```
per_mile   = (2 × cost_per_mile + 2/avg_speed × hourly_time_value) / batch_size
budget     = expected_profit × max_trip_cost_fraction
max_miles  = (budget − bulk_fixed_cost) / per_mile     clamped to [5, 60]
```

Two things make it match how reselling really works:

- **Batching.** Small items get bought several at a time, so one loop covers
  several pickups and the trip cost divides. That's why a $40 phone flip can
  justify a real drive while a $40 couch cannot.
- **Bulk surcharges.** A couch needs a truck and a friend. That's a fixed cost
  off the top before any distance is affordable.

With the defaults (35¢/mile, 32 mph, $25/hour, 25% of profit):

| Profit | Item | Worth driving |
|---|---|---|
| $2,000 | truck | 60 mi (the ceiling) |
| $900 | two-person | 60 mi |
| $500 | truck | 29 mi |
| $300 | two-person | 27 mi |
| $150 | box | 41 mi |
| $60 | box | 17 mi |
| $40 | box | 11 mi |
| **$60** | **truck** | **0 mi — not worth it at any distance** |

That last row is the model earning its keep. A $60 profit on something needing a
truck genuinely isn't worth doing, and a tier table would have said "10 miles."

## Pickup runs

Individually-scored deals each carry their own share of a trip cost. When
several cluster geographically, `scoring/routes.py` regroups them: adds those
per-item trip costs back, then charges **one** shared cost for the whole loop.

A run can therefore be worth driving even when none of its members clears the
bar alone. This is where the margin on small items actually comes from.

## What the price means

The resale estimate is a blend, weighted by both source quality and each
source's own confidence:

| Source | Weight | What it is |
|---|---|---|
| eBay sold | 2.4 | Somebody actually paid this |
| Your own history | 1.6 | The local market, small sample |
| eBay active | 1.0 | Asking prices, cut 22% |
| Web research | 1.0 | Claude with search, evidence required |
| Category prior | 0.35 | A guess with a category attached |

When sources **agree** (within 20%), confidence rises 15% — independent
agreement is real evidence. When they **disagree** (over 45% apart), confidence
drops 35% and the range widens to span both. Two sources 1.6× apart don't
average into a good estimate; they average into a confident wrong one.

### Condition adjusts the estimate

Comps are drawn from working, presentable examples, so anything below that gets
discounted: `A ×1.10, B ×1.00, C ×0.82, D ×0.58, F ×0.30`, floored further by
functional status. Undisclosed damage costs extra — if the photos contradict the
description, the rest of the listing is unreliable too.

### It calibrates against reality

Record what something actually sold for, and `comps/internal.calibration_factor`
compares predictions to outcomes per category. If furniture estimates have run
15% high across the last dozen sales, every future furniture estimate is
corrected by 0.85×. Needs 4 sales in a category before it acts, and is clamped
to ±35% — beyond that it's more likely a change in what she's buying than a
systematic bias.

## Fees

| Venue | Fee |
|---|---|
| Facebook local (cash) | 0% |
| Facebook shipping | 5% + $0.40 |
| eBay | 13.25% + $0.40 |
| Mercari | 10% + $0.50 |
| OfferUp shipping | 12.9% + $0.30 |
| Craigslist | 0% |

Plus shipping (~$12 small, ~$19.50 boxed), $3.50 of supplies, and a cleanup
allowance that scales with condition grade.

Venue is chosen automatically: bulky items are always local, and small valuable
items (≥$250, pocket-sized) go to eBay because the national price ceiling
usually more than covers the fee.
