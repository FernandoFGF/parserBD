# SiPM Data Tools — Guide for the receiving laboratory

Step-by-step guide to install and use the tool on another workstation,
without depending on the original machine's setup.

## 1. What it is and what it does

Validates and fixes raw SiPM data before uploading it to the DUNE database:

1. Reads `Box##` folders with `Tray******` (or `BoxX_TrayY_measures_*.zip` zips) from `input/`.
2. Applies automatic fixes (`fixes/`): noise floats, missing DAQ rows,
   empty cells, missing IV rows, manifest, missing IDs, HPK/SMB prefixes, comments.
3. Validates (`validators/`): `SiPM_Location` sequence, dates, means, IDs.
4. Exports to `checked/<VENDOR>/Box##_checked/` with `Tray******_checked` + `global_validation_log.md`.
5. Optional: uploads the resulting zip over SSH. With no SSH configured,
   everything stays local. No Excel tracking is done; the log file is the only report.

Secondary scripts:

- `verify.py`: verifies an already processed Box (`python verify.py fbk Box05`).
- `auto.py`: alternative entry point, runs the same processing as `main.py`.
- `apply_hpk_prefix.py`: manual use for replacement from `referencia/` + prefixes.
- `_analysis.py`: development only, do not use in production.

## 2. Requirements

- Python 3.10+ (3.11 or 3.12 recommended).
- Windows, Linux or Mac.
- Nothing to compile.

Check your Python:

```bash
python --version
```

## 3. Installation (5 minutes)

### Option A — Windows (recommended)

1. Copy the whole project folder to the new PC.
2. Double-click `install.bat`. This installs dependencies and creates `config.py` if missing.
3. Edit `config.py` (see section 4).

### Option B — Manual / Linux / Mac

```bash
python3 -m pip install -r requirements.txt
cp config.example.py config.py   # on Windows: copy config.example.py config.py
```

## 4. Mandatory configuration (`config.py`)

Open `config.py` and adjust ONLY the manifest section for your batch:

```python
VENDOR = "FBK"                    # 'FBK' or 'Hamamatsu'/'HPK'
VENDOR_DELIVERY_ID = "FBK_9"      # e.g. 'FBK_9', 'HPK_CIEMAT_08'
VENDOR_BOX_NUMBER = 16            # Box number to process (filters Box16)
TEST_BOX_ID = "Gra16"             # e.g. 'Gra5', 'Gra16'
INSTITUTION = "(99) University of Granada & CAFPE"
```

Notes:

- `VENDOR_BOX_NUMBER` decides which `Box##` folder in `input/` gets processed.
- `CHECKED_BOXES_DIR` defaults to `referencia/` (relative to the project).
  Only needed for the HPK "upload fix". If you don't have it, leave it as is.
- SSH: leave `SSH_REMOTE_HOST = ""` if you do NOT want remote upload.
  Only fill it in if your laboratory has its own server. Never upload `config.py`
  with a password to git, and never send it by email.

Optional environment variables (override `config.py`):

- `SIPM_CHECKED_BOXES`: path to the reference folder.
- `SIPM_CHECKED_FBK`, `SIPM_CHECKED_DIR`: analysis scripts only.

## 5. Normal use (each batch)

1. Edit `config.py` with the 5 values of the new batch.
2. Copy the full original folder (e.g. `Box16` with its zips inside) into `input/`.
   It must look like: `input/Box16/Box16_Tray*_measures_*.zip` or `input/Box16/Tray000***`.
3. Run:
   - Windows: double-click `run.bat`, or `python main.py`.
   - Linux/Mac: `./run.sh` or `python3 main.py`.
4. Collect the result from `checked/<VENDOR>/Box##_checked/`:
   - `global_validation_log.md`: only shows applied fixes and real errors.
   - `Tray******_checked`: folders ready to upload to DUNE.
5. If a tray comes out with errors, fix the source data or review the log and reprocess.

Follow-up verification example:

```bash
python verify.py fbk Box05
python verify.py hpk_ciemat Box32
python verify.py hpk_infn Box15
```

## 6. Folder structure (what is sent and what is not)

```
SiPM_Data_Tools/
  main.py, auto.py, verify.py, apply_hpk_prefix.py
  config.example.py      <- template (DO send)
  config.py              <- YOUR local data (DO NOT send, it is in .gitignore)
  requirements.txt       <- dependencies (DO send)
  install.bat / run.bat / install.sh / run.sh
  fixes/ / validators/   <- code (DO send)
  input/                 <- YOUR raw data (DO NOT send, only .gitkeep)
  output/                <- temporary (DO NOT send)
  checked/               <- results (DO NOT send, it is local)
  referencia/            <- HPK reference data (optional, NOT sent by default)
```

To hand the project to another laboratory, send ONLY the code:

```bash
git archive HEAD -o SiPM_Data_Tools.zip
```

or a manual zip EXCLUDING `input/`, `output/`, `checked/`, `referencia/` and `config.py`.
The recipient will generate their own `config.py` from `config.example.py` via `install.bat`.

## 7. Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| `No Box folder found in 'input/'` | Misnamed or empty folder | It must be `input/Box05` (exact, capital B) |
| `No Box folder found for number 16` | `VENDOR_BOX_NUMBER` mismatch | Set `config.py` to the number of the folder you put in `input/` |
| `ModuleNotFoundError: pandas/openpyxl/paramiko` | Dependencies not installed | Run `install.bat` or `pip install -r requirements.txt` |
| `Remote copy FAILED` | No network or bad SSH | Normal if you don't use SSH: leave `SSH_REMOTE_HOST = ""` |
| `Tray...-upload not found` | No `referencia/` folder | Only affects the HPK auto-fix; put your data in `referencia/` or ignore it |
| Unknown `VENDOR_DELIVERY_ID` | New vendor value | `main.py` leaves it in `output/` for manual placement |

## 8. Portability notes for this delivery

- New `requirements.txt`: `pandas`, `openpyxl`, `paramiko`, `numpy`.
- New `config.example.py`: template without secrets.
- `apply_hpk_prefix.py`: `CHECKED_BOXES_DIR` used to be absolute (`C:\Users\Ferna\...`),
  now relative to `referencia/` + `config.py` + `SIPM_CHECKED_BOXES` env var.
- `_analysis.py` and `checked/build_summary.py`: absolute paths replaced with relative ones.
- `fixes/__init__.py`, `validators/__init__.py` added for compatibility.
- `.gitignore`: ignores data contents but keeps folders with `.gitkeep`.
- Removed Excel tracking: `main.py` no longer creates `checked/summary.xlsx` nor syncs
  it remotely, and `auto.py` no longer updates statuses from `done.txt`.
  The per-tray report is only `global_validation_log.md` next to the results.
