import os
import re
import pandas as pd
import numpy as np


def fix_missing_iv_rows(base_dir=None):
    """
    Walks Box##/Tray###### folders and fixes missing rows in
    IV-SiPM-characterization.xlsx.

    The SiPM_Location column must cycle 0,1,2,3,4,5 for each group
    (same SiPM_Strip_ID + Thermal_Cycle + Polarization + Temperature).
    When locations are missing (e.g. the DAQ didn't record them), this fix
    inserts placeholder rows copying the shared metadata columns, setting
    SiPM_Location to the missing value, and filling measurement columns
    (V, I, I_Err, Fit_range_Low, Fit_Polynomial_Degree) with NaN and
    Status/Comment with 'No data - inserted by fix'.
    """
    if base_dir is None:
        base_dir = os.getcwd()

    box_pattern = re.compile(r"^Box\d{2}$")
    tray_pattern = re.compile(r"^Tray\d{6}$")

    file_name = "IV-SiPM-characterization.xlsx"

    # Columns that are shared across all 6 locations of a group
    shared_cols = [
        'SiPM_Strip_ID', 'Date', 'Location', 'Operator',
        'Thermal_Cycle', 'Polarization', 'Temperature',
        'R_cable', 'R_eff'
    ]

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

                if 'SiPM_Location' not in df.columns:
                    continue

                # Group by the combination that defines a "set of 6"
                group_cols = ['SiPM_Strip_ID', 'Thermal_Cycle',
                              'Polarization', 'Temperature']

                # Check if all group_cols exist
                if not all(c in df.columns for c in group_cols):
                    continue

                total_inserted = 0
                rows_to_insert = []

                # Process the dataframe in order, finding groups
                for _, group_df in df.groupby(group_cols, sort=False):
                    existing_locs = set(group_df['SiPM_Location'].dropna().astype(int).tolist())
                    expected_locs = {0, 1, 2, 3, 4, 5}
                    missing_locs = expected_locs - existing_locs

                    if not missing_locs:
                        continue

                    # Use the first row of the group as template for shared columns
                    template = group_df.iloc[0].copy()

                    for loc in sorted(missing_locs):
                        new_row = template.copy()
                        new_row['SiPM_Location'] = loc
                        # Set measurement columns to 1
                        for col in ['V', 'I', 'I_Err', 'Fit_range_Low',
                                    'Fit_Polynomial_Degree']:
                            if col in df.columns:
                                new_row[col] = 1
                        rows_to_insert.append((group_df.index[0], loc, new_row))
                        total_inserted += 1

                if total_inserted == 0:
                    continue

                # Build the new dataframe by inserting rows at the right positions
                # Strategy: rebuild by processing each group and ensuring all 6 locations
                new_rows = []
                for _, group_df in df.groupby(group_cols, sort=False):
                    existing_locs = set(group_df['SiPM_Location'].dropna().astype(int).tolist())
                    expected_locs = {0, 1, 2, 3, 4, 5}
                    missing_locs = expected_locs - existing_locs

                    # Build a dict of existing rows by location
                    loc_rows = {}
                    for _, row in group_df.iterrows():
                        loc_val = int(row['SiPM_Location'])
                        loc_rows[loc_val] = row

                    template = group_df.iloc[0]

                    for loc in range(6):
                        if loc in loc_rows:
                            new_rows.append(loc_rows[loc])
                        else:
                            new_row = template.copy()
                            new_row['SiPM_Location'] = loc
                            for col in ['V', 'I', 'I_Err', 'Fit_range_Low',
                                        'Fit_Polynomial_Degree']:
                                if col in df.columns:
                                    new_row[col] = 1
                            if 'Status' in df.columns:
                                new_row['Status'] = 'Failed'
                            if 'Comment' in df.columns:
                                new_row['Comment'] = np.nan
                            new_rows.append(new_row)

                new_df = pd.DataFrame(new_rows).reset_index(drop=True)
                new_df.to_excel(file_path, index=False)

                print(f"[FIX] {tray_folder}/{file_name}: "
                      f"Inserted {total_inserted} missing row(s) "
                      f"to complete SiPM_Location sequence 0-5")

            except Exception as e:
                print(f"Error processing {tray_folder}/{file_name}: {e}")


if __name__ == "__main__":
    fix_missing_iv_rows()
