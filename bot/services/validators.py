def parse_amount(value: str | None) -> float | None:
    if value is None:
        return None

    normalized = value.strip().replace(" ", "").replace(",", ".")
    if not normalized:
        return None

    try:
        amount = float(normalized)
    except ValueError:
        return None

    if amount <= 0:
        return None
    return amount


def format_amount(amount: float) -> str:
    formatted = f"{amount:,.2f}".replace(",", " ")
    if formatted.endswith(".00"):
        formatted = formatted[:-3]
    return formatted.replace(".", ",")
