def add(a, b):
    """Return the sum of two numbers."""
    return a + b


def divide(a, b):
    """Divide a by b, raising ValueError for zero divisor."""
    if b == 0:
        raise ValueError("Cannot divide by zero")
    return a / b


def is_even(n: int) -> bool:
    """True if n is even, False otherwise."""
    return n % 2 == 0


if __name__ == "__main__":
    print("add(2, 3) =", add(2, 3))
    print("divide(10, 2) =", divide(10, 2))
    print("is_even(6) =", is_even(6))
