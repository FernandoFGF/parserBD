import os
import re
import sys
import pandas as pd

parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if parent_dir not in sys.path:
    sys.path.append(parent_dir)

try:
    from config import VENDOR, VENDOR_DELIVERY_ID, VENDOR_BOX_NUMBER, TEST_BOX_ID, INSTITUTION
except ImportError:
    VENDOR = "FBK"
    VENDOR_DELIVERY_ID = "FBK_ciemat_4"
    VENDOR_BOX_NUMBER = 5
    TEST_BOX_ID = "Gra5"
    INSTITUTION = "(99) University of Granada & CAFPE"


def fix_manifest(base_dir=None):
    """
    Reads each SiPM-item-manifest.xlsx and overwrites the columns
    Vendor, Vendor_Delivery_ID, Vendor_Box_Number, Tray_Number, and Test_Box_ID
    with the values from config.py. Vendor_Box_Number and Tray_Number are
    auto-detected from the folder names (Box## and Tray######).
    """
    if base_dir is None:
        base_dir = os.getcwd()

    box_pattern = re.compile(r"^Box(\d{2})$")
    tray_pattern = re.compile(r"^Tray(\d{6})$")

    for box_folder in os.listdir(base_dir):
        box_match = box_pattern.match(box_folder)
        if not box_match:
            continue

        box_num = int(box_match.group(1))
        box_path = os.path.join(base_dir, box_folder)

        if not os.path.isdir(box_path):
            continue

        for tray_folder in os.listdir(box_path):
            tray_match = tray_pattern.match(tray_folder)
            if not tray_match:
                continue

            tray_path = os.path.join(box_path, tray_folder)
            manifest_path = os.path.join(tray_path, "SiPM-item-manifest.xlsx")

            if not os.path.isfile(manifest_path):
                continue

            # Deduce Tray_Number from the folder name (full 6-digit number)
            digits = tray_match.group(1)
            tray_numbers = [int(digits)]

            try:
                df = pd.read_excel(manifest_path)
                modified = False

                # Fix Vendor
                if 'Vendor' in df.columns:
                    current = df['Vendor'].dropna().unique()
                    if not all(str(v).strip() == VENDOR for v in current):
                        df['Vendor'] = VENDOR
                        modified = True
                        print(f"[FIX] {tray_folder}: Vendor -> '{VENDOR}'")

                # Fix Vendor_Delivery_ID
                if 'Vendor_Delivery_ID' in df.columns:
                    current = df['Vendor_Delivery_ID'].dropna().unique()
                    if not all(str(v).strip() == VENDOR_DELIVERY_ID for v in current):
                        old_val = ', '.join(str(v).strip() for v in current) if len(current) > 0 else 'empty'
                        df['Vendor_Delivery_ID'] = VENDOR_DELIVERY_ID
                        modified = True
                        print(f"[FIX] {tray_folder}: Vendor_Delivery_ID '{old_val}' -> '{VENDOR_DELIVERY_ID}'")

                # Fix Vendor_Box_Number (auto-detected from Box## folder name)
                if 'Vendor_Box_Number' in df.columns:
                    current = df['Vendor_Box_Number'].dropna().unique()
                    if not all(int(v) == box_num for v in current):
                        df['Vendor_Box_Number'] = box_num
                        modified = True
                        print(f"[FIX] {tray_folder}: Vendor_Box_Number -> {box_num}")

                # Fix Tray_Number (auto-detected from folder name, e.g. Tray000138 -> 138)
                if 'Tray_Number' in df.columns:
                    current = df['Tray_Number'].dropna().unique()
                    if not all(int(v) == tray_numbers[0] for v in current):
                        df['Tray_Number'] = tray_numbers[0]
                        modified = True
                        print(f"[FIX] {tray_folder}: Tray_Number -> {tray_numbers[0]}")

                # Fix Test_Box_ID
                if 'Test_Box_ID' in df.columns:
                    current = df['Test_Box_ID'].dropna().unique()
                    if not all(str(v).strip() == TEST_BOX_ID for v in current):
                        df['Test_Box_ID'] = TEST_BOX_ID
                        modified = True
                        print(f"[FIX] {tray_folder}: Test_Box_ID -> '{TEST_BOX_ID}'")

                # Fix Institution
                if 'Institution' in df.columns:
                    current = df['Institution'].dropna().unique()
                    if not all(str(v).strip() == INSTITUTION for v in current):
                        old_val = ', '.join(str(v).strip() for v in current) if len(current) > 0 else 'empty'
                        df['Institution'] = INSTITUTION
                        modified = True
                        print(f"[FIX] {tray_folder}: Institution '{old_val}' -> '{INSTITUTION}'")

                if modified:
                    df.to_excel(manifest_path, index=False)

            except Exception as e:
                print(f"[Error] {tray_folder}: Could not process manifest: {e}")


if __name__ == "__main__":
    fix_manifest()
