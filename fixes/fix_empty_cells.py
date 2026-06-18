import os
import re
import pandas as pd

def fill_empty_cells(base_dir=None):
    """
    Walks Box##/Tray###### folders and fills blank/NaN cells with 1
    in both SiPM-mass-test-results.xlsx and IV-SiPM-characterization.xlsx.
    """
    if base_dir is None:
        base_dir = os.getcwd()

    box_pattern = re.compile(r"^Box\d{2}$")
    tray_pattern = re.compile(r"^Tray\d{6}$")

    # Files to check and the numeric columns where blanks should be filled
    files_and_columns = {
        "SiPM-mass-test-results.xlsx": ['Result', 'Result_Err', 'Strip_Avg_Result'],
        "IV-SiPM-characterization.xlsx": ['SiPM_Location'],
    }

    for box_folder in os.listdir(base_dir):
        box_path = os.path.join(base_dir, box_folder)
        if not (os.path.isdir(box_path) and box_pattern.match(box_folder)):
            continue

        for tray_folder in os.listdir(box_path):
            tray_path = os.path.join(box_path, tray_folder)
            if not (os.path.isdir(tray_path) and tray_pattern.match(tray_folder)):
                continue

            for file_name, columns_to_check in files_and_columns.items():
                file_path = os.path.join(tray_path, file_name)

                if not os.path.exists(file_path):
                    continue

                try:
                    df = pd.read_excel(file_path)
                    modified = False

                    for column in columns_to_check:
                        if column not in df.columns:
                            continue

                        empty_mask = df[column].isna()
                        if empty_mask.any():
                            empty_rows = df[empty_mask].index.tolist()
                            print(f"[FIX] {tray_folder}/{file_name}: "
                                  f"Filled {len(empty_rows)} blank(s) with 0 "
                                  f"in column '{column}' at rows {[x + 2 for x in empty_rows]}")
                            df[column] = df[column].fillna(0)
                            modified = True

                    if modified:
                        df.to_excel(file_path, index=False)

                except Exception as e:
                    print(f"Error processing {tray_folder}/{file_name}: {e}")

if __name__ == "__main__":
    fill_empty_cells()
