import os
import re

# Base path
base_path = os.path.dirname(os.path.abspath(__file__))

# Regular expressions for Box** and Tray******
box_pattern = r"^Box\d{2}$"  
tray_pattern = r"^Tray\d{6}$"

# Patterns for LN2
LN2_folder_patterns = {
    "LN2_forward": r"^LN2_f_IV_(?:HPK|FBK)_standard_LN2T_(\d{2}_\d{2}_\d{4}-\d{1,2}_\d{2})$",
    "LN2_reverse": r"^LN2_r_IV_(?:HPK|FBK)_standard_LN2T_(\d{2}_\d{2}_\d{4}-\d{1,2}_\d{2})$",
}
LN2_file_patterns = {
    "LN2_forward": r"^LN2_f_Tray\d{6}_(\d{2}_\d{2}_\d{4}-\d{1,2}_\d{2})\.txt$",
    "LN2_reverse": r"^LN2_r_Tray\d{6}_(\d{2}_\d{2}_\d{4}-\d{1,2}_\d{2})\.txt$",
}

# Patterns for ROOMT
ROOMT_folder_patterns = {
    "ROOMT_forward": r"^room_f_IV_(?:HPK|FBK)_standard_roomT_(\d{2}_\d{2}_\d{4}-\d{1,2}_\d{2})$",
    "ROOMT_reverse": r"^room_r_IV_(?:HPK|FBK)_standard_roomT_(\d{2}_\d{2}_\d{4}-\d{1,2}_\d{2})$",
}
ROOMT_file_patterns = {
    "ROOMT_forward": r"^room_f_Tray\d{6}_(\d{2}_\d{2}_\d{4}-\d{1,2}_\d{2})\.txt$",
    "ROOMT_reverse": r"^room_r_Tray\d{6}_(\d{2}_\d{2}_\d{4}-\d{1,2}_\d{2})\.txt$",
}

def check_matches(box_name, tray_name, tray_path):
    """
    Verifies:
      1. LN2: First_Cycle and Third_Cycle subfolders, looking for LN2_f / LN2_r.
         Compares folder date vs .txt file date,
         and also compares the first cycle date vs third cycle date.
      2. ROOMT: 'ROOMT' subfolder (without cycle subfolders).
         Compares folder date vs .txt file date for room_f / room_r,
         but WITHOUT comparing 1st vs 3rd cycle.

    Returns:
        (errors, warnings): tuple of lists. errors = real date mismatches.
        warnings = only time mismatches (same date, different time).
    """
    errors = []
    warnings = []

    def _time_only_mismatch(date1, date2):
        """Return True if same date (DD_MM_YYYY) but different time (HH_MM)."""
        parts1 = date1.split("-")
        parts2 = date2.split("-")
        if len(parts1) != 2 or len(parts2) != 2:
            return False
        date_part1, time_part1 = parts1
        date_part2, time_part2 = parts2
        return date_part1 == date_part2 and time_part1 != time_part2

    # 1) LN2 PROCESS (with First_Cycle and Third_Cycle)
    cycle_dates = {}
    cycles = ["First_Cycle", "Third_Cycle"]
    ln2_base_path = os.path.join(tray_path, "LN2")

    if os.path.exists(ln2_base_path):
        for cycle_name in cycles:
            cycle_path = os.path.join(ln2_base_path, cycle_name)
            if not os.path.exists(cycle_path):
                continue

            for root, dirs, _ in os.walk(cycle_path):
                for folder in dirs:
                    for key, folder_pattern in LN2_folder_patterns.items():
                        folder_match = re.match(folder_pattern, folder)
                        if folder_match:
                            folder_date = folder_match.group(1)
                            folder_path = os.path.join(root, folder)

                            for file in os.listdir(folder_path):
                                file_pattern = LN2_file_patterns[key]
                                file_match = re.match(file_pattern, file)
                                if file_match:
                                    file_date = file_match.group(1)
                                    if folder_date == file_date:
                                        cycle_dates.setdefault((key, cycle_name), []).append(file_date)
                                    elif _time_only_mismatch(folder_date, file_date):
                                        warnings.append(
                                            f"[TS_DIFF] .txt '{file}' ({key}, {cycle_name}): time {file_date.split('-')[1]} vs folder {folder_date.split('-')[1]}."
                                        )
                                    else:
                                        errors.append(
                                            f"Mismatch between .txt '{file}' ({key}, {cycle_name}) and folder '{folder}'."
                                        )


    # 2) ROOMT PROCESS
    roomt_path = os.path.join(tray_path, "ROOMT")
    if os.path.exists(roomt_path):
        for root, dirs, _ in os.walk(roomt_path):
            for folder in dirs:
                for key, folder_pattern in ROOMT_folder_patterns.items():
                    folder_match = re.match(folder_pattern, folder)
                    if folder_match:
                        folder_date = folder_match.group(1)
                        folder_path = os.path.join(root, folder)

                        for file in os.listdir(folder_path):
                            file_pattern = ROOMT_file_patterns[key]
                            file_match = re.match(file_pattern, file)
                            if file_match:
                                file_date = file_match.group(1)
                                if folder_date != file_date:
                                    if _time_only_mismatch(folder_date, file_date):
                                        warnings.append(
                                            f"[TS_DIFF] .txt '{file}' ({key}): time {file_date.split('-')[1]} vs folder {folder_date.split('-')[1]}."
                                        )
                                    else:
                                        errors.append(
                                            f"Mismatch between .txt '{file}' ({key}) and folder '{folder}'."
                                        )

    # 3) Show results if there are messages
    if errors or warnings:
        print(f"In folder '{tray_name}' of {box_name}:")
        for msg in errors:
            print(" -", msg)
        for msg in warnings:
            print(" -", msg)
        print()

    return errors, warnings

def check_dates(base_path=None):
    if base_path is None:
        base_path = os.path.dirname(os.path.abspath(__file__))

    all_errors = []
    all_warnings = []

    # SEARCH FOR Box** and Tray******
    for item in os.listdir(base_path):
        if re.match(box_pattern, item):
            box_path = os.path.join(base_path, item)
            if os.path.isdir(box_path):
                for subitem in os.listdir(box_path):
                    if re.match(tray_pattern, subitem):
                        tray_path = os.path.join(box_path, subitem)
                        if os.path.isdir(tray_path):
                            errors, warnings = check_matches(item, subitem, tray_path)
                            all_errors.extend(errors)
                            all_warnings.extend(warnings)

    return all_errors, all_warnings

if __name__ == "__main__":
    check_dates()
