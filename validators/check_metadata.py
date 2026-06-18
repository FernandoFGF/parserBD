import os
import pandas as pd
import re
import sys

parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if parent_dir not in sys.path:
    sys.path.append(parent_dir)

try:
    from config import DELIVERY_ID, TEST_BOX_ID
except ImportError:
    DELIVERY_ID = '08'
    TEST_BOX_ID = '14'

def verify_excel(path_excel, expected_delivery, expected_test, expected_trays, expected_box, errors, tray_name):
    try:
        df = pd.read_excel(path_excel)

        # 1. Check Delivery (Vendor_Delivery_ID)
        if 'Vendor_Delivery_ID' in df.columns:
             col_delivery_val = df['Vendor_Delivery_ID']
             col_delivery_name = 'Vendor_Delivery_ID'
        else:
             col_delivery_val = df.iloc[:, 6]
             col_delivery_name = df.columns[6]

        if not col_delivery_val.dropna().apply(lambda x: str(x).strip())\
               .isin([f'HPK_CIEMAT_{expected_delivery}', f'HPK_INFN_{expected_delivery}', f'FBK_ciemat_{expected_delivery}', f'3FBK_ciemat_{expected_delivery}']).all():
            errors.append(f"{tray_name}: Incorrect values in column '{col_delivery_name}'.")

        # Check Test Box ID
        if 'Test_Box_ID' in df.columns:
             col_test_val = df['Test_Box_ID']
             col_test_name = 'Test_Box_ID'
        else:
             col_test_val = df.iloc[:, 6] 
             col_test_name = df.columns[6]

        if not col_test_val.dropna().apply(lambda x: str(x).strip())\
               .isin([f'Gra{expected_test}', f'Gra{expected_test}']).all():
            errors.append(f"{tray_name}: Incorrect values in column '{col_test_name}'.")

        # 2. Check Box (Vendor_Box_Number)
        if 'Vendor_Box_Number' in df.columns:
            col_box_val = df['Vendor_Box_Number']
            col_box_name = 'Vendor_Box_Number'
        else:
            col_box_val = df.iloc[:, 7]
            col_box_name = df.columns[7]

        if not col_box_val.dropna().apply(lambda x: int(x)).eq(expected_box).all():
            errors.append(f"{tray_name}: Incorrect values in column '{col_box_name}'. Expected: {expected_box}")

        # 3. Check Tray (Tray_Number)
        if 'Tray_Number' in df.columns:
            col_tray_val = df['Tray_Number']
            col_tray_name = 'Tray_Number'
        else:
            col_tray_val = df.iloc[:, 8]
            col_tray_name = df.columns[8]

        if len(expected_trays) == 2:
            if not col_tray_val.iloc[:10].dropna().apply(lambda x: int(x)).eq(expected_trays[0]).all():
                errors.append(f"{tray_name}: Incorrect values in column '{col_tray_name}' (rows 1-10). Expected: {expected_trays[0]}")
            
            if not col_tray_val.iloc[10:20].dropna().apply(lambda x: int(x)).eq(expected_trays[1]).all():
                errors.append(f"{tray_name}: Incorrect values in column '{col_tray_name}' (rows 11-20). Expected: {expected_trays[1]}")
        else:
            if not col_tray_val.dropna().apply(lambda x: int(x)).eq(expected_trays[0]).all():
                errors.append(f"{tray_name}: Incorrect values in column '{col_tray_name}'. Expected: {expected_trays[0]}")

    except Exception as e:
        errors.append(f"{tray_name}: Error processing file: {e}")

def check_data(base_dir=None):
    if base_dir is None:
        base_dir = os.path.dirname(os.path.abspath(__file__))

    for box_folder in os.listdir(base_dir):
        if re.match(r'Box\d{2}$', box_folder):
            box_num = int(box_folder[-2:])
            box_path = os.path.join(base_dir, box_folder)
            errors = []

            for tray_folder in os.listdir(box_path):
                if re.match(r'Tray\d{6}$', tray_folder):
                    digits = tray_folder[-6:]
                    part1 = int(digits[0:3])
                    part2 = int(digits[3:6])
                    
                    expected_trays = [t for t in [part1, part2] if t != 0]

                    excel_path = os.path.join(box_path, tray_folder, 'SiPM-item-manifest.xlsx')

                    if os.path.isfile(excel_path):
                        verify_excel(excel_path, DELIVERY_ID, TEST_BOX_ID, expected_trays, box_num, errors, tray_folder)
                    else:
                        errors.append(f"{tray_folder}: File 'SiPM-item-manifest.xlsx' not found.")

            print(f"\nVerification of {box_folder}:")
            if errors:
                for e in errors:
                    print(" -", e)
            else:
                print(" All correct in every Tray.")

if __name__ == "__main__":
    check_data()
