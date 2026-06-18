import os
import pandas as pd
import re

def extract_numbers(value):
    if isinstance(value, str):
        numbers = re.findall(r'\d+\.\d+', value)
        return f"[{', '.join(numbers)}]" if numbers else value
    return value

def fix_noise_floats(base_dir=None):
    if base_dir is None:
        base_dir = os.getcwd()

    file_name = "IV-SiPM-noise-test.xlsx"
    box_pattern = re.compile(r"^Box\d{2}$")
    tray_pattern = re.compile(r"^Tray\d{6}$")

    for box_folder in os.listdir(base_dir):
        box_path = os.path.join(base_dir, box_folder)
        if not (os.path.isdir(box_path) and box_pattern.match(box_folder)):
            continue

        for tray_folder in os.listdir(box_path):
            tray_path = os.path.join(box_path, tray_folder)
            if not (os.path.isdir(tray_path) and tray_pattern.match(tray_folder)):
                continue

            file_path = os.path.join(tray_path, file_name)

            if not os.path.exists(file_path):
                continue

            try:
                df = pd.read_excel(file_path)

                if "V_Range_Low" not in df.columns or "V_Range_High" not in df.columns:
                    print(f"Columns 'V_Range_Low' and 'V_Range_High' not found in {tray_folder}/{file_name}.")
                    continue

                df["V_Range_Low"] = df["V_Range_Low"].astype(str).apply(extract_numbers)
                df["V_Range_High"] = df["V_Range_High"].astype(str).apply(extract_numbers)

                df.to_excel(file_path, index=False)
                print(f"[FIX] {tray_folder}/{file_name}: Fixed noise floats.")
            except Exception as e:
                print(f"Error processing {tray_folder}/{file_name}: {e}")

if __name__ == "__main__":
    fix_noise_floats()
