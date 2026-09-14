import os

from main import process_box


if __name__ == "__main__":
    script_dir = os.path.dirname(os.path.abspath(__file__))

    print("=" * 50)
    print(" auto.py - SiPM Data Tools")
    print("=" * 50)

    process_box()
