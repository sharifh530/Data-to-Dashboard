# Upload test data

`synthetic-sales-messy.csv` is entirely fictional, UTF-8 CSV: 245 data rows, 11 columns, 17,418 bytes. Select CSV in the workspace upload form. Current support stores/downloads bytes only; automated inspection and cleaning are not enabled.

Columns: order_id, order_date, customer_id, region, channel, category, quantity, unit_price, discount_rate, revenue, delivery_days. Customer IDs deliberately retain leading zeros. Dates cover January–June 2025. There are no real people or business records.

Deliberate issues: five exact duplicate rows; some region names have surrounding spaces and lowercase spelling; some prices include a dollar sign; some channel and delivery_days values are missing. The CSV structure itself is valid. Revenue is quantity × unit price × (1 − discount), rounded to cents, before formatting issues are introduced. Do not use revenue prediction from these inputs as meaningful model-quality evidence: it is a constructed arithmetic target.

Validation: parsed with Python's standard CSV reader; confirmed 245 rows, 11 fields each, 240 distinct order IDs, five exact duplicates, and positive numeric revenue. This checked-in synthetic fixture was generated locally; no uploaded untrusted file was parsed.
