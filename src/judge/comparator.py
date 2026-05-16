class OutputComparator:
    """MVP comparator: BOJ-style stripped stdout equality."""

    def equals(self, actual: str, expected: str) -> bool:
        return actual.strip() == expected.strip()

