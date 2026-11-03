"""Regenerate only the five M6 synthetic text PDFs and malformed input.

Does not rewrite the original demo fixtures or reviewed parser expectations.
"""

from generate import HARBOR_PAGE_1, HARBOR_PAGE_2, HERE, _write_text_pdf


def main() -> None:
    variants = {
        "included_tooling.pdf": {
            "Tooling/setup cost: USD 150": "Tooling/setup: included in unit price; no separate charge"
        },
        "missing_moq.pdf": {"Minimum order quantity: 1,000 units": None},
        "quantity_mismatch.pdf": {"Quoted quantity: 2,000 units": "Quoted quantity: 5,000 units"},
        "non_usd.pdf": {
            line: line.replace("USD", "AUD") for line in HARBOR_PAGE_1 if "USD" in line
        },
        "explicit_unknown.pdf": {
            "Sample cost: USD 40": "Sample cost: not stated",
            "Shipping cost: USD 320 to Manila": "Shipping cost: to be confirmed",
            "Shipping time: 12 days after production": "Shipping time: not stated",
        },
    }
    for name, replacements in variants.items():
        lines = [replacements.get(line, line) for line in HARBOR_PAGE_1]
        _write_text_pdf(name, [[line for line in lines if line is not None], HARBOR_PAGE_2])
    (HERE / "malformed.pdf").write_bytes(
        b"%PDF-1.7\nSYNTHETIC DEMO QUOTE - intentionally malformed\n"
    )


if __name__ == "__main__":
    main()
