"""Command line — setup, one-off scans, and running the server."""

from __future__ import annotations

import asyncio
import logging
import secrets
from pathlib import Path

import typer

from .config import REPO_ROOT, get_settings

app = typer.Typer(
    add_completion=False,
    help="FlipScan — find resale deals near Portland and push them to your phone.",
)


def _setup_logging(level: str = "INFO") -> None:
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)-5s %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )


@app.command()
def init(
    force: bool = typer.Option(False, "--force", help="Overwrite an existing .env"),
) -> None:
    """Create .env with generated secrets, and set up the database."""
    env_path = REPO_ROOT / ".env"

    if env_path.exists() and not force:
        typer.secho(f"{env_path} already exists. Use --force to overwrite.",
                    fg=typer.colors.YELLOW)
        raise typer.Exit(1)

    api_token = secrets.token_urlsafe(32)
    # Long and random on purpose: on a public ntfy server the topic name is
    # the only thing standing between her alerts and anyone who guesses it.
    ntfy_topic = f"flipscan-{secrets.token_urlsafe(18)}"

    env_path.write_text(
        f"""# FlipScan configuration. Never commit this file.

# --- Required -------------------------------------------------------------
# Shared secret the phone sends to the API.
FLIPSCAN_API_TOKEN={api_token}

# Private ntfy topic for push notifications. Subscribe to this exact string
# in the ntfy iOS app (App Store: "ntfy"). Anyone who knows it can read your
# alerts, so don't share it or use a guessable name.
FLIPSCAN_NOTIFY__NTFY_TOPIC={ntfy_topic}

# --- Recommended ----------------------------------------------------------
# Photo condition analysis and web research. Without it the tool still runs,
# using text-only analysis. Get one at console.anthropic.com
# FLIPSCAN_ANTHROPIC_API_KEY=sk-ant-...

# eBay comps — free developer keys at developer.ebay.com. Strongly worth
# doing: real sold prices are the difference between a valuation and a guess.
# FLIPSCAN_SOURCES__EBAY_CLIENT_ID=
# FLIPSCAN_SOURCES__EBAY_CLIENT_SECRET=
# Set true only after eBay approves Marketplace Insights (real SOLD data).
# FLIPSCAN_SOURCES__EBAY_HAS_INSIGHTS_ACCESS=false

# --- Market ---------------------------------------------------------------
FLIPSCAN_MARKET__CENTER_LAT=45.5152
FLIPSCAN_MARKET__CENTER_LON=-122.6784
FLIPSCAN_MARKET__SEARCH_RADIUS_MILES=60

# --- Money ----------------------------------------------------------------
FLIPSCAN_PROFIT__MIN_NET_PROFIT=60
FLIPSCAN_PROFIT__MIN_ROI_PCT=45
FLIPSCAN_PROFIT__MAX_BUY_PRICE=2500

# --- Behaviour ------------------------------------------------------------
FLIPSCAN_SCAN__INTERVAL_MINUTES=60
FLIPSCAN_AI__DAILY_BUDGET_USD=3.00
# Start with 'demo' to try it without touching Facebook; switch to 'facebook'
# once you've run `flipscan login`.
FLIPSCAN_SOURCES__COLLECTORS=demo

# Public URL of this server, used for links inside notifications.
FLIPSCAN_PUBLIC_BASE_URL=http://localhost:8000
""",
        encoding="utf-8",
    )
    env_path.chmod(0o600)

    get_settings.cache_clear()
    from .db import init_db

    init_db()

    typer.secho(f"\n  Wrote {env_path}", fg=typer.colors.GREEN)
    typer.secho(f"  Database ready at {get_settings().database_url}\n", fg=typer.colors.GREEN)
    typer.echo("  Next steps:")
    typer.echo("    1. Install the 'ntfy' app on the iPhone (free, App Store)")
    typer.echo(f"    2. Subscribe to the topic:  {ntfy_topic}")
    typer.echo("    3. flipscan test-notify        # confirm the phone buzzes")
    typer.echo("    4. flipscan scan --demo        # try the whole pipeline")
    typer.echo("    5. flipscan serve              # start the app + scheduler\n")


@app.command()
def scan(
    demo: bool = typer.Option(False, "--demo", help="Use fixture listings, not Facebook"),
    notify: bool = typer.Option(True, "--notify/--no-notify"),
    reanalyze: bool = typer.Option(False, "--reanalyze", help="Re-score known listings"),
    log_level: str = typer.Option("INFO", "--log-level"),
) -> None:
    """Run one scan right now."""
    _setup_logging(log_level)
    from .collectors import DemoCollector
    from .db import init_db
    from .pipeline import run_scan

    init_db()
    settings = get_settings()
    collectors = [DemoCollector(settings)] if demo else None

    run = asyncio.run(
        run_scan(settings, trigger="cli", collectors=collectors,
                 notify=notify, force_reanalyze=reanalyze)
    )

    typer.echo("")
    typer.secho(f"  Listings seen   {run.listings_seen}", fg=typer.colors.CYAN)
    typer.secho(f"  New             {run.new_listings}", fg=typer.colors.CYAN)
    typer.secho(f"  Price changes   {run.price_changes}", fg=typer.colors.CYAN)
    typer.secho(f"  Photo-analyzed  {run.analyzed}", fg=typer.colors.CYAN)
    typer.secho(f"  Deals found     {run.deals_found}",
                fg=typer.colors.GREEN if run.deals_found else typer.colors.YELLOW)
    typer.secho(f"  Alerts sent     {run.alerts_sent}", fg=typer.colors.CYAN)
    typer.secho(f"  AI spend        ${run.ai_cost_usd:.4f}", fg=typer.colors.CYAN)
    if run.errors:
        typer.echo("")
        for error in run.errors[:10]:
            typer.secho(f"  ! {error}", fg=typer.colors.RED)


@app.command()
def login() -> None:
    """Open a browser to log into Facebook once. The session persists."""
    _setup_logging()
    settings = get_settings()

    typer.echo("\n  Opening a browser window.")
    typer.echo("  Log into Facebook, then close the window when you're done.\n")
    typer.secho(
        "  Use a SECONDARY Facebook account, not the one the business sells\n"
        "  from. Automating a logged-in session is against Meta's terms, and\n"
        "  the account that carries that risk should not be the one holding\n"
        "  your seller rating. See docs/LEGAL.md.\n",
        fg=typer.colors.YELLOW,
    )

    async def _login() -> None:
        try:
            from playwright.async_api import async_playwright
        except ImportError:
            typer.secho(
                "  Playwright isn't installed. Run:\n"
                "    pip install 'flipscan[browser]' && playwright install chromium",
                fg=typer.colors.RED,
            )
            raise typer.Exit(1) from None

        profile = Path(settings.sources.browser_profile_dir)
        profile.mkdir(parents=True, exist_ok=True)

        async with async_playwright() as pw:
            context = await pw.chromium.launch_persistent_context(
                user_data_dir=str(profile), headless=False,
                viewport={"width": 1280, "height": 900},
            )
            page = context.pages[0] if context.pages else await context.new_page()
            await page.goto("https://www.facebook.com/marketplace/")
            typer.echo("  Waiting for you to finish (close the window when done)...")
            try:
                await page.wait_for_event("close", timeout=600_000)
            except Exception:
                pass
            await context.close()

    asyncio.run(_login())
    typer.secho(f"\n  Session saved to {settings.sources.browser_profile_dir}",
                fg=typer.colors.GREEN)
    typer.echo("  Now set FLIPSCAN_SOURCES__COLLECTORS=facebook in .env\n")


@app.command("test-notify")
def test_notify() -> None:
    """Send a sample deal alert, to check the phone is set up."""
    _setup_logging()
    from .notify import DealAlert, broadcast, build_notifiers

    settings = get_settings()
    notifiers = build_notifiers(settings)
    if not notifiers:
        typer.secho(
            "  No notification channel is configured.\n"
            "  Set FLIPSCAN_NOTIFY__NTFY_TOPIC in .env (run `flipscan init`).",
            fg=typer.colors.RED,
        )
        raise typer.Exit(1)

    alert = DealAlert(
        deal_id=0,
        title="Herman Miller Aeron Chair Size B (test alert)",
        buy_price=180, net_profit=570, roi_pct=248, resale_estimate=800,
        distance_miles=12, deal_score=94, confidence=0.85,
        listing_url="https://www.facebook.com/marketplace/",
        app_url=f"{settings.public_base_url}/app/",
        location="Beaverton, OR", est_days_to_sell=9,
    )

    results = asyncio.run(broadcast(notifiers, alert))
    for result in results:
        if result.sent:
            typer.secho(f"  sent via {result.channel}", fg=typer.colors.GREEN)
        for error in result.errors:
            typer.secho(f"  {result.channel}: {error}", fg=typer.colors.RED)


@app.command("vapid-keys")
def vapid_keys() -> None:
    """Generate Web Push (VAPID) keys for the installed PWA."""
    try:
        import base64

        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.primitives.asymmetric import ec
    except ImportError:
        typer.secho("  pip install 'flipscan[push]' first", fg=typer.colors.RED)
        raise typer.Exit(1) from None

    private_key = ec.generate_private_key(ec.SECP256R1())

    private_der = private_key.private_bytes(
        encoding=serialization.Encoding.DER,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    public_point = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.X962,
        format=serialization.PublicFormat.UncompressedPoint,
    )

    b64 = lambda raw: base64.urlsafe_b64encode(raw).decode().rstrip("=")  # noqa: E731

    typer.echo("\n  Add these to .env:\n")
    typer.secho(f"FLIPSCAN_NOTIFY__VAPID_PRIVATE_KEY={b64(private_der)}", fg=typer.colors.CYAN)
    typer.secho(f"FLIPSCAN_NOTIFY__VAPID_PUBLIC_KEY={b64(public_point)}", fg=typer.colors.CYAN)
    typer.echo("\n  Then add 'webpush' to FLIPSCAN_NOTIFY__CHANNELS.\n")


@app.command()
def calibrate() -> None:
    """Show how well the resale estimates have matched real outcomes."""
    from .comps import calibration_factor
    from .db import init_db, session_scope

    init_db()
    with session_scope() as session:
        typer.echo("")
        factor, n, explanation = calibration_factor(session)
        typer.secho(f"  Overall: {explanation}", fg=typer.colors.CYAN)
        for category in ["tools", "furniture", "electronics", "bikes", "outdoor"]:
            factor, n, explanation = calibration_factor(session, category)
            if n:
                typer.echo(f"    {explanation}")
        typer.echo("")


@app.command()
def serve(
    host: str = typer.Option(None, "--host"),
    port: int = typer.Option(None, "--port"),
    no_scheduler: bool = typer.Option(False, "--no-scheduler"),
    reload: bool = typer.Option(False, "--reload"),
) -> None:
    """Run the API, the phone app, and the hourly scanner."""
    import uvicorn

    settings = get_settings()
    if no_scheduler:
        import os

        os.environ["FLIPSCAN_DISABLE_SCHEDULER"] = "1"

    uvicorn.run(
        "flipscan.main:app",
        host=host or settings.host,
        port=port or settings.port,
        reload=reload,
        log_level=settings.log_level.lower(),
    )


@app.command()
def status() -> None:
    """Recent scans, deal counts, and AI spend."""
    from sqlmodel import select

    from .db import init_db, session_scope
    from .models import ApiUsage, Deal, Listing, ScanRun

    init_db()
    with session_scope() as session:
        runs = session.exec(select(ScanRun).order_by(ScanRun.started_at.desc()).limit(8)).all()
        listings = len(session.exec(select(Listing)).all())
        deals = len(session.exec(select(Deal)).all())
        usage = session.exec(select(ApiUsage).order_by(ApiUsage.day.desc()).limit(5)).all()

        typer.echo(f"\n  {listings} listings tracked, {deals} deals found\n")
        typer.echo("  Recent scans:")
        for run in runs:
            mark = "ok " if run.ok else "ERR"
            typer.echo(
                f"    [{mark}] {run.started_at:%m-%d %H:%M}  "
                f"seen={run.listings_seen:<4} new={run.new_listings:<3} "
                f"deals={run.deals_found:<3} ${run.ai_cost_usd:.3f}"
            )
        if usage:
            typer.echo("\n  AI spend:")
            for row in usage:
                typer.echo(f"    {row.day}  ${row.cost_usd:.3f} over {row.calls} calls")
        typer.echo("")


if __name__ == "__main__":
    app()
