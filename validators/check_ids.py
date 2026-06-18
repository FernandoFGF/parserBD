import os
import re
import pandas as pd
import pickle

INDEX_FILENAME = "index.pkl"

# --- coincident_ID functions ---

def verify_ids_in_tray(tray_path):
    files = [f for f in os.listdir(tray_path) if f.endswith('.xlsx') and not f.startswith('~$')]
    ids_per_file = {}

    for file in files:
        path = os.path.join(tray_path, file)
        try:
            df = pd.read_excel(path)
            ids = set()

            if file == "SiPM-item-manifest.xlsx":
                columns = []
                if df.shape[1] > 4:
                    columns.append(df.iloc[:, 4])
                if df.shape[1] > 9:
                    columns.append(df.iloc[:, 9])
                for col in columns:
                    ids.update(col.dropna().astype(str).tolist())
            else:
                col = df.iloc[:, 0]
                ids.update(col.dropna().astype(str).tolist())

            ids_per_file[file] = ids

        except Exception as e:
            print(f"Error processing '{file}' in {tray_path}: {e}")

    errors = False
    if not ids_per_file:
        print(f"\n[WARNING] No valid files found in {os.path.basename(tray_path)}.")
        return

    reference_name, reference_ids = list(ids_per_file.items())[0]

    if len(reference_ids) != 20:
        print(f"\n[ERROR] '{os.path.basename(tray_path)}': file '{reference_name}' has {len(reference_ids)} distinct IDs. Expected exactly 20.")
        errors = True

    for file, ids in ids_per_file.items():
        if ids != reference_ids:
            errors = True
            extra_ids = ids - reference_ids
            missing_ids = reference_ids - ids
            print(f"\n[ERROR] '{os.path.basename(tray_path)}': file '{file}' does not contain the exact same 20 IDs:")
            if missing_ids:
                print(f" - Missing: {sorted(missing_ids)}")
            if extra_ids:
                print(f" - Extra: {sorted(extra_ids)}")

    if not errors:
        print(f"\n[OK] '{os.path.basename(tray_path)}': All files contain the exact same 20 IDs.")

def check_coincident_ids(base_dir=None):
    if base_dir is None:
        base_dir = os.getcwd()

    box_folders = [os.path.join(base_dir, d) for d in os.listdir(base_dir) if os.path.isdir(os.path.join(base_dir, d)) and d.startswith('Box')]

    if not box_folders:
        print("No 'Box**' folders found in the directory.")
    else:
        for box_path in sorted(box_folders):
            tray_subfolders = [os.path.join(box_path, t) for t in os.listdir(box_path) if os.path.isdir(os.path.join(box_path, t)) and t.startswith('Tray')]
            if not tray_subfolders:
                print(f"\n[WARNING] No 'Tray******' folders found in {os.path.basename(box_path)}.")
            else:
                for tray_path in sorted(tray_subfolders):
                    verify_ids_in_tray(tray_path)

# --- find_all_ID functions ---

def create_index(base_path):
    index = {}
    tray_pattern = re.compile(r"^Tray\d{6}$")
    for root, dirs, files in os.walk(base_path):
        if any(file in files for file in ["IV-SiPM-characterization.xlsx", "SiPM-mass-test-results.xlsx"]):
            tray_folder = os.path.basename(root)
            box_folder = os.path.basename(os.path.dirname(root))
            
            # Only index valid Tray folders to ignore backups or old folder structures
            if not tray_pattern.match(tray_folder):
                continue
                
            for file in ["IV-SiPM-characterization.xlsx", "SiPM-mass-test-results.xlsx"]:
                file_path = os.path.join(root, file)
                if os.path.exists(file_path):
                    try:
                        df = pd.read_excel(file_path, usecols=[0], dtype=str)
                        values = set(df.iloc[:, 0].dropna().astype(str))
                        index[(box_folder, tray_folder, file_path)] = values
                    except Exception as e:
                        print(f"Error reading {file_path}: {e}")

    with open(INDEX_FILENAME, "wb") as f:
        pickle.dump(index, f)
    
    return index

def load_index():
    if os.path.exists(INDEX_FILENAME):
        try:
            with open(INDEX_FILENAME, "rb") as f:
                return pickle.load(f)
        except:
            return None
    return None

def search_in_index(index, number):
    results = []
    number_str = str(number)
    for (box, tray, file_path), values in index.items():
        if number_str in values:
            results.append((box, tray, file_path))
    return results

def read_20_ids_from_manifest(manifest_path):
    try:
        df = pd.read_excel(manifest_path, usecols=[4])
        numbers = df.iloc[:, 0].dropna().astype(str).tolist()[:20]
        return numbers
    except Exception as e:
        print(f"Error reading {manifest_path}: {e}")
        return []

def find_all_ids(base_dir=None):
    if base_dir is None:
        base_dir = os.getcwd()
    
    index = load_index()
    if index is None:
        print("Index not found or could not be loaded. Creating a new one...")
        index = create_index(base_dir)
    else:
        print("Index loaded successfully. Fast searches ready.")

    box_pattern = re.compile(r"^Box\d{2}$")
    tray_pattern = re.compile(r"^Tray\d{6}$")

    for box_folder in os.listdir(base_dir):
        if box_pattern.match(box_folder):
            box_path = os.path.join(base_dir, box_folder)
            if not os.path.isdir(box_path):
                continue
            
            for tray_folder in os.listdir(box_path):
                if tray_pattern.match(tray_folder):
                    tray_path = os.path.join(box_path, tray_folder)
                    if not os.path.isdir(tray_path):
                        continue

                    manifest_path = os.path.join(tray_path, "SiPM-item-manifest.xlsx")
                    if not os.path.exists(manifest_path):
                        continue

                    numbers = read_20_ids_from_manifest(manifest_path)
                    if not numbers:
                        continue

                    found_outside = False
                    for number in numbers:
                        results = search_in_index(index, number)
                        locations_found = set( (b, t) for (b, t, _) in results )
                        
                        for (b, t) in locations_found:
                            if (b, t) != (box_folder, tray_folder):
                                found_outside = True
                                print(f"ID {number} is found both in Tray {tray_folder} of {box_folder} "
                                      f"and in Tray {t} of {b}.")

                    if not found_outside:
                        print(f"All IDs from Tray {tray_folder} of {box_folder} are contained only in this tray.")
