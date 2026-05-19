def odd_even_distribution(draw: list[int]) -> dict[str, int]:
    odd = sum(1 for number in draw if number % 2)
    return {"odd": odd, "even": len(draw) - odd}


def low_high_distribution(draw: list[int]) -> dict[str, int]:
    low = sum(1 for number in draw if number <= 13)
    return {"low": low, "high": len(draw) - low}
