import os
import re
import sys
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import VENDOR

FILES = [
    "SiPM-item-manifest.xlsx",
    "IV-SiPM-characterization.xlsx",
    "IV-SiPM-noise-test.xlsx",
    "SiPM-mass-test-results.xlsx",
    "Dark-noise-SiPM-counts.xlsx",
]


def find_tray_path(tray_input):
    script_dir = os.path.dirname(os.path.abspath(__file__))
    checked_dir = os.path.join(script_dir, "checked")
    if not os.path.isdir(checked_dir):
        return None

    tray_num = tray_input.strip()
    if tray_num.isdigit():
        tray_folder = f"Tray{tray_num.zfill(6)}_checked"
    elif re.match(r"^Tray\d+$", tray_input, re.IGNORECASE):
        num = re.search(r"\d+", tray_input).group()
        tray_folder = f"Tray{num.zfill(6)}_checked"
    else:
        tray_folder = tray_input
        if not tray_folder.endswith("_checked"):
            tray_folder += "_checked"

    matches = []
    for vendor in os.listdir(checked_dir):
        vendor_path = os.path.join(checked_dir, vendor)
        if not os.path.isdir(vendor_path) or vendor.startswith("~$"):
            continue
        if vendor.upper() == "SUMMARY":
            continue
        for box_entry in os.listdir(vendor_path):
            box_path = os.path.join(vendor_path, box_entry)
            if not os.path.isdir(box_path):
                continue
            tray_path = os.path.join(box_path, tray_folder)
            if os.path.isdir(tray_path):
                matches.append(tray_path)

    return matches


def apply_hpk_prefix(tray_path):
    vendor_upper = VENDOR.strip().upper()
    if vendor_upper not in ("HAMAMATSU", "HPK"):
        print(f"VENDOR is {VENDOR}, not HPK/HAMAMATSU. HPK prefix not applicable.")
        return False

    tray_name = os.path.basename(tray_path)
    modified_any = False

    for fname in FILES:
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
                    if s.isdigit():
                        return f"HPK{s.zfill(5)}"
                    return val

                new_vals = df[col].apply(transform_id)
                if not new_vals.equals(df[col]):
                    df[col] = new_vals
                    modified = True

            if modified:
                df.to_excel(fpath, index=False)
                print(f"  [FIX] {tray_name}/{fname}: HPK prefix added to strip IDs.")
                modified_any = True

        except Exception as e:
            print(f"  [Error] {tray_name}/{fname}: {e}")

    return modified_any


if __name__ == "__main__":
    tray_input = input("Enter tray number (e.g. 5, 12, Tray000012): ").strip()
    if not tray_input:
        print("No tray specified.")
        sys.exit(1)

    matches = find_tray_path(tray_input)
    if not matches:
        print(f"Tray '{tray_input}' not found in checked/ directory.")
        sys.exit(1)

    if len(matches) > 1:
        print(f"Found {len(matches)} matches:")
        for i, m in enumerate(matches):
            print(f"  [{i + 1}] {m}")
        choice = input("Select one (number): ").strip()
        try:
            idx = int(choice) - 1
            tray_path = matches[idx]
        except (ValueError, IndexError):
            print("Invalid selection.")
            sys.exit(1)
    else:
        tray_path = matches[0]

    print(f"\nProcessing: {tray_path}")
    ok = apply_hpk_prefix(tray_path)
    if ok:
        print("Done: HPK prefixes applied.")
    else:
        print("No changes needed (IDs already have HPK prefix or vendor is not HPK).")
