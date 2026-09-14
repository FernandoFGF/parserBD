# SiPM Data Tools

Unified tool for validating and fixing raw SiPM data before uploading it to the DUNE database.

> **New in another laboratory:** read **`LAB_INSTRUCTIONS.md`** first.

## Quick install

```bash
pip install -r requirements.txt
copy config.example.py config.py   # on Linux/Mac: cp config.example.py config.py
```

On Windows you can also use `install.bat` and then `run.bat`.

## Usage

1. Edit `config.py` (`VENDOR`, `VENDOR_DELIVERY_ID`, `VENDOR_BOX_NUMBER`, `TEST_BOX_ID`, `INSTITUTION`).
2. Copy the original folder (e.g. `Box16`) into `input/`.
3. Run `python main.py`.
4. Collect the result from `checked/<VENDOR>/Box##_checked/` (`Tray******_checked` + `global_validation_log.md`).

## Structure

- `main.py`: main executable.
- `auto.py`: alternative entry point (same processing as `main.py`).
- `verify.py`: verifies a processed Box (`python verify.py fbk Box05`).
- `apply_hpk_prefix.py`: manual replacement from `referencia/` + HPK/SMB prefixes.
- `config.example.py`: template (copy to `config.py`, which is never shared).
- `fixes/`, `validators/`: fixes and validators.
- `input/`, `output/`, `checked/`, `referencia/`: local data (never sent).
