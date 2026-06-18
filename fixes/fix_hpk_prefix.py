import os
import re
import sys
import pandas as pd

parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if parent_dir not in sys.path:
    sys.path.append(parent_dir)

try:
    from config import VENDOR
except ImportError:
    VENDOR = "FBK"


def fix_hpk_prefix(base_dir=None):
    if base_dir is None:
        base_dir = os.getcwd()

    vendor_upper = VENDOR.strip().upper()
    if vendor_upper not in ("HAMAMATSU", "HPK"):
        return

    box_pattern = re.compile(r"^Box\d{2}$")
    tray_pattern = re.compile(r"^Tray\d{6}$")

    files_to_check = [
        "SiPM-item-manifest.xlsx",
        "IV-SiPM-characterization.xlsx",
        "IV-SiPM-noise-test.xlsx",
        "SiPM-mass-test-results.xlsx",
        "Dark-noise-SiPM-counts.xlsx",
    ]

    for box_folder in os.listdir(base_dir):
        box_path = os.path.join(base_dir, box_folder)
        if not (os.path.isdir(box_path) and box_pattern.match(box_folder)):
            continue

        for tray_folder in os.listdir(box_path):
            tray_path = os.path.join(box_path, tray_folder)
            if not (os.path.isdir(tray_path) and tray_pattern.match(tray_folder)):
                continue

            for fname in files_to_check:
                fpath = os.path.join(tray_path, fname)
                if not os.path.exists(fpath):
                    continue

                try:
                    df = pd.read_excel(fpath)
                    modified = False

                    if fname == "SiPM-item-manifest.xlsx":
                        id_cols = [df.columns[4], df.columns[9]]
                    else:
                        id_cols = [df.columns[0]]

                    for col in id_cols:
                        if col not in df.columns:
                            continue

                        def transform_id(val):
                            if pd.isna(val):
                                return val
                            s = str(val).strip()
                            if s.startswith("HPK"):
                                return val
                            digits = s
                            if digits.isdigit():
                                padded = digits.zfill(5)
                                return f"HPK{padded}"
                            return val

                        new_vals = df[col].apply(transform_id)
                        if not new_vals.equals(df[col]):
                            df[col] = new_vals
                            modified = True

                    if modified:
                        df.to_excel(fpath, index=False)
                        print(f"[FIX] {tray_folder}/{fname}: HPK prefix added to strip IDs.")

                except Exception as e:
                    print(f"[Error] {tray_folder}/{fname}: {e}")


if __name__ == "__main__":
    fix_hpk_prefix()
