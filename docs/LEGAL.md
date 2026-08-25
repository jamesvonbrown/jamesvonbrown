# Read this before you point it at Facebook

This is the part that matters most, so it goes first and it goes plainly.

## Facebook Marketplace has no public API

There is no sanctioned, supported way for a program to read Marketplace
listings. Meta shut down the last public paths years ago and has not replaced
them. So the collector in `server/flipscan/collectors/facebook.py` does the only
thing that works: it drives a real Chromium browser, logged into a real account,
and reads the pages that account can already see.

**That is against Meta's Terms of Service.** Section 3.2.3 of the Terms of
Service prohibits accessing or collecting data from their products using
automated means without prior permission. There is no reading of this where
running an automated scraper against a logged-in session is permitted.

## What can actually happen

In rough order of likelihood:

1. **Nothing, for a long time.** One account making a few dozen page loads an
   hour looks a lot like a person who checks Marketplace obsessively — because
   it is basically indistinguishable from that.
2. **Checkpoints.** Facebook asks the account to re-verify. Scanning stops until
   someone logs in again. Annoying, recoverable.
3. **Rate limiting.** Searches start returning nothing. The scan logs an error
   and keeps going.
4. **Account restriction or ban.** The account loses Marketplace access, or is
   disabled entirely. **This is the one that matters**, and it is why the next
   section exists.

Meta does not litigate against individuals doing personal-scale scraping. The
lawsuits you can find are against companies harvesting data at scale and
reselling it. That is a genuinely different activity from one person watching
her own local market — but "they probably won't sue you" is not the same as
"this is allowed," and you should not confuse the two.

## Use a separate account. Not the selling account.

This is the single most important line in this document.

Her reselling business will live on her Marketplace seller rating, her
reviews, and her account history. Those take months to build and cannot be
recovered if the account is disabled.

**Make a second Facebook account for scanning.** Log the scanner into that one.
If it gets restricted, you have lost a throwaway, not the business.

Bear in mind that Facebook's own terms also prohibit maintaining more than one
personal account. There is no configuration of this tool that is simultaneously
useful and fully compliant with Meta's terms. That is the actual trade being
made here, and it should be made deliberately rather than discovered later.

## What this tool does to stay small

These aren't decorative. They're in `ScanSettings` and enforced in the
collector:

| Limit | Default | Why |
|---|---|---|
| `interval_minutes` | 60 | Hourly. Not continuous. |
| `jitter_seconds` | up to 420 | Never fires at exactly :00 — predictable timing is a bot signature |
| `max_searches_per_scan` | 25 | Bounded work per pass |
| `max_listings_per_scan` | 400 | Bounded results per pass |
| `max_detail_fetches_per_scan` | 60 | Detail pages are the expensive request |
| `delay_between_actions` | 1.8–4.5s, randomised | Human-paced |

It also fetches only listings that are public to the logged-in account, in one
metro, in categories she has explicitly asked for. It does not touch profiles,
messages, friend lists, groups, or anything about other people beyond the seller
name attached to a public listing. It stores no personal data beyond what a
listing shows.

**Do not raise these limits.** The ceilings are what keeps this a personal
shopping assistant rather than a harvesting operation, and the difference
between those two things is the difference between a mild terms violation and
the thing that actually gets people sued.

## Ways to avoid the risk entirely

Every one of these is fully supported:

- **`FLIPSCAN_SOURCES__COLLECTORS=demo`** — the whole pipeline on fixtures. Good
  for trying it and for development.
- **Manual entry** — paste a link or type an item into the app's *Check* tab and
  get the full valuation, condition read, and profit maths with no scraping at
  all. Genuinely useful standing in front of something at an estate sale.
- **Other sources** — the collector interface is one class. Craigslist has RSS.
  eBay has a real API. Both are far friendlier ground, and neither requires any
  of the above.

The valuation engine, the scoring, the trip economics, the safety briefs, and
the app are all completely independent of where listings come from. Facebook is
one collector, not the foundation.

## Other things worth knowing

**eBay's API is fine.** It's a real, documented, sanctioned API. Get the free
developer keys; using them is exactly what they're for.

**Photos.** Listing images are downloaded to grade condition and cached
locally. They are the seller's photographs. Keep them local, don't republish
them. Cached images live in `data/media/` and can be deleted at any time.

**Claude API.** Listing text and photos are sent to Anthropic's API for
analysis, subject to their usage policies. No personal data beyond the public
listing content is sent.

**Consumer law.** Reselling secondhand goods is legal and ordinary. Two
exceptions worth knowing: **recalled items** (check CPSC before listing) and
**car seats** (expiry dates and liability make them a bad idea — the seeded
watchlists say so).

**Taxes.** Reselling for profit is income. In the US, payment processors report
above certain thresholds. Oregon has no sales tax, which simplifies things, but
income is still income. Talk to an accountant once this is making real money.

## The short version

Using this against Facebook violates Meta's terms. The practical risk is losing
the account you point it at. Point it at an account you can afford to lose, keep
the limits where they are, and the tool works fine. If that trade isn't
acceptable, the demo and manual paths give you most of the value with none of
the exposure.
