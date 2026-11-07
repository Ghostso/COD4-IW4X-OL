"""Build AlwaysofflineRe's complete CODOL SKU catalog from dumped StringTables."""

from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path
from typing import Any


TABLES = {
    "skus": "mp_comarketplaceskus.csv",
    "products": "mp_comarketplaceproducts.csv",
    "product_items": "mp_comarketplaceproductitems.csv",
    "items": "mp_coMarketplaceItems.csv",
}


def parse_args() -> argparse.Namespace:
    repository = Path(__file__).resolve().parents[2]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input_dir", type=Path, help="Directory created by DumpCodolStringTables.py")
    parser.add_argument(
        "--output",
        type=Path,
        default=repository / "assets" / "backend" / "1004" / "MarketplaceSkus.json",
    )
    return parser.parse_args()


def read_rows(path: Path, minimum_columns: int) -> list[list[str]]:
    with path.open(encoding="utf-8", newline="") as stream:
        rows = list(csv.reader(stream))
    for index, row in enumerate(rows, 1):
        if len(row) < minimum_columns:
            raise ValueError(f"{path.name}:{index}: expected at least {minimum_columns} columns")
    return rows


def positive(value: str, context: str) -> int:
    try:
        result = int(value, 10)
    except ValueError as error:
        raise ValueError(f"{context}: invalid integer {value!r}") from error
    if result <= 0 or result > 0xFFFFFFFF:
        raise ValueError(f"{context}: value outside uint32 range: {result}")
    return result


def optional_unsigned(value: str, context: str) -> int | None:
    if not value:
        return None
    try:
        result = int(value, 10)
    except ValueError as error:
        raise ValueError(f"{context}: invalid integer {value!r}") from error
    if result < 0 or result > 0xFFFFFFFF:
        raise ValueError(f"{context}: value outside uint32 range: {result}")
    return result


def make_grant(row: list[str], item_index: int, quantity_index: int, duration_index: int, context: str) -> dict[str, Any]:
    grant: dict[str, Any] = {
        "itemId": positive(row[item_index], f"{context} item"),
        "quantity": positive(row[quantity_index], f"{context} quantity"),
    }
    duration = optional_unsigned(row[duration_index], f"{context} duration")
    if duration is not None:
        grant["durationDays"] = duration
    return grant


def main() -> int:
    args = parse_args()
    source = args.input_dir.resolve()
    paths = {name: source / filename for name, filename in TABLES.items()}
    missing = [str(path) for path in paths.values() if not path.is_file()]
    if missing:
        raise SystemExit("Missing dumped tables:\n" + "\n".join(missing))

    sku_rows = read_rows(paths["skus"], 16)
    product_rows = read_rows(paths["products"], 10)
    extra_rows = read_rows(paths["product_items"], 4)
    item_rows = read_rows(paths["items"], 12)

    items = {
        positive(row[0], f"items row {index}"): {
            "name": row[1],
            "type": row[2],
            "subtype": row[3],
        }
        for index, row in enumerate(item_rows, 1)
    }
    extras: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for index, row in enumerate(extra_rows, 1):
        product_id = positive(row[0], f"product-items row {index} product")
        extras[product_id].append(make_grant(row, 1, 2, 3, f"product-items row {index}"))

    products: dict[int, dict[str, Any]] = {}
    for index, row in enumerate(product_rows, 1):
        product_id = positive(row[0], f"products row {index} product")
        if product_id in products:
            raise ValueError(f"duplicate product ID {product_id}")
        grants = [make_grant(row, 4, 5, 6, f"products row {index}")]
        grants.extend(extras.get(product_id, []))
        for grant in grants:
            metadata = items.get(grant["itemId"])
            if metadata:
                grant.update(metadata)
        product: dict[str, Any] = {"productId": product_id, "grants": grants}
        if row[1]:
            product["name"] = row[1]
        if row[2]:
            product["description"] = row[2]
        if row[3]:
            product["icon"] = row[3]
        if row[7]:
            product["requirement"] = row[7]
        requirement_value = optional_unsigned(row[8], f"products row {index} requirement value")
        if requirement_value is not None:
            product["requirementValue"] = requirement_value
        products[product_id] = product

    catalog: list[dict[str, Any]] = []
    seen_skus: set[int] = set()
    for index, row in enumerate(sku_rows, 1):
        sku = positive(row[0], f"skus row {index} SKU")
        product_id = positive(row[1], f"skus row {index} product")
        if sku in seen_skus:
            raise ValueError(f"duplicate SKU {sku}")
        seen_skus.add(sku)
        if product_id not in products:
            raise ValueError(f"SKU {sku} references missing product {product_id}")

        product = products[product_id]
        entry: dict[str, Any] = {
            "sku": sku,
            "productId": product_id,
        }
        prices = []
        for column in range(2, 6):
            amount = optional_unsigned(row[column], f"skus row {index} price column {column}")
            if amount is not None:
                prices.append({"column": column, "amount": amount})
        if prices:
            entry["prices"] = prices
        duration = optional_unsigned(row[6], f"skus row {index} duration")
        if duration is not None:
            entry["durationDays"] = duration
        available_from = optional_unsigned(row[7], f"skus row {index} available from")
        available_until = optional_unsigned(row[8], f"skus row {index} available until")
        if available_from is not None:
            entry["availableFrom"] = available_from
        if available_until is not None:
            entry["availableUntil"] = available_until
        if row[15]:
            entry["tags"] = row[15].split("|")
        catalog.append(entry)

    document = {
        "formatVersion": 2,
        "source": {
            "titleId": 1004,
            "tables": TABLES,
            "skuCount": len(catalog),
            "productCount": len(products),
            "additionalProductItemCount": len(extra_rows),
        },
        "products": list(products.values()),
        "skus": catalog,
    }
    output = args.output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8", newline="\n") as stream:
        stream.write("{\n")
        stream.write(f'  "formatVersion": {document["formatVersion"]},\n')
        stream.write('  "source": ' + json.dumps(document["source"], separators=(",", ":")) + ",\n")
        stream.write('  "products": [\n')
        for index, product in enumerate(document["products"]):
            suffix = "," if index + 1 != len(document["products"]) else ""
            stream.write("    " + json.dumps(product, separators=(",", ":"), ensure_ascii=True) + suffix + "\n")
        stream.write("  ],\n")
        stream.write('  "skus": [\n')
        for index, entry in enumerate(document["skus"]):
            suffix = "," if index + 1 != len(document["skus"]) else ""
            stream.write("    " + json.dumps(entry, separators=(",", ":"), ensure_ascii=True) + suffix + "\n")
        stream.write("  ]\n}\n")
    print(f"Built {len(catalog)} SKUs from {len(products)} products: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
