import os
import re
import pandas as pd


def get_ids_from_file(file_path, filename, df):
    if filename == "SiPM-item-manifest.xlsx":
        ids = set()
        if df.shape[1] > 4:
            ids.update(df.iloc[:, 4].dropna().astype(str).tolist())
        if df.shape[1] > 9:
            ids.update(df.iloc[:, 9].dropna().astype(str).tolist())
        return ids
    else:
        if df.shape[1] > 0:
            return set(df.iloc[:, 0].dropna().astype(str).tolist())
    return set()


def fix_missing_ids(base_dir=None):
    if base_dir is None:
        base_dir = os.getcwd()

    box_pattern = re.compile(r"^Box\d{2}$")
    tray_pattern = re.compile(r"^Tray\d{6}$")

    files_to_check = [
        "SiPM-item-manifest.xlsx",
        "IV-SiPM-characterization.xlsx",
        "IV-SiPM-noise-test.xlsx",
        "SiPM-mass-test-results.xlsx",
        "Dark-noise-SiPM-counts.xlsx",
    ]

    for box_folder in os.listdir(base_dir):
        box_path = os.path.join(base_dir, box_folder)
        if not (os.path.isdir(box_path) and box_pattern.match(box_folder)):
            continue

        for tray_folder in os.listdir(box_path):
            tray_path = os.path.join(box_path, tray_folder)
            if not (os.path.isdir(tray_path) and tray_pattern.match(tray_folder)):
                continue

            # Read all existing files and collect their IDs
            file_data = {}
            all_ids = set()
            for fname in files_to_check:
                fpath = os.path.join(tray_path, fname)
                if os.path.exists(fpath):
                    try:
                        df = pd.read_excel(fpath)
                        ids = get_ids_from_file(fpath, fname, df)
                        file_data[fname] = {"df": df, "ids": ids}
                        all_ids.update(ids)
                    except Exception as e:
                        print(f"[Error] {tray_folder}: Could not read {fname}: {e}")

            if len(file_data) < 2:
                continue

            complete_ids = all_ids

            for fname, data in file_data.items():
                df = data["df"]
                current_ids = data["ids"]
                missing_ids = complete_ids - current_ids

                if not missing_ids:
                    continue

                # Find a template: all rows for one existing ID
                existing_id = next(iter(current_ids))
                if fname == "SiPM-item-manifest.xlsx":
                    template_rows = df[df.iloc[:, 4].astype(str) == existing_id]
                    if template_rows.empty:
                        template_rows = df[df.iloc[:, 9].astype(str) == existing_id]
                else:
                    template_rows = df[df.iloc[:, 0].astype(str) == existing_id]

                if template_rows.empty:
                    continue

                # Determine which columns hold the ID
                if fname == "SiPM-item-manifest.xlsx":
                    id_col_idxs = [4, 9]
                else:
                    id_col_idxs = [0]

                new_rows_list = []
                for missing_id_str in sorted(missing_ids):
                    for _, trow in template_rows.iterrows():
                        new_row = trow.to_dict()
                        for col_idx in id_col_idxs:
                            template_val = trow.iloc[col_idx]
                            try:
                                id_val = type(template_val)(missing_id_str)
                            except (ValueError, TypeError):
                                id_val = missing_id_str
                            new_row[df.columns[col_idx]] = id_val
                        new_rows_list.append(new_row)

                if not new_rows_list:
                    continue

                new_df = pd.DataFrame(new_rows_list)

                # Overwrite measurement columns with 0
                if fname == "IV-SiPM-characterization.xlsx":
                    for col in ["V", "I", "I_Err", "Fit_range_Low", "Fit_Polynomial_Degree"]:
                        if col in new_df.columns:
                            new_df[col] = 0
                elif fname == "IV-SiPM-noise-test.xlsx":
                    for col in ["V", "I", "V_Range_Low", "I_Mean_Low", "V_Range_High", "I_Mean_High", "I_Rel_Diff"]:
                        if col in new_df.columns:
                            new_df[col] = 0
                elif fname == "SiPM-mass-test-results.xlsx":
                    for col in ["Result", "Result_Err", "Strip_Avg_Result"]:
                        if col in new_df.columns:
                            new_df[col] = 0
                elif fname == "Dark-noise-SiPM-counts.xlsx":
                    for col in ["OV", "Counts"]:
                        if col in new_df.columns:
                            new_df[col] = 0

                # Append new rows to existing dataframe and sort by ID
                combined = pd.concat([df, new_df], ignore_index=True)
                sort_col = df.columns[id_col_idxs[0]]
                combined['_sort_key'] = pd.to_numeric(combined[sort_col], errors='coerce')
                combined = combined.sort_values(by='_sort_key').drop(columns=['_sort_key']).reset_index(drop=True)
                # Regenerate SiPM_Location for the entire file to guarantee correct
                # 0,1,2,3,4,5 cycling (fixes corruption from fix_empty_cells fillna(0))
                if 'SiPM_Location' in combined.columns:
                    combined['SiPM_Location'] = [i % 6 for i in range(len(combined))]
                combined.to_excel(os.path.join(tray_path, fname), index=False)

                ids_str = ", ".join(sorted(missing_ids))
                print(f"[FIX] {tray_folder}/{fname}: Added {len(missing_ids)} missing strip(s): {ids_str}")


if __name__ == "__main__":
    fix_missing_ids()
