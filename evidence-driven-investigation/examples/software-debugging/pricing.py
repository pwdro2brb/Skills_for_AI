"""Toy module with a bug report attached: "average_price crashes for some stores"."""


def parse_price(text):
    """Parse a price string like '12.50' or 'R$ 12.50' into a float."""
    return float(text.strip().replace("R$", ""))


def average_price(rows):
    prices = [parse_price(r["price"]) for r in rows]
    return sum(prices) / len(prices)
