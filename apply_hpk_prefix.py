import os
import re
import shutil
import sys
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import VENDOR, VENDOR_DELIVERY_ID, VENDOR_BOX_NUMBER


def _get_destination():
    parts = str(VENDOR_DELIVERY_ID).split("_")
    if len(parts) >= 3:
        return parts[1].upper()
    return None


def _get_expected_vendor_folder():
    dest = _get_destination()
    if dest:
        return f"HPK_{dest}"
    return None


def _get_expected_box_suffix():
    return f"Box{str(VENDOR_BOX_NUMBER).zfill(2)}"


def _filter_by_config(matches):
    vendor = _get_expected_vendor_folder()
    box_suffix = _get_expected_box_suffix()
    if not vendor or not box_suffix:
        return None
    filtered = []
    for m in matches:
        parts = m.replace("\\", "/").split("/")
        for p in parts:
            if p.startswith("Box") and p.endswith("_checked"):
                if p == f"{box_suffix}_checked":
                    filtered.append(m)
                    break
    if len(filtered) == 1:
        return filtered[0]
    vendor_filtered = [m for m in filtered if vendor in m]
    if len(vendor_filtered) == 1:
        return vendor_filtered[0]
    return None


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
    if vendor_upper in ("HAMAMATSU", "HPK"):
        prefix = "HPK"
    elif vendor_upper == "FBK":
        prefix = "SMB"
    else:
        print(f"VENDOR is {VENDOR}, not HPK/HAMAMATSU/FBK. Prefix not applicable.")
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

                def transform_id(val, p=prefix):
                    if pd.isna(val):
                        return val
                    s = str(val).strip()
                    if s.startswith(p):
                        return val
                    rest = re.sub(r'^[A-Za-z]+', '', s)
                    if rest != s and rest:
                        return f"{p}{rest}"
                    if s.isdigit():
                        return f"{p}{s.zfill(5)}"
                    return val

                new_vals = df[col].apply(transform_id)
                if not new_vals.equals(df[col]):
                    df[col] = new_vals
                    modified = True

            if modified:
                df.to_excel(fpath, index=False)
                print(f"  [FIX] {tray_name}/{fname}: {prefix} prefix added to strip IDs.")
                modified_any = True

        except Exception as e:
            print(f"  [Error] {tray_name}/{fname}: {e}")

    return modified_any


def process_tray(tray_path):
    print(f"\nProcessing: {tray_path}")

    ok = apply_hpk_prefix(tray_path)
    if ok:
        print("Done: vendor prefixes applied.")
    else:
        print("No changes needed (IDs already have prefix or vendor not applicable).")

    tray_name = os.path.basename(tray_path)
    tray_parent = os.path.dirname(tray_path)
    zip_base = os.path.join(tray_parent, tray_name)
    zip_path = shutil.make_archive(zip_base, "zip", tray_path)
    print(f"Zipped: {zip_path}")


def resolve_tray(tray_input):
    matches = find_tray_path(tray_input)
    if not matches:
        print(f"Tray '{tray_input}' not found in checked/ directory.")
        return None
    if len(matches) == 1:
        return matches[0]
    auto = _filter_by_config(matches)
    if auto:
        print(f"Auto-selected by config (dest={_get_destination()}, box={VENDOR_BOX_NUMBER}):")
        print(f"  {auto}")
        return auto
    print(f"Found {len(matches)} matches for '{tray_input}':")
    for i, m in enumerate(matches):
        print(f"  [{i + 1}] {m}")
    choice = input("Select one (number, or 's' to skip): ").strip()
    if choice.lower() == "s":
        return None
    try:
        idx = int(choice) - 1
        return matches[idx]
    except (ValueError, IndexError):
        print("Invalid selection, skipping.")
        return None


if __name__ == "__main__":
    if len(sys.argv) > 1:
        tray_inputs = sys.argv[1:]
    else:
        raw = input("Enter tray number(s) (e.g. 5, 12, Tray000012, or space-separated): ").strip()
        if not raw:
            print("No tray specified.")
            sys.exit(1)
        tray_inputs = raw.split()

    for ti in tray_inputs:
        tray_path = resolve_tray(ti.strip())
        if tray_path:
            process_tray(tray_path)
