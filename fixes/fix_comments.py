import os
import re
import pandas as pd


def clear_comments(base_dir=None):
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

            for fname in files_to_check:
                fpath = os.path.join(tray_path, fname)
                if not os.path.exists(fpath):
                    continue

                try:
                    df = pd.read_excel(fpath)
                    if 'Comment' not in df.columns:
                        continue
                    if df['Comment'].isna().all():
                        continue

                    df['Comment'] = None
                    df.to_excel(fpath, index=False)
                    print(f"[FIX] {tray_folder}/{fname}: Cleared Comment column.")

                except Exception as e:
                    print(f"[Error] {tray_folder}/{fname}: {e}")


if __name__ == "__main__":
    clear_comments()
