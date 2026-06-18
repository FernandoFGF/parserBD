import os
import re
import pandas as pd
import numpy as np

# Define the ranges
ranges = [0, 120, 240, 360, 480, 600, 720, 840]

box_pattern = re.compile(r"^Box\d{2}$")
tray_pattern = re.compile(r"^Tray\d{6}$")

def check_means(base_dir=None):
    if base_dir is None:
        base_dir = os.getcwd()

    for box_folder in os.listdir(base_dir):
        box_path = os.path.join(base_dir, box_folder)
        if os.path.isdir(box_path) and box_pattern.match(box_folder):
                
            for tray_folder in os.listdir(box_path):
                tray_path = os.path.join(box_path, tray_folder)
                if os.path.isdir(tray_path) and tray_pattern.match(tray_folder):

                    file_path = os.path.join(tray_path, 'SiPM-mass-test-results.xlsx')

                    if not os.path.exists(file_path):
                        print(f"File not found in: {tray_folder} of {box_folder}, skipping this folder.")
                        continue

                    print(f"Processing file in: {tray_folder} of {box_folder}")

                    try:
                        data = pd.read_excel(file_path)
                    except Exception as e:
                        print(f"Error reading {file_path}: {e}")
                        continue

                    SiPM_Strip_ID = data.iloc[:, 0]        # First column
                    Result = data.iloc[:, 10]              # Column 11 (index 10)
                    Strip_Avg_Result = data.iloc[:, 12]    # Column 13 (index 12)

                    for r in range(len(ranges) - 1):
                        start_idx = ranges[r]
                        end_idx = ranges[r + 1]
            
                        for k in range(start_idx, end_idx):
                            total = 0
                            medium = []
                
                            for j in range(start_idx, end_idx):
                                if k < len(SiPM_Strip_ID) and j < len(SiPM_Strip_ID):
                                    if SiPM_Strip_ID[k] == SiPM_Strip_ID[j]:
                                        total += Result[j]
                                        medium.append(Strip_Avg_Result[j])
                
                            medium_mean = round(np.mean(medium), 4) if medium else 0
                
                            if medium_mean == 0:
                                pass
                            elif medium_mean != round(total / 6, 4):
                                print(f'No match at row {k + 2} in {tray_folder} of {box_folder}')
                    
                    print(f'File in {tray_folder} of {box_folder} processed.\n')

    print('Code execution finished.')

if __name__ == "__main__":
    check_means()
