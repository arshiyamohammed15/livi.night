import pytest

from p3 import (
    BankAccount,
    Inventory,
    Order,
    OrderItem,
    Product,
    apply_coupon,
    calculate_subtotal,
    compute_tax,
    parse_products_csv,
    process_order,
)


def build_inventory() -> Inventory:
    inv = Inventory()
    for product in [
        Product("SKU1", "Pen", 10.5, "stationery"),
        Product("SKU2", "Notebook", 25.0, "books"),
    ]:
        inv.add_product(product)
        inv.add_stock(product.sku, 10)
    return inv


def test_parse_products_csv_skips_header_and_preserves_float_prices() -> None:
    csv_text = """sku,name,price,category
SKU1,Pen,10.50,stationery
SKU2,Notebook,25.00,books
"""
    products = parse_products_csv(csv_text)

    assert len(products) == 2
    assert products[0].sku == "SKU1"
    assert products[0].price == pytest.approx(10.5)
    assert products[1].price == pytest.approx(25.0)


def test_parse_products_csv_empty_text_returns_empty_list() -> None:
    assert parse_products_csv("   \n") == []


def test_parse_products_csv_malformed_row_raises() -> None:
    csv_text = "sku,name,price\nBADSKU,OnlyTwoFields"
    with pytest.raises(ValueError):
        parse_products_csv(csv_text)


def test_inventory_add_stock_accumulates_instead_of_overwriting() -> None:
    inv = Inventory()
    inv.add_product(Product("SKU1", "Pen", 5.0))

    inv.add_stock("SKU1", 2)
    inv.add_stock("SKU1", 3)

    assert inv.get_stock("SKU1") == 5


def test_inventory_add_stock_validations() -> None:
    inv = Inventory()
    inv.add_product(Product("SKU1", "Pen", 5.0))

    with pytest.raises(ValueError):
        inv.add_stock("SKU1", 0)
    with pytest.raises(KeyError):
        inv.add_stock("UNKNOWN", 1)


def test_inventory_remove_stock_blocks_if_insufficient() -> None:
    inv = Inventory()
    inv.add_product(Product("SKU1", "Pen", 5.0))
    inv.add_stock("SKU1", 1)

    with pytest.raises(ValueError):
        inv.remove_stock("SKU1", 2)


def test_inventory_remove_stock_invalid_qty() -> None:
    inv = Inventory()
    inv.add_product(Product("SKU1", "Pen", 5.0))
    inv.add_stock("SKU1", 1)

    with pytest.raises(ValueError):
        inv.remove_stock("SKU1", 0)


def test_apply_coupon_behaviour() -> None:
    assert apply_coupon(200.0, "SAVE10") == pytest.approx(180.0)
    assert apply_coupon(250.0, "FLAT50") == pytest.approx(200.0)
    assert apply_coupon(150.0, "FLAT50") == pytest.approx(150.0)


def test_apply_coupon_handles_none_and_unknown_codes() -> None:
    assert apply_coupon(100.0, None) == pytest.approx(100.0)
    assert apply_coupon(100.0, "BOGUS") == pytest.approx(100.0)


def test_compute_tax_rounds_only_at_end() -> None:
    amount = 10.015
    expected_tax = round(amount * 0.18, 2)

    assert compute_tax(amount) == expected_tax


def test_calculate_subtotal_uses_exact_quantities() -> None:
    inv = Inventory()
    inv.add_product(Product("SKU1", "Pen", 10.0))
    inv.add_product(Product("SKU2", "Book", 5.0))

    order = Order("ORD1", [OrderItem("SKU1", 2), OrderItem("SKU2", 3)])

    assert calculate_subtotal(order, inv) == pytest.approx(2 * 10.0 + 3 * 5.0)


def test_calculate_subtotal_unknown_sku_raises() -> None:
    inv = Inventory()
    order = Order("ORD2", [OrderItem("MISSING", 1)])

    with pytest.raises(KeyError):
        calculate_subtotal(order, inv)


def test_process_order_validates_all_skus() -> None:
    inv = build_inventory()
    payer = BankAccount("Tester", 100.0)
    order = Order(
        "ORD-SKUS",
        [
            OrderItem("SKU1", 1),
            OrderItem("UNKNOWN", 1),
        ],
    )

    with pytest.raises(KeyError):
        process_order(order, inv, payer)


def test_process_order_checks_stock_per_item() -> None:
    inv = build_inventory()
    payer = BankAccount("Tester", 0.0)
    order = Order(
        "ORD-STOCK",
        [
            OrderItem("SKU1", 1),
            OrderItem("SKU2", 20),
        ],
    )

    with pytest.raises(ValueError):
        process_order(order, inv, payer)


def test_process_order_tax_applies_on_discounted_total() -> None:
    inv = build_inventory()
    payer = BankAccount("Tester", 100.0)
    order = Order(
        "ORD-TAX",
        [
            OrderItem("SKU1", 2),
        ],
        coupon_code="SAVE10",
    )

    receipt = process_order(order, inv, payer)

    subtotal = calculate_subtotal(order, inv)
    discounted = apply_coupon(subtotal, "SAVE10")
    expected_tax = round(discounted * 0.18, 2)

    assert receipt["discounted"] == pytest.approx(discounted)
    assert receipt["tax"] == pytest.approx(expected_tax)
    assert receipt["grand_total"] == pytest.approx(discounted + expected_tax)


def test_bank_account_deposit_validations() -> None:
    acct = BankAccount("Tester", 0.0)

    with pytest.raises(TypeError):
        acct.deposit("10")  # type: ignore[arg-type]
    with pytest.raises(ValueError):
        acct.deposit(-5)


def test_bank_account_withdraw_validations() -> None:
    acct = BankAccount("Tester", 50.0)
    acct.deposit(25)

    with pytest.raises(ValueError):
        acct.withdraw(0)
    with pytest.raises(ValueError):
        acct.withdraw(1000)
