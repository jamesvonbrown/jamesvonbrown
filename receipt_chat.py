#!/usr/bin/env python3
"""Receipt Chat: a conversational CLI for logging and querying expenses from receipts.

Log expenses by hand, or paste in receipt text (e.g. from a photo you've
transcribed or run through OCR) and let it pull out the vendor, date,
category, and amount automatically. No external dependencies required.
"""

import argparse
import json
import os
import re
from dataclasses import asdict, dataclass
from datetime import datetime

DEFAULT_STORE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "expenses.json")
SAMPLE_RECEIPT_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "examples", "sample_gas_receipt.txt"
)

CATEGORY_KEYWORDS = {
    "Fuel": ["pump#", "unlead", "unleaded", "diesel", "fuel total", "price/gal"],
    "Groceries": ["grocery", "market", "safeway", "kroger", "trader joe", "whole foods"],
    "Dining": ["restaurant", "cafe", "diner", "grill", "pizza", "coffee", "bar & grill"],
    "Pharmacy": ["pharmacy", "walgreens", "cvs", "rite aid"],
    "Home & Garden": ["hardware", "ace hardware", "home depot", "lowe's", "lowes", "garden center"],
}

CATEGORY_ALIASES = {
    "fuel": "Fuel", "gas": "Fuel", "gasoline": "Fuel", "petrol": "Fuel",
    "groceries": "Groceries", "grocery": "Groceries",
    "dining": "Dining", "restaurant": "Dining", "restaurants": "Dining", "food": "Dining",
    "pharmacy": "Pharmacy", "meds": "Pharmacy", "medicine": "Pharmacy",
    "hardware": "Home & Garden", "home": "Home & Garden", "garden": "Home & Garden",
}

# Boilerplate lines to ignore when guessing the vendor from the top of a receipt.
VENDOR_BOILERPLATE_PREFIXES = ("thank you", "welcome to")

DATE_RE = re.compile(r"\b(\d{1,2})/(\d{1,2})/(\d{2}|\d{4})\b")
TIME_RE = re.compile(r"\b(\d{1,2}:\d{2}(?::\d{2})?\s*[AP]M)\b", re.IGNORECASE)
FUEL_TOTAL_RE = re.compile(r"FUEL\s+TOTAL\s*:?\s*\$?\s*([\d,]+\.\d{2})", re.IGNORECASE)
# Anchored to the start of a line so it doesn't match "SUB-TOTAL" (which also
# satisfies a bare \bTOTAL\b search, since '-' counts as a word boundary).
GENERIC_TOTAL_RE = re.compile(r"^\s*TOTAL\s*:?\s*\$?\s*([\d,]+\.\d{2})", re.IGNORECASE | re.MULTILINE)
GALLONS_RE = re.compile(r"([\d.]+)\s*G(?:AL)?\b", re.IGNORECASE)
PRICE_PER_GAL_RE = re.compile(r"PRICE/GAL\s*\$?\s*([\d.]+)", re.IGNORECASE)
PUMP_RE = re.compile(r"PUMP#\s*(\d+)", re.IGNORECASE)

HELP_TEXT = """\
Receipt Chat -- commands:
  add                     Add an expense by answering a few prompts
  paste                   Paste raw receipt text (type '.' on its own line when done);
                           vendor/date/category/amount are pulled out for you
  list [filters]          List expenses. Filters: category:<name> vendor:<text>
                           month:<YYYY-MM> year:<YYYY> date:<YYYY-MM-DD>
  total [filters]         Show total spent, with the same filters as `list`
  delete <id>             Delete an expense by id
  help                    Show this message
  exit / quit             Leave the chat

You can also just ask things like:
  "how much did I spend on fuel this month"
  "show my dining expenses"
"""


@dataclass
class Expense:
    id: int
    date: str
    time: str
    vendor: str
    category: str
    amount: float
    description: str = ""
    raw_text: str = ""

    def to_dict(self):
        return asdict(self)


class ExpenseStore:
    def __init__(self, path=DEFAULT_STORE_PATH):
        self.path = path
        self.expenses = []
        self._load()

    def _load(self):
        if os.path.exists(self.path):
            with open(self.path, "r") as f:
                data = json.load(f)
            self.expenses = [Expense(**item) for item in data]
        else:
            self.expenses = []

    def save(self):
        with open(self.path, "w") as f:
            json.dump([e.to_dict() for e in self.expenses], f, indent=2)

    def next_id(self):
        return max((e.id for e in self.expenses), default=0) + 1

    def add(self, **kwargs):
        expense = Expense(id=self.next_id(), **kwargs)
        self.expenses.append(expense)
        self.save()
        return expense

    def delete(self, expense_id):
        before = len(self.expenses)
        self.expenses = [e for e in self.expenses if e.id != expense_id]
        changed = len(self.expenses) != before
        if changed:
            self.save()
        return changed

    def filter(self, category=None, vendor=None, month=None, year=None, date=None):
        results = self.expenses
        if category:
            results = [e for e in results if e.category.lower() == category.lower()]
        if vendor:
            results = [e for e in results if vendor.lower() in e.vendor.lower()]
        if month:
            results = [e for e in results if e.date.startswith(month)]
        if year:
            results = [e for e in results if e.date.startswith(str(year))]
        if date:
            results = [e for e in results if e.date == date]
        return results

    def total(self, **filters):
        return sum(e.amount for e in self.filter(**filters))


def categorize(text):
    lowered = text.lower()
    for category, keywords in CATEGORY_KEYWORDS.items():
        if any(kw in lowered for kw in keywords):
            return category
    return "Other"


def parse_receipt_text(text):
    """Pull vendor/date/category/amount out of raw receipt text (e.g. an OCR dump)."""
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    if not lines:
        raise ValueError("Empty receipt text")

    date_match = DATE_RE.search(text)
    time_match = TIME_RE.search(text)
    date = ""
    if date_match:
        mm, dd, yyyy = date_match.groups()
        year = int(yyyy)
        if year < 100:  # 2-digit year, e.g. "08/22/26"
            year += 2000
        date = f"{year:04d}-{int(mm):02d}-{int(dd):02d}"
    time_str = time_match.group(1).upper() if time_match else ""

    vendor_lines = []
    for line in lines:
        if DATE_RE.search(line) or TIME_RE.search(line):
            break
        if line.isdigit():
            continue  # skip bare store numbers / zip codes
        if line.lower().startswith(VENDOR_BOILERPLATE_PREFIXES):
            continue  # skip greeting lines like "Thank you for shopping at"
        if "$" in line:
            break  # reached line items / totals, which come after the header
        vendor_lines.append(line)
    vendor = ", ".join(vendor_lines[:3]) if vendor_lines else lines[0]

    category = categorize(text)

    amount = None
    fuel_match = FUEL_TOTAL_RE.search(text)
    if fuel_match:
        amount = float(fuel_match.group(1).replace(",", ""))
    else:
        total_match = GENERIC_TOTAL_RE.search(text)
        if total_match:
            amount = float(total_match.group(1).replace(",", ""))
    if amount is None:
        raise ValueError("Could not find a total amount on the receipt")

    details = []
    gallons_match = GALLONS_RE.search(text)
    price_gal_match = PRICE_PER_GAL_RE.search(text)
    pump_match = PUMP_RE.search(text)
    if gallons_match:
        details.append(f"{gallons_match.group(1)} gal")
    if price_gal_match:
        details.append(f"${price_gal_match.group(1)}/gal")
    if pump_match:
        details.append(f"Pump #{pump_match.group(1)}")

    return {
        "date": date or datetime.now().strftime("%Y-%m-%d"),
        "time": time_str,
        "vendor": vendor,
        "category": category,
        "amount": amount,
        "description": ", ".join(details),
        "raw_text": text,
    }


def parse_filters(args_str):
    filters = {}
    for token in args_str.split():
        if ":" in token:
            key, _, value = token.partition(":")
            key = key.lower()
            if key in ("category", "vendor", "month", "year", "date"):
                filters[key] = value
    return filters


def describe_filters(filters):
    parts = []
    if "category" in filters:
        parts.append(filters["category"])
    if "vendor" in filters:
        parts.append(f"at {filters['vendor']}")
    if "month" in filters:
        parts.append(f"in {filters['month']}")
    if "year" in filters:
        parts.append(f"in {filters['year']}")
    if "date" in filters:
        parts.append(f"on {filters['date']}")
    return " ".join(parts)


def guess_filters_from_text(text):
    lowered = text.lower()
    filters = {}
    for alias, category in CATEGORY_ALIASES.items():
        if alias in lowered:
            filters["category"] = category
            break
    now = datetime.now()
    if "today" in lowered:
        filters["date"] = now.strftime("%Y-%m-%d")
    elif "this month" in lowered:
        filters["month"] = now.strftime("%Y-%m")
    elif "this year" in lowered:
        filters["year"] = str(now.year)
    return filters


def format_expense_line(e):
    return f"#{e.id:<3} {e.date} {e.category:<10} ${e.amount:>8.2f}  {e.vendor}"


def handle_list(store, line):
    _, _, rest = line.partition(" ")
    filters = parse_filters(rest)
    results = sorted(store.filter(**filters), key=lambda e: e.date)
    if not results:
        return "No expenses found."
    header = f"{'ID':<4}{'Date':<11}{'Category':<11}{'Amount':>10}  Vendor"
    lines = [header] + [format_expense_line(e) for e in results]
    lines.append(f"\n{len(results)} expense(s), total ${sum(e.amount for e in results):.2f}")
    return "\n".join(lines)


def handle_total(store, line):
    _, _, rest = line.partition(" ")
    filters = parse_filters(rest)
    results = store.filter(**filters)
    total = sum(e.amount for e in results)
    label = describe_filters(filters) or "all expenses"
    breakdown = {}
    for e in results:
        breakdown[e.category] = breakdown.get(e.category, 0) + e.amount
    lines = [f"Total for {label}: ${total:.2f} ({len(results)} expense(s))"]
    for cat, amt in sorted(breakdown.items(), key=lambda kv: -kv[1]):
        lines.append(f"  {cat:<12} ${amt:.2f}")
    return "\n".join(lines)


def handle_delete(store, line):
    parts = line.split(maxsplit=1)
    if len(parts) < 2 or not parts[1].strip().isdigit():
        return "Usage: delete <id>"
    expense_id = int(parts[1].strip())
    if store.delete(expense_id):
        return f"Deleted expense #{expense_id}."
    return f"No expense with id {expense_id}."


def handle_freeform(store, line):
    filters = guess_filters_from_text(line)
    filter_str = " ".join(f"{k}:{v}" for k, v in filters.items())
    lowered = line.lower()
    if any(word in lowered for word in ("how much", "total", "spend", "spent")):
        return handle_total(store, "total " + filter_str)
    if any(word in lowered for word in ("show", "list")):
        return handle_list(store, "list " + filter_str)
    return (
        "I didn't understand that. Type 'help' to see available commands, "
        "or try something like 'how much did I spend on fuel this month'."
    )


def add_expense_interactive(store):
    print("Let's log a new expense.")
    vendor = input("Vendor/location: ").strip()
    date = input("Date (YYYY-MM-DD) [today]: ").strip() or datetime.now().strftime("%Y-%m-%d")
    category = input(f"Category [{'/'.join(CATEGORY_KEYWORDS)}/Other]: ").strip() or "Other"
    amount_str = input("Amount ($): ").strip()
    try:
        amount = float(amount_str)
    except ValueError:
        print("Amount must be a number. Cancelled.")
        return
    description = input("Description (optional): ").strip()
    expense = store.add(
        date=date, time="", vendor=vendor, category=category,
        amount=amount, description=description, raw_text="",
    )
    print(f"Logged #{expense.id}: {expense.vendor} -- ${expense.amount:.2f} ({expense.category})")


def paste_receipt_interactive(store):
    print("Paste the receipt text below. Type '.' on its own line when done.")
    lines = []
    while True:
        line = input()
        if line.strip() == ".":
            break
        lines.append(line)
    text = "\n".join(lines)
    if not text.strip():
        print("No text received. Cancelled.")
        return
    try:
        parsed = parse_receipt_text(text)
    except ValueError as e:
        print(f"Couldn't parse that receipt: {e}")
        return
    print(f"Parsed: {parsed['vendor']} on {parsed['date']} -- ${parsed['amount']:.2f} ({parsed['category']})")
    if parsed["description"]:
        print(f"Details: {parsed['description']}")
    confirm = input("Save this expense? [Y/n]: ").strip().lower()
    if confirm in ("", "y", "yes"):
        expense = store.add(**parsed)
        print(f"Saved as expense #{expense.id}.")
    else:
        print("Discarded.")


def run_chat(store):
    print(HELP_TEXT)
    while True:
        try:
            line = input("you> ").strip()
        except EOFError:
            print()
            break
        if not line:
            continue
        lowered = line.lower()
        if lowered in ("exit", "quit"):
            print("Goodbye!")
            break
        elif lowered in ("help", "?"):
            print(HELP_TEXT)
        elif lowered == "add":
            add_expense_interactive(store)
        elif lowered == "paste":
            paste_receipt_interactive(store)
        elif lowered.startswith("delete"):
            print(handle_delete(store, line))
        elif lowered.startswith("list"):
            print(handle_list(store, line))
        elif lowered.startswith("total") or lowered.startswith("summary"):
            print(handle_total(store, line))
        else:
            print(handle_freeform(store, line))


def run_demo():
    with open(SAMPLE_RECEIPT_PATH) as f:
        text = f.read()
    parsed = parse_receipt_text(text)
    print("Parsed sample receipt (not saved):")
    for key, value in parsed.items():
        if key == "raw_text":
            continue
        print(f"  {key}: {value}")


def main():
    parser = argparse.ArgumentParser(description="Receipt Chat -- a conversational expense tracker.")
    parser.add_argument("--store", default=DEFAULT_STORE_PATH, help="Path to the expenses JSON file")
    parser.add_argument(
        "--demo", action="store_true",
        help="Parse the bundled sample receipt and print the result, without saving it",
    )
    args = parser.parse_args()

    if args.demo:
        run_demo()
        return

    run_chat(ExpenseStore(args.store))


if __name__ == "__main__":
    main()
