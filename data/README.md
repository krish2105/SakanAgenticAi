# /data

This folder holds the raw real-estate transactions extract used by
`backend/scripts/map_dld_columns.py`. The real dataset is large (1M+ rows) and
is **not** committed to the repo — download it locally:

```bash
pip install kaggle --break-system-packages
# place your kaggle.json API token in ~/.kaggle/
kaggle datasets download -d alexefimik/dubai-real-estate-transactions-dataset -p ./data --unzip
```

This is a Kaggle mirror of the Dubai Land Department's public "Transactions"
open dataset (published on Dubai Pulse). It is **not** the synthetic dataset
described in `ARCHITECTURE.md` Section 7 — see the README's Data Sources
section for how the two relate.

Expected file: `data/transactions.csv`.
