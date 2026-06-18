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

            # Deduce Tray_Number from the folder name
            # Supports both 4+2 (00XXYY -> XX, YY) and 3+3 (XXYYZZ -> XX, YYZZ) splits
            digits = tray_match.group(1)
            first4 = int(digits[0:4])
            last2 = int(digits[4:6])
            if first4 != 0 and last2 != 0 and digits.startswith("00"):
                tray_numbers = [first4, last2]
            else:
                first3 = int(digits[0:3])
                last3 = int(digits[3:6])
                tray_numbers = [t for t in [first3, last3] if t != 0]

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

                # Fix Tray_Number (auto-detected from folder)
                if 'Tray_Number' in df.columns:
                    if len(tray_numbers) == 2:
                        half = len(df) // 2
                        first_half = df.iloc[:half, df.columns.get_loc('Tray_Number')]
                        second_half = df.iloc[half:, df.columns.get_loc('Tray_Number')]
                        if not (all(int(v) == tray_numbers[0] for v in first_half.dropna()) and
                                all(int(v) == tray_numbers[1] for v in second_half.dropna())):
                            df.loc[df.index[:half], 'Tray_Number'] = tray_numbers[0]
                            df.loc[df.index[half:], 'Tray_Number'] = tray_numbers[1]
                            modified = True
                            print(f"[FIX] {tray_folder}: Tray_Number split -> top={tray_numbers[0]}, bottom={tray_numbers[1]}")
                    elif len(tray_numbers) == 1:
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
