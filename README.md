# DKB-Convert

Create `config.toml` with contents, while making sure that `in_dir` and
`out_dir` do not point to the same or overlapping path.

```
in_dir = "IN_DIR"
out_dir = "OUT_DIR"
```

Put the files in the in folder so that you will have the following tree:

```
./in
├── dkb_cc
│   └── 2022-10-06
│       └── transactions.csv
├── dkb_giro
│   └── 2022-10-06
│       └── transactions.csv
├── rakuten
│   └── 2022-10-06
│       └── transactions.csv
├── shinsei
│   └── 2022-10-06
│       └── transactions.csv
├── shinsei_new
│   └── 2022-10-06
│       └── transactions.csv
├── shinsei_new_v2
│   └── 2022-10-06
│       └── transactions.csv
├── smbc
│   └── 2022-10-06
│       └── transactions.csv
└── smbc_new
    └── 2022-10-06
        └── transactions.csv
```

Then run

```
pipenv run ./convert-statement.py
```

The output can be found in the out folder.

## Supported Banks

- DKB (CC and Giro as of Aug 2022)
- Shinsei (Format until Oct 2018)
- Shinsei (Format until Nov 2021)
- Shinsei (Current as of Aug 2022)
- Rakuten Corporate (Format as of Aug 2022)
- SMBC 普通預金 (Format until Jul 2022)
- SMBC 普通預金 (Current as of Aug 2022)

## Testing

```
pipenv run ./convert-statement.py --config test/data/config.toml
```
