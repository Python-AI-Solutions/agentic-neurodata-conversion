#!/usr/bin/env python3
"""Validate ontology files before commit.

This script checks:
1. Valid JSON syntax
2. Required keys present
3. Header count matches actual count
4. No duplicate term IDs
5. All terms have required fields
6. Parent terms exist in the file

Usage:
    python scripts/validate_ontology.py

Exit codes:
    0 - All validations passed
    1 - Validation failed
"""

import json
import sys
from pathlib import Path


def validate_ontology_file(file_path: Path) -> bool:
    """Validate a single ontology JSON file.

    Args:
        file_path: Path to ontology JSON file

    Returns:
        True if valid, False otherwise
    """
    print(f"\nValidating {file_path.name}...")
    print("=" * 60)

    # 1. Check file exists
    if not file_path.exists():
        print(f"  ❌ File not found: {file_path}")
        return False

    # 2. Load and validate JSON syntax
    try:
        with open(file_path) as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        print(f"  ❌ Invalid JSON syntax: {e}")
        return False
    print("  ✅ Valid JSON syntax")

    # 3. Check required top-level keys
    required_keys = ["ontology", "version", "total_terms", "terms"]
    for key in required_keys:
        if key not in data:
            print(f"  ❌ Missing required key: '{key}'")
            return False
    print(f"  ✅ All required keys present: {required_keys}")

    # Optional keys
    if "description" in data:
        print(f"  ℹ️  Description: {data['description'][:60]}...")
    else:
        print("  ℹ️  No description (optional)")

    # 4. Check count matches
    header_count = data["total_terms"]
    actual_count = len(data["terms"])
    if header_count != actual_count:
        print("  ❌ Count mismatch:")
        print(f"     - Header 'total_terms': {header_count}")
        print(f"     - Actual term count:    {actual_count}")
        print(f'     → Update header to: "total_terms": {actual_count}')
        return False
    print(f"  ✅ Count matches: {actual_count} terms")

    # 5. Check for duplicate term IDs
    term_ids = [t["term_id"] for t in data["terms"]]
    unique_ids = set(term_ids)
    if len(term_ids) != len(unique_ids):
        duplicates = [tid for tid in term_ids if term_ids.count(tid) > 1]
        duplicate_set = set(duplicates)
        print(f"  ❌ Duplicate term IDs found: {len(term_ids) - len(unique_ids)} duplicates")
        for dup_id in sorted(duplicate_set):
            count = term_ids.count(dup_id)
            print(f"     - {dup_id} appears {count} times")
        return False
    print(f"  ✅ No duplicate term IDs ({len(unique_ids)} unique)")

    # 6. Check term schema
    required_term_keys = ["term_id", "label", "synonyms", "parent_terms"]
    invalid_terms = []
    for i, term in enumerate(data["terms"]):
        for key in required_term_keys:
            if key not in term:
                invalid_terms.append((i, term.get("term_id", "UNKNOWN"), key))

    if invalid_terms:
        print(f"  ❌ {len(invalid_terms)} terms missing required fields:")
        for idx, term_id, missing_key in invalid_terms[:5]:  # Show first 5
            print(f"     - Term {idx} ({term_id}): missing '{missing_key}'")
        if len(invalid_terms) > 5:
            print(f"     ... and {len(invalid_terms) - 5} more")
        return False
    print(f"  ✅ All terms have required fields: {required_term_keys}")

    # 7. Check parent terms exist (WARNING ONLY for subsets)
    invalid_parents = []
    for term in data["terms"]:
        for parent_id in term["parent_terms"]:
            if parent_id not in unique_ids:
                invalid_parents.append((term["term_id"], term["label"], parent_id))

    if invalid_parents:
        print(f"  ⚠️  {len(invalid_parents)} terms reference external parents (OK for subsets):")
        for term_id, label, parent_id in invalid_parents[:3]:  # Show first 3
            print(f"     - {term_id} ({label}) → {parent_id}")
        if len(invalid_parents) > 3:
            print(f"     ... and {len(invalid_parents) - 3} more")
    else:
        print("  ✅ All parent terms exist in file (complete hierarchy)")

    # 8. Check for circular references (basic check)
    # A term should not be its own parent
    self_references = []
    for term in data["terms"]:
        if term["term_id"] in term["parent_terms"]:
            self_references.append((term["term_id"], term["label"]))

    if self_references:
        print(f"  ❌ {len(self_references)} terms reference themselves as parent:")
        for term_id, label in self_references:
            print(f"     - {term_id} ({label})")
        return False
    print("  ✅ No self-references detected")

    # Summary
    print("\n  " + "─" * 56)
    print(f"  ✅ {file_path.name}: ALL CHECKS PASSED")
    print(f"     - Ontology: {data['ontology']}")
    print(f"     - Version: {data['version']}")
    print(f"     - Terms: {actual_count}")
    print(f"     - Unique IDs: {len(unique_ids)}")
    print("  " + "─" * 56)

    return True


def main() -> int:
    """Run validation on all ontology files.

    Returns:
        0 if all files valid, 1 if any validation fails
    """
    print("\n" + "=" * 60)
    print("  ONTOLOGY FILE VALIDATION")
    print("=" * 60)

    ontology_dir = Path("agentic_neurodata_conversion/kg_service/ontologies")

    if not ontology_dir.exists():
        print(f"\n❌ Ontology directory not found: {ontology_dir}")
        print("   Are you running from the project root?")
        return 1

    files = [
        ontology_dir / "ncbi_taxonomy_subset.json",
        ontology_dir / "uberon_subset.json",
        ontology_dir / "pato_sex_subset.json",
    ]

    all_valid = True
    for file_path in files:
        if not validate_ontology_file(file_path):
            all_valid = False

    print("\n" + "=" * 60)
    if all_valid:
        print("  ✅ ALL ONTOLOGY FILES VALID")
        print("=" * 60)
        print("\nSafe to commit! 🎉\n")
        return 0
    else:
        print("  ❌ VALIDATION FAILED")
        print("=" * 60)
        print("\n⚠️  Fix issues before committing!\n")
        return 1


if __name__ == "__main__":
    sys.exit(main())
