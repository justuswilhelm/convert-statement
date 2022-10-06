# DKB-Convert

```
./convert-statement.py
```

## Configuration

Create `config.toml` with contents

```
in_dir = "IN_DIR"
out_dir = "OUT_DIR"
```

Folder structure of in folder:

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

## Supported Banks

- DKB (CC and Giro as of Aug 2022)
- Shinsei (Format until Oct 2018)
- Shinsei (Format until Nov 2021)
- Shinsei (Current as of Aug 2022)
- Rakuten Corporate (Format as of Aug 2022)
- SMBC 普通預金 (Format until Jul 2022)
- SMBC 普通預金 (Current as of Aug 2022)
