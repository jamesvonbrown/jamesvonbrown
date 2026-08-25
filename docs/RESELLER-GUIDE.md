# Using it to actually make money

The software finds candidates. These are the things that decide whether a
candidate becomes profit, most of which no scanner can see.

## The first two weeks

Don't buy anything on the app's say-so yet.

Run it, look at what it surfaces, and **check its work**. Open the comps it
used. Ask whether the resale estimate matches what you'd have guessed. When it's
wrong, notice *how* it's wrong — consistently high on furniture, consistently
low on tools, whatever the pattern is.

Then start recording outcomes. Every time you buy something, hit **I bought it**
and enter what you paid. Every time you sell, record the sale price. After four
sales in a category the calibration kicks in and starts correcting that
category's estimates automatically.

The tool is worth substantially more in month three than in week one, and that
difference is entirely made of recorded outcomes.

## What actually flips well in Portland

The seeded watchlists reflect these. Adjust as you learn your market.

**Tools are the reliable bread and butter.** Brand-name cordless (DeWalt,
Milwaukee, Makita) barely depreciates, sells in days, and people liquidate it
constantly — job changes, divorces, estates. Check the batteries: a kit without
them is worth far less than the photo suggests, and batteries alone are a
respectable flip.

**Herman Miller Aerons are the single most reliable furniture flip.** Portland's
office churn keeps supply steady and demand is permanent. Size B is the common
one. Check the cylinder holds height and the mesh has no tears.

**Mid-century furniture is where the biggest spreads are.** People inherit teak
credenzas and list them for $75 because they're "old brown furniture." Look for
dovetailed drawers and a maker's stamp inside. Veneer over particleboard is not
worth the truck.

**Bikes move year-round here.** Frame size drives price more than components —
a 56cm sells in a week, a 48cm sits for two months. On e-bikes the battery is
the whole deal: a dead pack costs $400–800 and often can't be sourced at all.

**Outdoor gear punches above its weight.** Premium brands hold value hard, it
ships easily (which opens the national market), and Portland is saturated with
it. Buy snowboards in April, sell in November.

**Baby gear churns constantly.** Motivated sellers, fast turns. **Never resell
car seats** — expiry dates and recall liability make it a legal headache rather
than a flip.

**Be careful with appliances.** The spreads are large and so are the risks. Only
buy one you have personally watched run. "Worked when removed" means it doesn't
work.

## What the scanner can't see

**Whether the seller will actually respond.** Maybe a third won't. Message
early, message briefly.

**Whether it's already gone.** Good deals move in minutes. The hourly cadence is
a compromise; on a genuinely great find, message immediately rather than
finishing your coffee.

**Whether it smells.** Smoke is close to unsellable in furniture and textiles
and no photo shows it. Ask.

**Whether it fits in your car.** The app classifies bulk from the title, which
is a guess. Ask for dimensions before driving.

**Whether the seller is difficult.** Endless haggling, no-shows, and
last-minute changes are real costs. A "firm" price from a responsive seller is
often better than "obo" from someone who takes six hours to reply.

## Negotiating

The app surfaces motivation signals — "moving", "must go this weekend",
"already reduced" — because that's the most useful thing to know walking in.

- **Never lead with a lowball on a fresh listing.** A good listing at a good
  price gets ten messages in an hour; the one that reads like a serious buyer
  wins.
- **On anything listed more than a week, offer.** It hasn't sold at the asking
  price, and both of you know it.
- **Cash in hand, today, is worth 15%** to someone who is moving on Sunday.
  Say so plainly.
- **Bundle.** If they're clearing a garage, buy three things at a package price.
  This is also where trip batching pays off.

## Meeting people

Take the safety brief seriously. It scales with the situation, and it's not
boilerplate.

The rules that matter most: **daylight, public, someone knows where you are, and
test before money changes hands.** For furniture pickups at a house, bring
someone — every time, not just when it feels off. Ask them to bring the item to
the driveway rather than going inside.

Portland-area police departments run exchange zones. Call ahead to confirm the
location and hours; add the ones you confirm to `VERIFIED_EXCHANGE_ZONES` in
`server/flipscan/safety.py` and they'll show up in the app.

If something feels wrong, leave. There will be another chair.

## Pricing what you list

The app tells you what an item is worth; that's not the same as what to list it
at.

- **List 10–15% above** your target, so there's room to come down. Marketplace
  buyers expect to negotiate.
- **Photograph it properly.** Good light, clean background, every angle, and a
  close-up of any flaw. This is worth more than the price you pick.
- **Disclose flaws in the description.** A disclosed scratch costs a little; a
  discovered one costs the sale and your rating.
- **Renew rather than relist.** Relisting loses the listing's age and any saved
  interest.

## The numbers to watch

`GET /api/calibration` (or the CLI's `flipscan calibrate`) shows how your
estimates have tracked reality per category.

Also worth tracking yourself:

- **Sell-through rate.** What fraction of what you buy actually sells? Below
  80% and you're buying things you like rather than things that sell.
- **Days to sale.** Capital tied up in a garage isn't working. A 30% margin
  turning in a week beats a 60% margin turning in four months.
- **Profit per hour, including the driving.** This is the real number, and it's
  what the trip-cost model is there to protect.

## Scaling

Once it's working, the constraints become storage and time rather than finding
deals.

Raise the profit bar rather than the volume. Two $400 flips a week is a better
business than fifteen $40 ones — same money, a fraction of the driving,
messaging, and garage space.

Use the **Runs** tab. Batching is what makes small items viable at all, and
ignoring it is the most common way a reselling operation quietly loses money to
gas and hours.
