# config.py
# ==========================================
# MANIFEST SETTINGS
# ==========================================
# Put here the EXACT text that must appear in each
# column of SiPM-item-manifest.xlsx.
# If the manifest doesn't match, the tool will overwrite it.

# Vendor (e.g. 'FBK', 'Hamamatsu')
VENDOR = "Hamamatsu"

# Vendor_Delivery_ID (e.g. 'FBK_ciemat_4', 'HPK_CIEMAT_08')
VENDOR_DELIVERY_ID = "HPK_CIEMAT_7"

# Vendor_Box_Number (e.g. 5, 14) — auto-detected from folder name
VENDOR_BOX_NUMBER = 33

# Test_Box_ID (e.g. 'Gra5', 'Gra14')
TEST_BOX_ID = "Gra4"

# Institution (e.g. '(99) University of Granada & CAFPE')
INSTITUTION = "(99) University of Granada & CAFPE"

# ==========================================
# REMOTE SSH SETTINGS
# ==========================================
# If empty/None, remote copy is skipped.
SSH_REMOTE_HOST = ""
SSH_REMOTE_PORT = 22
SSH_USERNAME = ""
SSH_PASSWORD = ""
SSH_REMOTE_PATH = ""
