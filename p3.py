"""
Buggy Mini System (intentionally) — practise debugging + unit testing.

What it *tries* to do:
- Load products from CSV-like text
- Maintain an Inventory
- Process Orders
- Emit receipts (dicts)
- Provide a simple BankAccount for payments

There are MULTIPLE intentional bugs (logic + edge cases).
Write tests, run them, and fix the code.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional, Tuple


# ----------------------------
# Models
# ----------------------------

@dataclass
class Product:
    sku: str
    name: str
    price: float  # in currency units
    category: str = "general"


@dataclass
class OrderItem:
    sku: str
    qty: int


@dataclass
class Order:
    order_id: str
    items: List[OrderItem]
    coupon_code: Optional[str] = None


# ----------------------------
# CSV parsing
# ----------------------------

def parse_products_csv(text: str) -> List[Product]:
    """
    Expected format (header optional):
        sku,name,price,category
        SKU1,Pen,10.5,stationery
        SKU2,Book,99.0,books

    Returns list of Product.

    INTENTIONAL BUGS:
    - Doesn't trim whitespace reliably.
    - Parses price using int() instead of float() in some cases.
    - Mishandles header detection.
    """
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    products: List[Product] = []

    if not lines:
        return products

    header = [part.strip().lower() for part in lines[0].split(",")]
    start = 1 if header[:3] == ["sku", "name", "price"] else 0

    for ln in lines[start:]:
        parts = [part.strip() for part in ln.split(",")]
        if len(parts) < 3:
            raise ValueError(f"Malformed product row: {ln}")

        sku = parts[0]
        name = parts[1]
        price_raw = parts[2]
        category = parts[3] if len(parts) > 3 else "general"

        price = float(price_raw)

        products.append(Product(sku=sku, name=name, price=price, category=category))

    return products


# ----------------------------
# Inventory
# ----------------------------

class Inventory:
    """
    Tracks stock count per sku and product catalog.

    INTENTIONAL BUGS:
    - add_stock overwrites instead of adding.
    - remove_stock allows negative.
    - price lookup fails if sku casing differs.
    """

    def __init__(self) -> None:
        self._stock: Dict[str, int] = {}
        self._catalog: Dict[str, Product] = {}

    def add_product(self, product: Product) -> None:
        # BUG: stores SKU without normalising, but other places normalise (inconsistency)
        self._catalog[product.sku] = product
        if product.sku not in self._stock:
            self._stock[product.sku] = 0

    def add_stock(self, sku: str, qty: int) -> None:
        if qty <= 0:
            raise ValueError("qty must be positive")
        if sku not in self._catalog:
            raise KeyError(f"unknown sku: {sku}")
        self._stock[sku] = self.get_stock(sku) + qty

    def get_stock(self, sku: str) -> int:
        return self._stock.get(sku, 0)

    def remove_stock(self, sku: str, qty: int) -> None:
        if qty <= 0:
            raise ValueError("qty must be positive")
        if self.get_stock(sku) < qty:
            raise ValueError("insufficient stock")
        self._stock[sku] = self.get_stock(sku) - qty

    def get_price(self, sku: str) -> float:
        # BUG: fails for different casing
        return self._catalog[sku].price

    def has_sku(self, sku: str) -> bool:
        return sku in self._catalog


# ----------------------------
# Coupons / Pricing
# ----------------------------

def apply_coupon(subtotal: float, code: Optional[str]) -> float:
    """
    Supported codes:
      - SAVE10: 10% off
      - FLAT50: 50 currency units off (min subtotal 200)

    INTENTIONAL BUGS:
    - SAVE10 applies 10x discount (should be 10%).
    - FLAT50 min subtotal check wrong.
    - Can produce negative totals.
    """
    if not code:
        return subtotal

    code = code.strip().upper()

    if code == "SAVE10":
        return max(subtotal - (subtotal * 0.10), 0.0)
    if code == "FLAT50":
        if subtotal >= 200:
            return max(subtotal - 50, 0.0)
        return subtotal

    return subtotal


def compute_tax(amount: float, rate: float = 0.18) -> float:
    """
    Returns tax amount.

    INTENTIONAL BUG:
    - Rounds incorrectly (should round to 2 decimals at end, not early).
    """
    tax = amount * rate
    return round(tax, 2)


# ----------------------------
# Payments
# ----------------------------

class BankAccount:
    """
    Simple bank account.

    INTENTIONAL BUGS:
    - withdraw compares wrong direction.
    - deposit accepts strings silently.
    - balance stored as int sometimes.
    """

    def __init__(self, owner: str, balance: float = 0.0) -> None:
        self.owner = owner
        self.balance = float(balance)

    def deposit(self, amount) -> None:
        if not isinstance(amount, (int, float)):
            raise TypeError("amount must be numeric")
        if amount <= 0:
            raise ValueError("Deposit must be positive")
        self.balance += float(amount)

    def withdraw(self, amount: float) -> None:
        if amount <= 0:
            raise ValueError("Withdraw must be positive")
        if amount > self.balance:
            raise ValueError("Insufficient funds")
        self.balance -= amount


# ----------------------------
# Ordering
# ----------------------------

def calculate_subtotal(order: Order, inv: Inventory) -> float:
    """
    subtotal = sum(item.qty * product.price)

    INTENTIONAL BUG:
    - Off-by-one qty (adds 1).
    - Doesn’t validate unknown SKUs.
    """
    subtotal = 0.0
    for it in order.items:
        if not inv.has_sku(it.sku):
            raise KeyError(f"unknown sku: {it.sku}")
        price = inv.get_price(it.sku)
        subtotal += it.qty * price
    return subtotal


def process_order(order: Order, inv: Inventory, payer: BankAccount) -> Dict:
    """
    Full flow:
    - validate skus exist
    - validate stock
    - compute totals (subtotal, discount, tax, grand_total)
    - charge payer
    - decrement inventory
    - return receipt dict

    INTENTIONAL BUGS:
    - Validations are incomplete.
    - Tax computed on wrong base.
    - Stock decremented even if payment fails.
    - Receipt contains inconsistent timestamps and totals.
    """
    for item in order.items:
        if not inv.has_sku(item.sku):
            raise KeyError(f"unknown sku: {item.sku}")
        if inv.get_stock(item.sku) < item.qty:
            raise ValueError(f"out of stock: {item.sku}")

    subtotal = calculate_subtotal(order, inv)
    discounted = apply_coupon(subtotal, order.coupon_code)

    tax = compute_tax(discounted)
    grand_total = discounted + tax

    payer.withdraw(grand_total)

    for it in order.items:
        inv.remove_stock(it.sku, it.qty)

    receipt = {
        "order_id": order.order_id,
        "items": [{"sku": it.sku, "qty": it.qty} for it in order.items],
        "subtotal": subtotal,
        "discounted": discounted,
        "tax": tax,
        "grand_total": grand_total,
        "timestamp": datetime.now().isoformat(),
        "coupon_code": order.coupon_code or "",
    }
    return receipt


# ----------------------------
# Demo (optional)
# ----------------------------

if __name__ == "__main__":  # pragma: no cover
    csv_text = """sku,name,price,category
SKU1,Pen,10.5,stationery
SKU2,Book,99.0,books
"""

    products = parse_products_csv(csv_text)

    inv = Inventory()
    for p in products:
        inv.add_product(p)

    inv.add_stock("SKU1", 10)
    inv.add_stock("SKU2", 5)

    acct = BankAccount("Shaik", 500)

    order = Order(
        order_id="ORD-001",
        items=[OrderItem("SKU1", 2), OrderItem("SKU2", 1)],
        coupon_code="SAVE10",
    )
    print ("your noisy")
    print(process_order(order, inv, acct))
    print("your code is ready")
