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
    """
    messages = []

    # 1) LN2 PROCESS (with First_Cycle and Third_Cycle)
    cycle_dates = {}  # will store dates for LN2_forward / LN2_reverse in first and third cycle
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
                                    else:
                                        messages.append(
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
                                    messages.append(
                                        f"Mismatch between .txt '{file}' ({key}) and folder '{folder}'."
                                    )

    # 3) Show results if there are messages
    if messages:
        print(f"In folder '{tray_name}' of {box_name}:")
        for msg in messages:
            print(" -", msg)
        print()

def check_dates(base_path=None):
    if base_path is None:
        base_path = os.path.dirname(os.path.abspath(__file__))

    # SEARCH FOR Box** and Tray******
    for item in os.listdir(base_path):
        if re.match(box_pattern, item):
            box_path = os.path.join(base_path, item)
            if os.path.isdir(box_path):
                for subitem in os.listdir(box_path):
                    if re.match(tray_pattern, subitem):
                        tray_path = os.path.join(box_path, subitem)
                        if os.path.isdir(tray_path):
                            check_matches(item, subitem, tray_path)

if __name__ == "__main__":
    check_dates()
