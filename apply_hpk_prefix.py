import os
import re
import shutil
import sys
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import VENDOR, VENDOR_DELIVERY_ID, VENDOR_BOX_NUMBER

CHECKED_BOXES_DIR = r"C:\Users\Ferna\Desktop\database\checked_boxes"

DEST_TO_UPLOAD_FOLDER = {
    "CIEMAT": "Box_subidas_CIEMAT",
    "INFN": "Box_subidas_Italia",
}


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


def _filter_upload_by_config(matches):
    dest = _get_destination()
    box_suffix = _get_expected_box_suffix()
    upload_vendor = DEST_TO_UPLOAD_FOLDER.get(dest) if dest else None
    if not upload_vendor or not box_suffix:
        return None
    filtered = []
    for m in matches:
        parts = m.replace("\\", "/").split("/")
        has_vendor = upload_vendor in parts
        has_box = f"{box_suffix}-upload" in parts
        if has_vendor and has_box:
            filtered.append(m)
    if len(filtered) == 1:
        return filtered[0]
    return None

FILES = [
    "SiPM-item-manifest.xlsx",
    "IV-SiPM-characterization.xlsx",
    "IV-SiPM-noise-test.xlsx",
    "SiPM-mass-test-results.xlsx",
    "Dark-noise-SiPM-counts.xlsx",
]


def _extract_tray_num(tray_name):
    m = re.search(r"Tray(\d+)", tray_name, re.IGNORECASE)
    if m:
        return m.group(1)
    return None


def find_upload_source(tray_path):
    tray_name = os.path.basename(tray_path)
    tray_num = _extract_tray_num(tray_name)
    if not tray_num:
        print(f"  [WARN] Cannot extract tray number from {tray_name}")
        return None
    if not os.path.isdir(CHECKED_BOXES_DIR):
        print(f"  [WARN] checked_boxes dir not found: {CHECKED_BOXES_DIR}")
        return None

    upload_name = f"Tray{tray_num.zfill(6)}-upload"
    matches = []
    for root, dirs, _files in os.walk(CHECKED_BOXES_DIR):
        dirs[:] = [d for d in dirs if not d.startswith("~$")]
        for d in dirs:
            if d == upload_name:
                matches.append(os.path.join(root, d))

    if not matches:
        print(f"  [WARN] {upload_name} not found in checked_boxes")
        return None
    if len(matches) == 1:
        return matches[0]
    auto = _filter_upload_by_config(matches)
    if auto:
        print(f"  Auto-selected by config (dest={_get_destination()}, box={VENDOR_BOX_NUMBER}):")
        print(f"    {auto}")
        return auto
    print(f"  Found {len(matches)} matches for {upload_name}:")
    for i, m in enumerate(matches):
        print(f"    [{i + 1}] {m}")
    choice = input("  Select one (number, or 's' to skip): ").strip()
    if choice.lower() == "s":
        return None
    try:
        return matches[int(choice) - 1]
    except (ValueError, IndexError):
        print("  Invalid selection, skipping.")
        return None


def replace_with_upload(tray_path, source_path):
    tray_name = os.path.basename(tray_path)
    print(f"  Replacing {tray_name} with content from:")
    print(f"    {source_path}")

    for item in os.listdir(tray_path):
        item_path = os.path.join(tray_path, item)
        if os.path.isdir(item_path):
            shutil.rmtree(item_path)
        else:
            os.remove(item_path)

    for item in os.listdir(source_path):
        src = os.path.join(source_path, item)
        dst = os.path.join(tray_path, item)
        if os.path.isdir(src):
            shutil.copytree(src, dst)
        else:
            shutil.copy2(src, dst)

    print(f"  [OK] Content replaced.")


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


def process_tray(tray_path):
    print(f"\nProcessing: {tray_path}")

    source = find_upload_source(tray_path)
    if source:
        replace_with_upload(tray_path, source)

    ok = apply_hpk_prefix(tray_path)
    if ok:
        print("Done: HPK prefixes applied.")
    else:
        print("No changes needed (IDs already have HPK prefix or vendor is not HPK).")

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
