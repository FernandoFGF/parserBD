import os
import re
import sys
import argparse
import pandas as pd
import numpy as np
from collections import defaultdict

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

VENDOR_MAP = {
    "fbk": "FBK",
    "hpk_ciemat": "HPK_CIEMAT",
    "hpk_infn": "HPK_INFN",
}


# ── Helpers ─────────────────────────────────────────────────────

def extract_prefixes(series):
    prefixes = set()
    for val in series.dropna().astype(str):
        m = re.match(r'^([A-Za-z]+)', val)
        if m:
            prefixes.add(m.group(1))
    return prefixes


def read_manifest(tray_path):
    fp = os.path.join(tray_path, "SiPM-item-manifest.xlsx")
    if not os.path.exists(fp):
        return None
    try:
        return pd.read_excel(fp)
    except Exception:
        return None


def read_char(tray_path):
    fp = os.path.join(tray_path, "IV-SiPM-characterization.xlsx")
    if not os.path.exists(fp):
        return None
    try:
        return pd.read_excel(fp)
    except Exception:
        return None


def read_mass_test(tray_path):
    fp = os.path.join(tray_path, "SiPM-mass-test-results.xlsx")
    if not os.path.exists(fp):
        return None
    try:
        return pd.read_excel(fp)
    except Exception:
        return None


def read_noise(tray_path):
    fp = os.path.join(tray_path, "IV-SiPM-noise-test.xlsx")
    if not os.path.exists(fp):
        return None
    try:
        return pd.read_excel(fp)
    except Exception:
        return None


# ── Log Parser ──────────────────────────────────────────────────

def parse_log(log_path):
    sections = []
    current_tray = None
    current_is_important = False
    current_important = []
    current_not_important = []

    tray_pattern = re.compile(r"^## (Tray\d{6})")
    important_header = re.compile(r"^\*\*IMPORTANT:\*\*$")
    not_important_header = re.compile(r"^\*\*NOT IMPORTANT:\*\*$")

    with open(log_path, "r", encoding="utf-8") as f:
        for line in f:
            line_stripped = line.strip()
            m = tray_pattern.match(line_stripped)
            if m:
                if current_tray:
                    sections.append({
                        "tray": current_tray,
                        "important": list(current_important),
                        "not_important": list(current_not_important),
                    })
                current_tray = m.group(1)
                current_is_important = False
                current_important = []
                current_not_important = []
                continue

            if important_header.match(line_stripped):
                current_is_important = True
                continue
            if not_important_header.match(line_stripped):
                current_is_important = False
                continue

            if line_stripped.startswith("- [FIX]") or line_stripped.startswith("- [WARNING]") or line_stripped.startswith("- [ERROR]"):
                if current_is_important:
                    current_important.append(line_stripped)
                else:
                    current_not_important.append(line_stripped)

    if current_tray:
        sections.append({
            "tray": current_tray,
            "important": list(current_important),
            "not_important": list(current_not_important),
        })
    return sections


# ── Cross-Tray Collectors ──────────────────────────────────────

def collect_manifest_data(box_path, tray_list):
    data = {}
    for t in tray_list:
        tp = os.path.join(box_path, f"{t}_checked")
        df = read_manifest(tp)
        if df is None:
            data[t] = None
            continue
        info = {}
        for col in ["Vendor", "Vendor_Delivery_ID", "Vendor_Box_Number",
                     "Tray_Number", "Test_Box_ID", "Institution"]:
            if col in df.columns:
                vals = df[col].dropna().unique()
                info[col] = vals[0] if len(vals) == 1 else vals
            else:
                info[col] = None
        # Manufacturer consistency
        if "Manufacturer" in df.columns:
            info["Manufacturer"] = set(df["Manufacturer"].dropna().astype(str).str.strip())
        else:
            info["Manufacturer"] = set()
        # Serial_Number prefix check
        if "Serial_Number" in df.columns:
            info["Serial_Prefixes"] = extract_prefixes(df["Serial_Number"])
        else:
            info["Serial_Prefixes"] = set()
        # SiPM_Strip_ID prefix check from manifest
        if "SiPM_Strip_ID" in df.columns:
            info["StripID_Prefixes"] = extract_prefixes(df["SiPM_Strip_ID"])
        else:
            info["StripID_Prefixes"] = set()
        data[t] = info
    return data


def collect_prefix_data(box_path, tray_list):
    data = {}
    for t in tray_list:
        tp = os.path.join(box_path, f"{t}_checked")
        d = {"char": set(), "mass": set(), "manifest": set()}
        cdf = read_char(tp)
        if cdf is not None and "SiPM_Strip_ID" in cdf.columns:
            d["char"] = extract_prefixes(cdf["SiPM_Strip_ID"])
        mdf = read_mass_test(tp)
        if mdf is not None and "SiPM_Strip_ID" in mdf.columns:
            d["mass"] = extract_prefixes(mdf["SiPM_Strip_ID"])
        mf = read_manifest(tp)
        if mf is not None and "SiPM_Strip_ID" in mf.columns:
            d["manifest"] = extract_prefixes(mf["SiPM_Strip_ID"])
        data[t] = d
    return data


def collect_status_data(box_path, tray_list):
    data = {}
    for t in tray_list:
        tp = os.path.join(box_path, f"{t}_checked")
        cdf = read_char(tp)
        if cdf is not None and "Status" in cdf.columns:
            data[t] = set(cdf["Status"].dropna().astype(str).str.strip())
        else:
            data[t] = set()
    return data


def collect_row_counts(box_path, tray_list):
    data = {}
    files = ["IV-SiPM-characterization.xlsx", "SiPM-mass-test-results.xlsx",
             "IV-SiPM-noise-test.xlsx", "SiPM-item-manifest.xlsx"]
    for t in tray_list:
        tp = os.path.join(box_path, f"{t}_checked")
        counts = {}
        for fname in files:
            fp = os.path.join(tp, fname)
            if os.path.exists(fp):
                try:
                    df = pd.read_excel(fp)
                    counts[fname] = len(df)
                except Exception:
                    counts[fname] = None
            else:
                counts[fname] = None
        data[t] = counts
    return data


def check_row_count_consistency(row_count_data, tray_list):
    checks = []
    files = ["IV-SiPM-characterization.xlsx", "SiPM-mass-test-results.xlsx",
             "IV-SiPM-noise-test.xlsx", "SiPM-item-manifest.xlsx"]
    for fname in files:
        counts = {}
        for t, d in row_count_data.items():
            c = d.get(fname)
            if c is not None:
                counts[t] = c
        if not counts:
            continue
        # Find the majority count
        tally = defaultdict(int)
        for c in counts.values():
            tally[c] += 1
        majority_cnt = max(tally, key=tally.get)
        offenders = [(t, c) for t, c in counts.items() if c != majority_cnt]
        short_name = fname.replace("IV-SiPM-", "").replace("SiPM-", "").replace("-results", "")
        if not offenders:
            checks.append(("PASS", f"'{short_name}' row count consistent",
                          f"all={majority_cnt}"))
        else:
            detail = "; ".join(f"{t}={c}" for t, c in offenders)
            checks.append(("WARN", f"'{short_name}' row count differs",
                          f"expected {majority_cnt}, got: {detail}"))
    return checks


def collect_location_operator(box_path, tray_list):
    data = {}
    for t in tray_list:
        tp = os.path.join(box_path, f"{t}_checked")
        cdf = read_char(tp)
        if cdf is None:
            data[t] = None
            continue
        entry = {}
        if "Location" in cdf.columns:
            entry["Location"] = set(cdf["Location"].dropna().astype(str).str.strip())
        if "Operator" in cdf.columns:
            entry["Operator"] = set(cdf["Operator"].dropna().astype(str).str.strip())
        data[t] = entry
    return data


# ── Per-Tray Verifiers ─────────────────────────────────────────

def verify_tray_exists(tray_path):
    return os.path.isdir(tray_path)


def verify_noise_floats(tray_path):
    df = read_noise(tray_path)
    if df is None:
        return False, "IV-SiPM-noise-test.xlsx not found"
    for col in ["V_Range_Low", "V_Range_High"]:
        if col not in df.columns:
            return False, f"Column '{col}' not found"
        for i, val in enumerate(df[col]):
            s = str(val)
            if s in ("nan", ""):
                continue
            if not re.match(r'^\[[\d.,\s]*\]$', s.strip()):
                return False, f"Row {i+2}, col '{col}': '{s}' not valid noise float list"
    return True, "OK"


def verify_char_sequence(tray_path):
    df = read_char(tray_path)
    if df is None:
        return False, "IV-SiPM-characterization.xlsx not found"
    if "SiPM_Location" not in df.columns:
        return False, "Column 'SiPM_Location' not found"
    vals = df["SiPM_Location"].dropna().astype(int).tolist()
    expected = 0
    for i, v in enumerate(vals):
        if v != expected:
            return False, f"Broken at row {i+2}: expected {expected}, found {v}"
        expected = (expected + 1) % 6
    return True, f"OK ({len(vals)} rows, perfect 0-5 cycle)"


def verify_char_group_integrity(tray_path):
    df = read_char(tray_path)
    if df is None:
        return False, "File not found"
    group_cols = ["SiPM_Strip_ID", "Thermal_Cycle", "Polarization", "Temperature"]
    if not all(c in df.columns for c in group_cols):
        return True, "Skipped (group cols missing)"
    for name, group in df.groupby(group_cols, sort=False):
        locs = sorted(group["SiPM_Location"].dropna().astype(int).tolist())
        if locs != [0, 1, 2, 3, 4, 5]:
            return False, f"Group {name}: locations {locs} != [0-5]"
    n = len(df)
    return True, f"OK ({n} rows, {n//6} groups with 6 locations each)"


def verify_char_inserted_rows(tray_path, expected_inserted):
    df = read_char(tray_path)
    if df is None:
        return False, "File not found"
    failed = df[df["Status"].astype(str).str.strip() == "Failed"]
    ic = len(failed)
    if expected_inserted > 0 and ic == 0:
        return False, f"Expected {expected_inserted} Failed rows, found 0"
    if ic > 0:
        for _, row in failed.iterrows():
            loc = int(row["SiPM_Location"])
            if loc < 0 or loc > 5:
                return False, f"Invalid SiPM_Location={loc}"
            for c in ["V", "I", "I_Err"]:
                if str(row.get(c, "")) != "[0]":
                    return False, f"Inserted row has {c}='{row[c]}' not '[0]'"
    return True, f"OK ({ic} rows with Status='Failed')"


def verify_blanks_filled(tray_path, column, expected_rows):
    df = read_mass_test(tray_path)
    if df is None:
        return False, "SiPM-mass-test-results.xlsx not found"
    if column not in df.columns:
        return False, f"Column '{column}' not found"
    still_blank = df[column].isna().sum()
    bad = []
    for r in expected_rows:
        idx = r - 2
        if idx >= len(df):
            bad.append(r)
            continue
        val = df.iloc[idx][column]
        try:
            if pd.isna(val) or float(val) != 0.0:
                bad.append(r)
        except (ValueError, TypeError):
            bad.append(r)
    if still_blank > 0 or bad:
        return False, f"Column '{column}': {still_blank} blank, {len(bad)} rows not zero"
    return True, f"OK (all {len(expected_rows)} rows=0, no blanks)"


def verify_manifest(tray_path, tray):
    df = read_manifest(tray_path)
    if df is None:
        return False, "SiPM-item-manifest.xlsx not found"
    tray_num = int(tray.replace("Tray", ""))
    box_match = re.search(r"Box(\d+)", os.path.basename(os.path.dirname(tray_path)))
    box_num = int(box_match.group(1)) if box_match else None
    if box_num and "Vendor_Box_Number" in df.columns:
        for v in df["Vendor_Box_Number"].dropna():
            if int(v) != box_num:
                return False, f"Vendor_Box_Number mismatch"
    if "Tray_Number" in df.columns:
        for v in df["Tray_Number"].dropna():
            if int(v) != tray_num:
                return False, f"Tray_Number mismatch"
    return True, "OK"


def verify_mass_test_sequence(tray_path):
    df = read_mass_test(tray_path)
    if df is None:
        return False, "File not found"
    if "SiPM_Location" not in df.columns:
        return False, "Column not found"
    vals = df["SiPM_Location"].dropna().astype(int).tolist()[:720]
    expected = 0
    for i, v in enumerate(vals):
        if v != expected:
            return False, f"Broken at row {i+2}: expected {expected}, found {v}"
        expected = (expected + 1) % 6
    return True, "OK"


def verify_no_remaining_nans(tray_path):
    checks = {
        "SiPM-mass-test-results.xlsx": ["Result", "Result_Err", "Strip_Avg_Result"],
    }
    issues = []
    for fname, cols in checks.items():
        fp = os.path.join(tray_path, fname)
        if not os.path.exists(fp):
            continue
        df = pd.read_excel(fp)
        for col in cols:
            if col in df.columns:
                nans = df[col].isna().sum()
                if nans > 0:
                    issues.append(f"{fname}/{col}: {nans} NaN(s)")
    if issues:
        return False, "; ".join(issues)
    return True, "OK (no remaining NaNs)"


# ── Cross-Tray Checks ──────────────────────────────────────────

def check_manifest_consistency(manifest_data, tray_list):
    checks = []
    active = {t: d for t, d in manifest_data.items() if d is not None}
    if not active:
        return checks

    ref = list(active.values())[0]
    for col in ["Vendor", "Vendor_Delivery_ID", "Test_Box_ID", "Institution"]:
        ref_val = ref.get(col)
        if ref_val is None:
            continue
        offenders = []
        for t, d in active.items():
            v = d.get(col)
            if v != ref_val:
                offenders.append(f"{t}={v}")
        if offenders:
            checks.append(("FAIL", f"'{col}' inconsistency", f"{ref_val} expected, found: {', '.join(offenders)}"))
        else:
            checks.append(("PASS", f"'{col}' consistent", f"all={ref_val}"))

    # Manufacturer consistency
    ref_manu = ref.get("Manufacturer", set())
    if ref_manu:
        for t, d in active.items():
            m = d.get("Manufacturer", set())
            if m != ref_manu:
                checks.append(("WARN", f"'{t}' Manufacturer differs", f"{m} vs ref {ref_manu}"))
                break
        else:
            checks.append(("PASS", "Manufacturer consistent", f"all={ref_manu}"))

    return checks


def check_id_prefix_consistency(prefix_data, tray_list):
    checks = []
    active = {t: d for t, d in prefix_data.items()
              if d and any(v for v in d.values())}
    if not active:
        return checks

    all_prefixes = set()
    for t, d in active.items():
        for source in ["char", "mass", "manifest"]:
            all_prefixes |= d.get(source, set())

    if len(all_prefixes) <= 1:
        ref_p = list(all_prefixes)[0] if all_prefixes else "?"
        checks.append(("PASS", "SiPM_Strip_ID prefix consistent", f"all={ref_p}"))
        return checks

    # Multiple prefixes found — identify which trays are different
    ref_t = list(active.keys())[0]
    ref_prefixes = set()
    for source in ["char", "mass", "manifest"]:
        ref_prefixes |= active[ref_t].get(source, set())

    for t, d in active.items():
        t_prefixes = set()
        for source in ["char", "mass", "manifest"]:
            t_prefixes |= d.get(source, set())
        if t_prefixes != ref_prefixes:
            checks.append(("WARN", f"'{t}' prefix differs",
                          f"{t_prefixes} vs majority {ref_prefixes}"))
    if not any(c[0] == "WARN" for c in checks):
        checks.append(("PASS", "SiPM_Strip_ID prefix consistent (mixed)", f"all={all_prefixes}"))
    return checks


def check_delivery_id_format(manifest_data, tray_list):
    checks = []
    active = {t: d for t, d in manifest_data.items() if d is not None}
    if not active:
        return checks

    dids = {}
    for t, d in active.items():
        v = d.get("Vendor_Delivery_ID")
        if v is not None:
            v = str(v).strip()
            dids.setdefault(v, []).append(t)

    # Detect leading-zero inconsistency: e.g. HPK_CIEMAT_7 vs HPK_CIEMAT_07
    patterns = defaultdict(list)
    for did, trays in dids.items():
        # Normalise: remove leading zeros from last number segment
        norm = re.sub(r'(\D)(\d+)$', lambda m: m.group(1) + str(int(m.group(2))), did)
        patterns[norm].append((did, trays))

    if len(patterns) == 1:
        checks.append(("PASS", "Vendor_Delivery_ID format consistent", f"all={list(dids.keys())[0]}"))
    else:
        for norm, variants in patterns.items():
            for did, trays in variants:
                if len(variants) > 1:
                    checks.append(("WARN", f"Vendor_Delivery_ID '{did}' differs in format",
                                  f"{len(trays)} trays: {', '.join(trays[:5])}..."))
    return checks


def check_status_consistency(status_data, tray_list):
    checks = []
    active = {t: s for t, s in status_data.items() if s}
    if not active:
        return checks

    only_success = [t for t, s in active.items() if s == {"Success"}]
    with_failed = [t for t, s in active.items() if "Failed" in s]

    total = len(active)
    ok_count = len(only_success)
    fail_count = len(with_failed)

    if fail_count == 0:
        checks.append(("PASS", "Status consistent", f"all {ok_count}/{total} trays have only 'Success'"))
    else:
        checks.append(("INFO", f"Trays with 'Failed' status",
                      f"{fail_count}/{total}: {', '.join(with_failed)}"))
        checks.append(("PASS", "Status distribution OK", f"{ok_count} all-Success, {fail_count} with Failed"))

    return checks


def check_location_operator_consistency(locop_data, tray_list):
    checks = []
    active = {t: d for t, d in locop_data.items() if d}

    for attr in ["Location", "Operator"]:
        vals = {}
        for t, d in active.items():
            v = d.get(attr)
            if v:
                vals[t] = v
        if not vals:
            continue
        ref = list(vals.values())[0]
        all_same = all(v == ref for v in vals.values())
        if all_same:
            checks.append(("PASS", f"'{attr}' consistent", f"all={ref}"))
        else:
            offenders = [f"{t}={v}" for t, v in vals.items() if v != ref]
            checks.append(("WARN", f"'{attr}' varies", "; ".join(offenders)))

    return checks


# ── Main ────────────────────────────────────────────────────────

def run_verifications(box_path, box_name):
    log_path = os.path.join(box_path, "global_validation_log.md")
    if not os.path.exists(log_path):
        print(f"[ERROR] global_validation_log.md not found")
        return

    sections = parse_log(log_path)
    if not sections:
        print("[ERROR] No tray sections found in log")
        return

    tray_list = [s["tray"] for s in sections]

    # ── Collect cross-tray data ──
    manifest_data = collect_manifest_data(box_path, tray_list)
    prefix_data = collect_prefix_data(box_path, tray_list)
    status_data = collect_status_data(box_path, tray_list)
    locop_data = collect_location_operator(box_path, tray_list)
    row_count_data = collect_row_counts(box_path, tray_list)

    total_checks = 0
    passed_checks = 0
    failed_checks = 0
    warning_checks = 0
    info_checks = 0
    issues = []  # collect (type, label, detail) for summary

    print(f"{'='*70}")
    print(f" VERIFICATION REPORT — {box_name}")
    print(f" Path: {box_path}")
    print(f" Trays: {len(sections)}")
    print(f"{'='*70}")

    # ── CROSS-TRAY CHECKS ──
    print(f"\n{'-'*70}")
    print(" CROSS-TRAY CONSISTENCY CHECKS")
    print(f"{'-'*70}")

    for check_fn, title in [
        (check_manifest_consistency(manifest_data, tray_list), "Manifest"),
        (check_id_prefix_consistency(prefix_data, tray_list), "ID Prefix"),
        (check_delivery_id_format(manifest_data, tray_list), "Delivery ID Format"),
        (check_status_consistency(status_data, tray_list), "Status"),
        (check_location_operator_consistency(locop_data, tray_list), "Location/Operator"),
        (check_row_count_consistency(row_count_data, tray_list), "Row Counts"),
    ]:
        for status, label, msg in check_fn:
            total_checks += 1
            if status == "PASS":
                passed_checks += 1
                print(f"  [PASS] {label}: {msg}")
            elif status == "WARN":
                warning_checks += 1
                issues.append(("WARN", label, msg))
                print(f"  [WARN] {label}: {msg}")
            elif status == "INFO":
                info_checks += 1
                issues.append(("INFO", label, msg))
                print(f"  [INFO] {label}: {msg}")
            else:
                failed_checks += 1
                issues.append(("FAIL", label, msg))
                print(f"  [FAIL] {label}: {msg}")

    tray_status = {}  # tray -> list of (type, detail)

    # ── PER-TRAY CHECKS ──
    print(f"\n{'-'*70}")
    print(" PER-TRAY FIX VERIFICATION")
    print(f"{'-'*70}")

    for sec in sections:
        tray = sec["tray"]
        tray_check_dir = f"{tray}_checked"
        tray_path = os.path.join(box_path, tray_check_dir)

        if not verify_tray_exists(tray_path):
            print(f"\n  [SKIP] {tray}: folder not found")
            continue

        has_important = len(sec["important"]) > 0
        label = "IMPORTANT" if has_important else "minor"
        print(f"\n  [{label}] {tray}")

        all_fixes = sec["important"] + sec["not_important"]

        tray_issues = []

        for fix_line in all_fixes:
            fix_text = fix_line.lstrip("- ")

            if "Fixed noise floats" in fix_text:
                total_checks += 1
                ok, msg = verify_noise_floats(tray_path)
                if ok: passed_checks += 1
                else:
                    failed_checks += 1
                    tray_issues.append(("FAIL", f"{tray}: noise floats -> {msg}"))
                print(f"    [{'PASS' if ok else 'FAIL'}] {fix_text} -> {msg}")

            elif "Inserted" in fix_text and "missing row(s)" in fix_text and "SiPM_Location" in fix_text:
                m = re.search(r"Inserted (\d+) missing", fix_text)
                expected = int(m.group(1)) if m else 0

                total_checks += 1
                ok, msg = verify_char_sequence(tray_path)
                if ok: passed_checks += 1
                else:
                    failed_checks += 1
                    tray_issues.append(("FAIL", f"{tray}: char sequence -> {msg}"))
                print(f"    [{'PASS' if ok else 'FAIL'}] Sequence: {fix_text} -> {msg}")

                total_checks += 1
                ok, msg = verify_char_group_integrity(tray_path)
                if ok: passed_checks += 1
                else:
                    failed_checks += 1
                    tray_issues.append(("FAIL", f"{tray}: group integrity -> {msg}"))
                print(f"    [{'PASS' if ok else 'FAIL'}] Group integrity: -> {msg}")

                total_checks += 1
                ok, msg = verify_char_inserted_rows(tray_path, expected)
                if ok: passed_checks += 1
                else:
                    failed_checks += 1
                    tray_issues.append(("FAIL", f"{tray}: inserted rows -> {msg}"))
                print(f"    [{'PASS' if ok else 'FAIL'}] Inserted rows: -> {msg}")

            elif "Filled" in fix_text and "blank(s) with 0 in column" in fix_text:
                m_col = re.search(r"column '(\w+)'", fix_text)
                m_rows = re.search(r"at rows \[([^\]]+)\]", fix_text)
                if m_col and m_rows:
                    col = m_col.group(1)
                    expected_rows = [int(x.strip()) for x in m_rows.group(1).split(",")]
                    total_checks += 1
                    ok, msg = verify_blanks_filled(tray_path, col, expected_rows)
                    if ok: passed_checks += 1
                    else:
                        failed_checks += 1
                        tray_issues.append(("FAIL", f"{tray}: blanks not filled in {col}"))
                    print(f"    [{'PASS' if ok else 'FAIL'}] {fix_text} -> {msg}")

            elif any(kw in fix_text for kw in ["Vendor ->", "Vendor_Delivery_ID", "Vendor_Box_Number", "Tray_Number", "Test_Box_ID", "Institution"]):
                total_checks += 1
                ok, msg = verify_manifest(tray_path, tray)
                if ok: passed_checks += 1
                else:
                    failed_checks += 1
                    tray_issues.append(("FAIL", f"{tray}: manifest fix not applied"))
                print(f"    [{'PASS' if ok else 'FAIL'}] {fix_text} -> {msg}")

        total_checks += 1
        ok, msg = verify_mass_test_sequence(tray_path)
        if ok: passed_checks += 1
        else:
            failed_checks += 1
            tray_issues.append(("FAIL", f"{tray}: mass test location sequence broken"))
        print(f"    [{'PASS' if ok else 'FAIL'}] SiPM-mass-test-results.xlsx location sequence -> {msg}")

        total_checks += 1
        ok, msg = verify_no_remaining_nans(tray_path)
        if ok: passed_checks += 1
        else:
            failed_checks += 1
            tray_issues.append(("FAIL", f"{tray}: remaining NaNs -> {msg}"))
        print(f"    [{'PASS' if ok else 'FAIL'}] No remaining NaNs -> {msg}")

        if tray_issues:
            tray_status[tray] = tray_issues

    print(f"\n{'='*70}")
    print(f" SUMMARY — {box_name}")
    print(f"{'='*70}")
    print(f" Total checks: {total_checks}")
    print(f" Passed:       {passed_checks}")
    print(f" Warnings:     {warning_checks}")
    print(f" Failed:       {failed_checks}")
    if info_checks > 0:
        print(f" Info:         {info_checks}")

    if issues:
        print(f"\n{'='*70}")
        print(f" ISSUES TO REVIEW")
        print(f"{'='*70}")
        for typ, label, msg in issues:
            print(f"  [{typ}] {label}")
            print(f"        {msg}")

    if tray_status:
        print(f"\n{'='*70}")
        print(f" TRAY-LEVEL ISSUES")
        print(f"{'='*70}")
        for tray, t_issues in tray_status.items():
            for typ, detail in t_issues:
                print(f"  [{typ}] {detail}")

    print(f"\n{'='*70}")
    if failed_checks > 0:
        print(f" [X] FAILED — {failed_checks} check(s) failed, see above")
    elif warning_checks > 0:
        print(f" [!] PASSED WITH {warning_checks} WARNING(S) — see above")
    else:
        print(f" [V] ALL CHECKS PASSED")
    print(f"{'='*70}")


def main():
    parser = argparse.ArgumentParser(
        description="Verify box equivalency after fixes."
    )
    parser.add_argument("vendor", type=str, help="Vendor: fbk, hpk_ciemat, hpk_infn")
    parser.add_argument("box", type=str, help="Box: e.g. Box05, box05, 5")
    args = parser.parse_args()

    vendor = args.vendor.lower()
    if vendor not in VENDOR_MAP:
        print(f"[ERROR] Unknown vendor '{args.vendor}'. Options: {', '.join(VENDOR_MAP.keys())}")
        sys.exit(1)
    vendor_dir = VENDOR_MAP[vendor]

    box = args.box.lower().replace("box", "")
    if not box.isdigit():
        print(f"[ERROR] Invalid box '{args.box}'")
        sys.exit(1)
    box_num = int(box)
    box_folder = f"Box{box_num:02d}_checked"
    box_name = f"Box{box_num:02d}"

    box_path = os.path.join(SCRIPT_DIR, "checked", vendor_dir, box_folder)
    if not os.path.isdir(box_path):
        print(f"[ERROR] Not found: {box_path}")
        sys.exit(1)

    run_verifications(box_path, box_name)


if __name__ == "__main__":
    main()
