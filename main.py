import os
import sys
import shutil
import io
import re
import zipfile
import pandas as pd

from config import VENDOR_DELIVERY_ID
from fixes import fix_noise_floats, fix_daq_errors, fix_empty_cells, fix_missing_iv_rows, fix_manifest, fix_missing_ids, fix_hpk_prefix, fix_comments
from validators import check_sequence, check_dates, check_means, check_ids


def process_box():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    input_dir = os.path.join(script_dir, 'input')
    output_dir = os.path.join(script_dir, 'output')

    if not os.path.exists(input_dir):
        os.makedirs(input_dir)
    if os.path.exists(output_dir):
        shutil.rmtree(output_dir)
    os.makedirs(output_dir)
    open(os.path.join(output_dir, '.gitkeep'), 'a').close()

    # Find Box folders in input
    box_folders = [f for f in os.listdir(input_dir)
                   if os.path.isdir(os.path.join(input_dir, f)) and f.startswith('Box')]

    if not box_folders:
        print("No Box folder found in the 'input/' directory.")
        print("Place exactly ONE Box folder (e.g. Box05) inside 'input/' and run again.")
        return

    # Filter by VENDOR_BOX_NUMBER from config (match numerically, so Box05 matches 5)
    import config
    import re
    target_box_num = config.VENDOR_BOX_NUMBER
    box_folders = [
        f for f in box_folders
        if (m := re.match(r'^Box(\d+)$', f)) and int(m.group(1)) == target_box_num
    ]

    if not box_folders:
        print(f"No Box folder found for number {config.VENDOR_BOX_NUMBER} in the 'input/' directory.")
        print(f"Expected a folder like Box{config.VENDOR_BOX_NUMBER:02d} or Box{config.VENDOR_BOX_NUMBER} (based on VENDOR_BOX_NUMBER = {config.VENDOR_BOX_NUMBER})")
        print(f"Available folders: {[f for f in os.listdir(input_dir) if os.path.isdir(os.path.join(input_dir, f)) and f.startswith('Box')]}")
        return

    box = box_folders[0]
    src_box = os.path.join(input_dir, box)
    print(f"==================================================")
    print(f" SiPM Data Tools - Processing: {box}")
    print(f"==================================================\n")

    # --- STEP 1: Copy box to a temp dir and extract ZIPs ---
    temp_dir = os.path.join(output_dir, '.temp_processing')
    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir)
    os.makedirs(temp_dir)

    temp_box = os.path.join(temp_dir, box)
    shutil.copytree(src_box, temp_box)

    # Extract ZIPs
    zip_files = [f for f in os.listdir(temp_box) if f.endswith('.zip')]
    if zip_files:
        print("   Extracting ZIP files...")
        for item in zip_files:
            zip_path = os.path.join(temp_box, item)
            try:
                with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                    roots = set(p.split('/')[0] for p in zip_ref.namelist())
                    has_tray_root = any(r.startswith('Tray') for r in roots)

                    if has_tray_root:
                        zip_ref.extractall(temp_box)
                    else:
                        match = re.search(r'Tray(\d+)', item, re.IGNORECASE)
                        if match:
                            tray_num = match.group(1).zfill(6)
                            target_tray_dir = os.path.join(temp_box, f"Tray{tray_num}")
                            os.makedirs(target_tray_dir, exist_ok=True)
                            zip_ref.extractall(target_tray_dir)
                        else:
                            zip_ref.extractall(temp_box)

                os.remove(zip_path)
            except Exception as e:
                print(f"   [Error] Could not extract {item}: {e}")

    # --- STEP 1.5: Flatten intermediate folders that wrap Tray dirs ---
    tray_pattern = re.compile(r"^Tray\d{6}$")
    # Walk the whole tree repeatedly until no nested trays remain
    changed = True
    while changed:
        changed = False
        for root, dirs, _files in os.walk(temp_box, topdown=False):
            for d in dirs:
                if tray_pattern.match(d):
                    parent = os.path.basename(root)
                    if parent == os.path.basename(temp_box):
                        continue  # already at top level
                    src = os.path.join(root, d)
                    dest = os.path.join(temp_box, d)
                    if not os.path.exists(dest):
                        shutil.move(src, dest)
                    else:
                        # Merge: move contents from nested tray into existing one
                        for item in os.listdir(src):
                            shutil.move(os.path.join(src, item), os.path.join(dest, item))
                        shutil.rmtree(src)
                    changed = True
            # Remove empty intermediate folders (bottom-up)
            if root != temp_box and not os.listdir(root):
                shutil.rmtree(root)
                changed = True

    # --- STEP 2: Find all Tray folders ---
    tray_folders = sorted([f for f in os.listdir(temp_box)
                           if os.path.isdir(os.path.join(temp_box, f)) and tray_pattern.match(f)])

    if not tray_folders:
        print(f"[WARNING] No 'Tray******' folders found in {box} after extraction.")
        shutil.rmtree(temp_dir)
        return

    print(f"   Found {len(tray_folders)} trays: {tray_folders[0]} ... {tray_folders[-1]}\n")

    # --- STEP 3: Global log (reset each run) ---
    global_log_path = os.path.join(output_dir, "global_validation_log.md")
    global_log = open(global_log_path, "w", encoding="utf-8")
    global_log.write(f"# Validation & Fix Log for {box}\n\n")
    global_log.write("Only showing applied fixes and actual errors.\n\n")

    exported_count = 0
    error_count = 0
    important_fix_trays = []

    # --- STEP 4: Process each tray individually ---
    
    # Create global index of all IDs in the Box before processing in isolated sandboxes
    print("   Building global ID index for cross-tray duplicate checking...")
    check_ids.create_index(temp_box)
    
    for tray in tray_folders:
        tray_src = os.path.join(temp_box, tray)

        # Create a mini-environment that looks like Box##/Tray****** for the validators
        tray_sandbox = os.path.join(temp_dir, '_sandbox')
        if os.path.exists(tray_sandbox):
            shutil.rmtree(tray_sandbox)
        os.makedirs(tray_sandbox)

        sandbox_box = os.path.join(tray_sandbox, box)
        os.makedirs(sandbox_box)
        # Copy this single tray into the sandbox
        shutil.copytree(tray_src, os.path.join(sandbox_box, tray))

        # Capture stdout for this tray
        log_stream = io.StringIO()
        old_stdout = sys.stdout

        print(f" > Processing {tray}...", end=" ")

        date_warnings = []

        try:
            sys.stdout = log_stream

            # -- FIXES (run on the sandbox which has Box##/Tray##) --
            fix_noise_floats.fix_noise_floats(tray_sandbox)
            fix_daq_errors.add_blank_rows(tray_sandbox)
            fix_empty_cells.fill_empty_cells(tray_sandbox)
            fix_missing_iv_rows.fix_missing_iv_rows(tray_sandbox)
            fix_manifest.fix_manifest(tray_sandbox)
            fix_missing_ids.fix_missing_ids(tray_sandbox)
            fix_hpk_prefix.fix_hpk_prefix(tray_sandbox)
            fix_comments.clear_comments(tray_sandbox)

            # -- VALIDATORS --
            check_sequence.check_sipm_location(tray_sandbox)
            date_errors, date_warnings = check_dates.check_dates(tray_sandbox)
            check_means.check_means(tray_sandbox)
            check_ids.find_all_ids(tray_sandbox)
            check_ids.check_coincident_ids(tray_sandbox)

            # Append date errors to log for this tray
            for de in date_errors:
                log_stream.write(de + "\n")

        except Exception as e:
            log_stream.write(f"\n[CRITICAL ERROR] {e}\n")

        finally:
            sys.stdout = old_stdout
            log_content = log_stream.getvalue()

        # --- Filter output for this tray ---
        filtered_lines = []
        for line in log_content.splitlines():
            line_str = line.strip()
            if not line_str:
                continue

            # Skip noise
            if "File not found" in line_str: continue
            if "No se encontró el archivo" in line_str: continue
            if line_str == "Code execution finished.": continue
            if "Index not found" in line_str: continue
            if "Index loaded successfully" in line_str: continue
            if "All correct in every Tray" in line_str: continue
            if "[OK]" in line_str: continue
            if "All IDs from Tray" in line_str: continue
            if line_str.startswith("Verification of"): continue
            if line_str == "--------------------": continue
            if "=> OK" in line_str: continue
            if "processed." in line_str: continue
            if "Processing file in" in line_str: continue
            if "[TS_DIFF]" in line_str: continue

            filtered_lines.append(line)

        # Split fixes into important vs cosmetic
        important_keywords = ["Added", "Inserted"]
        exclude_keywords = ["I_Rel_Diff"]
        important_lines = [
            fl for fl in filtered_lines
            if any(kw in fl for kw in important_keywords)
            and not any(ek in fl for ek in exclude_keywords)
        ]
        not_important_lines = [fl for fl in filtered_lines if fl not in important_lines]
        if important_lines:
            important_fix_trays.append(tray)

        # --- Decide export ---
        error_keywords = ["Mismatch", "Incorrect", "[WARNING]", "[ERROR]",
                          "No match", "Consecution broken", "La ID", "CRITICAL"]
        has_errors = any(
            any(kw in fl for kw in error_keywords) for fl in filtered_lines
        )

        if has_errors:
            print("ERRORS FOUND - exported as-is.")
            tray_checked_name = f"{tray}_checked"
            final_tray_path = os.path.join(output_dir, tray_checked_name)
            if os.path.exists(final_tray_path):
                shutil.rmtree(final_tray_path)
            shutil.copytree(tray_src, final_tray_path)
            global_log.write(f"## {tray} — ❌ EXPORTED WITH ERRORS\n\n")
            if important_lines:
                global_log.write("**IMPORTANT:**\n")
                for fl in important_lines:
                    global_log.write(f"- {fl}\n")
            if not_important_lines:
                global_log.write("**NOT IMPORTANT:**\n")
                for fl in not_important_lines:
                    global_log.write(f"- {fl}\n")
            if date_warnings:
                global_log.write("**TIMESTAMP WARNINGS (not blocking):**\n")
                for tw in date_warnings:
                    global_log.write(f"- {tw}\n")
            global_log.write("\n")
            error_count += 1
        else:
            # Export the tray
            tray_checked_name = f"{tray}_checked"
            final_tray_path = os.path.join(output_dir, tray_checked_name)
            if os.path.exists(final_tray_path):
                shutil.rmtree(final_tray_path)
            shutil.move(os.path.join(sandbox_box, tray), final_tray_path)

            if filtered_lines:
                print("OK (fixes applied).")
                global_log.write(f"## {tray} — ⚠️ EXPORTED WITH FIXES\n\n")
                if important_lines:
                    global_log.write("**IMPORTANT:**\n")
                    for fl in important_lines:
                        global_log.write(f"- {fl}\n")
                if not_important_lines:
                    global_log.write("**NOT IMPORTANT:**\n")
                    for fl in not_important_lines:
                        global_log.write(f"- {fl}\n")
                global_log.write("\n")
            else:
                print("OK.")
                global_log.write(f"## {tray} — ✅ EXPORTED\n\n")

            if date_warnings:
                global_log.write("**TIMESTAMP WARNINGS (not blocking):**\n")
                for tw in date_warnings:
                    global_log.write(f"- {tw}\n")
                global_log.write("\n")

            exported_count += 1

        # Clean sandbox
        if os.path.exists(tray_sandbox):
            shutil.rmtree(tray_sandbox)

    # --- STEP 7: Cleanup temp ---
    global_log.close()
    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir)
    if os.path.exists("index.pkl"):
        os.remove("index.pkl")

    print(f"\n==================================================")
    print(f" Results: {exported_count} trays OK, {error_count} trays with errors.")
    if important_fix_trays:
        print(f" Review log for: {', '.join(important_fix_trays)}")

    # --- STEP 8: Determine vendor folder ---
    if VENDOR_DELIVERY_ID.startswith("FBK"):
        vendor_folder = "FBK"
    elif VENDOR_DELIVERY_ID.startswith("HPK_CIEMAT"):
        vendor_folder = "HPK_CIEMAT"
    elif VENDOR_DELIVERY_ID.startswith("HPK_INFN"):
        vendor_folder = "HPK_INFN"
    else:
        print(f" Unknown VENDOR_DELIVERY_ID: {VENDOR_DELIVERY_ID}")
        print(f" Results left in output/ for manual placement.")
        print(f"==================================================")
        return

    # --- STEP 9: Always move output to checked/<vendor>/ (even with errors) ---
    total_trays = exported_count + error_count
    if total_trays > 0:
        checked_dir = os.path.join(script_dir, 'checked', vendor_folder)
        os.makedirs(checked_dir, exist_ok=True)

        dest_path = os.path.join(checked_dir, f"{box}_checked")
        if os.path.exists(dest_path):
            shutil.rmtree(dest_path)
        shutil.move(output_dir, dest_path)

        os.makedirs(output_dir)

        print(f" Saved to: checked/{vendor_folder}/{box}_checked")
    else:
        print(f" No trays exported. Log saved to: output/global_validation_log.md")

    print(f"==================================================")


if __name__ == "__main__":
    process_box()
