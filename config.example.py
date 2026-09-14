# config.example.py
# ==========================================
# CONFIGURATION TEMPLATE - SiPM Data Tools
# Copy to config.py and fill in with your batch data:
#   copy config.example.py config.py   (Windows)
#   cp config.example.py config.py     (Linux/Mac)
# config.py is NOT uploaded to git (see .gitignore).
# ==========================================

# --- MANIFEST SETTINGS ---
# EXACT text that must appear in each column of SiPM-item-manifest.xlsx.
# If the manifest does not match, the tool will overwrite it.

# Vendor: 'FBK' or 'Hamamatsu'/'HPK'
VENDOR = "FBK"

# Vendor_Delivery_ID (e.g. 'FBK_9', 'HPK_CIEMAT_08', 'HPK_INFN_15')
VENDOR_DELIVERY_ID = "FBK_9"

# Vendor_Box_Number (e.g. 5, 14) - used to filter which Box## folder to process
VENDOR_BOX_NUMBER = 16

# Test_Box_ID (e.g. 'Gra5', 'Gra16')
TEST_BOX_ID = "Gra16"

# Institution (e.g. '(99) University of Granada & CAFPE')
INSTITUTION = "(99) University of Granada & CAFPE"
