# SiPM Data Tools

Fixes and validates raw SiPM data so it is ready to upload to the DUNE database.

## 1. Requirements

Python 3.10+.

## 2. Install (once)

1. Copy the whole project folder to the new PC.
2. Install dependencies and create `config.py`:

```bash
pip install -r requirements.txt
copy config.example.py config.py
```

On Linux/Mac use `pip3` and `cp` instead of `copy`.

## 3. Configure (each batch)

Open `config.py` in a text editor and edit only these 5 lines:

```python
VENDOR = "FBK"                    # 'FBK' or 'HPK'
VENDOR_DELIVERY_ID = "FBK_9"      # e.g. 'FBK_9', 'HPK_CIEMAT_08'
VENDOR_BOX_NUMBER = 16            # box number you want to process
TEST_BOX_ID = "Gra16"             # e.g. 'Gra5', 'Gra16'
INSTITUTION = "(99) University of Granada & CAFPE"
```

Notes:

- `VENDOR_BOX_NUMBER` must match the folder you put in `input/`. If you set `16`, `input/Box16` must exist.
- Everything stays local in `checked/<VENDOR>/`.
- Never commit `config.py` to git.

## 4. Normal use (each batch)

1. Put the original box in `input/`. It must look like: `input/Box16/` with its `Tray...` zips or folders inside.
2. Run:

```bash
python main.py
```

3. Collect the result from `checked/<VENDOR>/Box16_checked/`:
   - `Tray******_checked` folders: ready to upload to DUNE.
   - `global_validation_log.md`: what was fixed and what errors remain.
4. If there are errors, fix the source data and reprocess.

Optional check of an already processed box (takes arguments: vendor + box):

```bash
python verify.py fbk Box05
python verify.py hpk_ciemat Box32
python verify.py hpk_infn Box15
```

## 5. What to send to another lab

| Send | Do not send |
|---|---|
| Code: `main.py`, `verify.py`, `fixes/`, `validators/`, `requirements.txt`, `config.example.py` | `config.py` (local data) |
| | `input/` (raw data) |
| | `checked/` and `output/` (results and temp files) |

A zip of the code without those folders and without `config.py` is enough. The recipient creates their own `config.py` from `config.example.py`.

## 6. Troubleshooting

| Message | Fix |
|---|---|
| `No Box folder found in 'input/'` | Folder name must be exact: `input/Box05` (capital B). |
| `No Box folder found for number 16` | Number in `config.py` does not match folder in `input/`. Make them equal. |
| `ModuleNotFoundError: pandas...` | Missing dependencies. Run `pip install -r requirements.txt`. |
