import os
import re
import pandas as pd

def check_consecution(excel_path, sheet_name, column_name, limit=None):
    """
    Reads 'excel_path' and verifies the consecution of the specified column.
    Returns (True, "OK") if everything is correct, or (False, error_message) if it fails.
    """
    try:
        df = pd.read_excel(excel_path, sheet_name=sheet_name)
    except Exception as e:
        return False, f"Error reading file: {e}"

    if column_name not in df.columns:
        return False, f"Column '{column_name}' not found in {os.path.basename(excel_path)}."

    # Limit rows if applicable
    if limit:
        df = df.iloc[:limit]

    # Get numeric values from the column
    column_values = df[column_name].dropna().astype(int).tolist()

    # Verify consecution
    expected = 0
    for i, value in enumerate(column_values, start=1):
        if value != expected:
            return (False,
                    f"Consecution broken (expected: {expected}, found: {value}) at row {i - 1}.")
        # Increment and reset to 0 if it exceeds 5
        expected = (expected + 1) % 6

    return True, "OK"

def check_sipm_location(base_dir=None):
    """
    1) Searches for Box## folders in the current directory (or base_dir).
    2) Inside each Box##, searches for Tray****** folders.
    3) If it finds 'SiPM-mass-test-results.xlsx' or 'IV-SiPM-characterization.xlsx',
       verifies the 'SiPM_Location' column and prints the result.
    """
    if base_dir is None:
        base_dir = os.getcwd()

    # Regular expressions for Box## and Tray******
    box_pattern = re.compile(r"^Box\d{2}$")
    tray_pattern = re.compile(r"^Tray\d{6}$")

    # Iterate over folders matching Box##
    for box_folder in os.listdir(base_dir):
        box_path = os.path.join(base_dir, box_folder)
        if os.path.isdir(box_path) and box_pattern.match(box_folder):
            
            # Inside Box##, search for Tray******
            for tray_folder in os.listdir(box_path):
                tray_path = os.path.join(box_path, tray_folder)
                if os.path.isdir(tray_path) and tray_pattern.match(tray_folder):

                    # Construct paths for each file
                    mass_file = os.path.join(tray_path, "SiPM-mass-test-results.xlsx")
                    char_file = os.path.join(tray_path, "IV-SiPM-characterization.xlsx")

                    found_any = False

                    # 1) If mass_file exists, check consecution
                    if os.path.exists(mass_file):
                        success, message = check_consecution(
                            excel_path=mass_file,
                            sheet_name=0,
                            column_name="SiPM_Location",
                            limit=720
                        )
                        if success:
                            print(f"{box_folder}/{tray_folder}: [SiPM-mass-test-results.xlsx] => OK")
                        else:
                            print(f"{box_folder}/{tray_folder}: [SiPM-mass-test-results.xlsx] => {message}")
                        found_any = True

                    # 2) If char_file exists, check consecution
                    if os.path.exists(char_file):
                        success, message = check_consecution(
                            excel_path=char_file,
                            sheet_name=0,
                            column_name="SiPM_Location",
                            limit=None
                        )
                        if success:
                            print(f"{box_folder}/{tray_folder}: [IV-SiPM-characterization.xlsx] => OK")
                        else:
                            print(f"{box_folder}/{tray_folder}: [IV-SiPM-characterization.xlsx] => {message}")
                        found_any = True

                    if not found_any:
                        print(f"{box_folder}/{tray_folder}: Required files not found.")

if __name__ == "__main__":
    check_sipm_location()
