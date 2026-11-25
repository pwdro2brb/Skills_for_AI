"""The fix, copied to work/pricing.py by build_example.py (the original stays untouched)."""


def parse_price(text):
    """Parse '12.50', '12,50', 'R$ 1.234,50' (Brazilian thousands/decimal) into a float."""
    text = text.strip().replace("R$", "").strip()
    if "," in text:
        text = text.replace(".", "").replace(",", ".")
    return float(text)


def average_price(rows):
    """Average price, or None when there are no orders (no price to average)."""
    prices = [parse_price(r["price"]) for r in rows]
    if not prices:
        return None
    return sum(prices) / len(prices)
