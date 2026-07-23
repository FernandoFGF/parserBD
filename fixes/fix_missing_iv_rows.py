import os
import re
from collections import Counter
import pandas as pd
import numpy as np


def _make_inserted_row(template, group_cols, key, loc, df_cols):
    new_row = template.copy()
    for i, col in enumerate(group_cols):
        new_row[col] = key[i]
    new_row['SiPM_Location'] = loc
    if 'V' in df_cols:
        new_row['V'] = '[0]'
    if 'I' in df_cols:
        new_row['I'] = '[0]'
    if 'I_Err' in df_cols:
        new_row['I_Err'] = '[0]'
    for col in ['Fit_range_Low', 'Fit_Polynomial_Degree']:
        if col in df_cols:
            new_row[col] = 0
    if 'Status' in df_cols:
        new_row['Status'] = 'Failed'
    if 'Comment' in df_cols:
        new_row['Comment'] = np.nan
    return new_row


def fix_missing_iv_rows(base_dir=None):
    if base_dir is None:
        base_dir = os.getcwd()

    box_pattern = re.compile(r"^Box\d{2}$")
    tray_pattern = re.compile(r"^Tray\d{6}$")

    file_name = "IV-SiPM-characterization.xlsx"

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

                group_cols = ['SiPM_Strip_ID', 'Thermal_Cycle',
                              'Polarization', 'Temperature']

                if not all(c in df.columns for c in group_cols):
                    continue

                # Build the expected group pattern from existing data:
                # For each strip, collect its (Cycle, Polarization, Temp) combos,
                # then use the most common set as the expected pattern.
                strip_combos = {}
                for strip, gdf in df.groupby('SiPM_Strip_ID', sort=False):
                    combos = set()
                    for _, row in gdf.iterrows():
                        combos.add((row['Thermal_Cycle'], row['Polarization'], row['Temperature']))
                    strip_combos[strip] = frozenset(combos)

                # Find the most common combo set among existing strips
                from collections import Counter
                pattern_counts = Counter(strip_combos.values())
                if not pattern_counts:
                    continue
                expected_pattern = pattern_counts.most_common(1)[0][0]
                unique_strips = set(df['SiPM_Strip_ID'].dropna().unique())

                total_inserted = 0
                new_rows = []
                missing_details = []  # (strip, combo_tuple, missing_locs, start_row_excel)

                for strip in sorted(unique_strips):
                    existing_combos = strip_combos.get(strip, frozenset())
                    template_df = df[df['SiPM_Strip_ID'] == strip]
                    template = template_df.iloc[0] if len(template_df) > 0 else df.iloc[0]

                    for combo in sorted(expected_pattern):
                        key = (strip,) + combo
                        # Find existing rows for this combo
                        mask = (
                            (df['SiPM_Strip_ID'] == strip) &
                            (df['Thermal_Cycle'] == combo[0]) &
                            (df['Polarization'] == combo[1]) &
                            (df['Temperature'] == combo[2])
                        )
                        sub = df[mask]
                        if len(sub) == 0:
                            # Entire combo missing for this strip — insert 6 rows
                            start_row = len(new_rows) + 2
                            for loc in range(6):
                                new_rows.append(_make_inserted_row(
                                    template, group_cols, key, loc, df.columns))
                                total_inserted += 1
                            missing_details.append(
                                (strip, combo, list(range(6)), start_row, start_row + 5))
                        else:
                            # Combo exists — fill missing locations
                            loc_rows = {}
                            for _, row in sub.iterrows():
                                loc_rows[int(row['SiPM_Location'])] = row
                            # Use first row of this combo as template
                            local_template = sub.iloc[0]
                            missing_locs = []
                            start_row = None
                            for loc in range(6):
                                if loc in loc_rows:
                                    new_rows.append(loc_rows[loc])
                                else:
                                    if start_row is None:
                                        start_row = len(new_rows) + 2
                                    new_rows.append(_make_inserted_row(
                                        local_template, group_cols, key, loc, df.columns))
                                    total_inserted += 1
                                    missing_locs.append(loc)
                            if missing_locs:
                                end_row = start_row + len(missing_locs) - 1
                                missing_details.append(
                                    (strip, combo, missing_locs, start_row, end_row))

                if total_inserted == 0:
                    continue

                new_df = pd.DataFrame(new_rows).reset_index(drop=True)
                new_df.to_excel(file_path, index=False)

                print(f"[FIX] {tray_folder}/{file_name}: "
                      f"Inserted {total_inserted} missing row(s) "
                      f"to complete SiPM_Location sequence 0-5")
                for strip, combo, locs, r_start, r_end in missing_details:
                    cycle, pol, temp = combo
                    if len(locs) == 6:
                        print(f"  -> Sensor {strip} missing entire group "
                              f"(Cycle={cycle}, Polarization={pol}, Temperature={temp}) "
                              f"- added 6 rows at rows {r_start}-{r_end}")
                    else:
                        print(f"  -> Sensor {strip} missing locations {locs} "
                              f"for group (Cycle={cycle}, Polarization={pol}, Temperature={temp}) "
                              f"- added {len(locs)} row(s) at rows {r_start}-{r_end}")

            except Exception as e:
                print(f"Error processing {tray_folder}/{file_name}: {e}")


if __name__ == "__main__":
    fix_missing_iv_rows()
