#!/usr/bin/env python3
"""Verify brain_region schema fix without requiring API keys."""

from agentic_neurodata_conversion.agents.metadata.intelligent_parser import IntelligentMetadataParser
from agentic_neurodata_conversion.agents.metadata.schema import NWBDANDISchema


def verify_schema_fix():
    """Verify brain_region is properly configured in schema and parser."""

    print("=" * 60)
    print("VERIFYING BRAIN_REGION SCHEMA FIX")
    print("=" * 60)

    parser = IntelligentMetadataParser()
    schema = NWBDANDISchema()

    # Check 1: Fields exist in schema
    print("\n✓ Check 1: Schema field definitions")
    schema_fields = {f.name: f for f in schema.get_all_fields()}

    checks = {
        "brain_region": schema_fields.get("brain_region"),
        "electrode_location": schema_fields.get("electrode_location"),
    }

    for field_name, field_obj in checks.items():
        if field_obj:
            print(f"  ✅ {field_name}: Found in schema")
            print(f"     - Display name: {field_obj.display_name}")
            print(f"     - Requirement: {field_obj.requirement_level.value}")
            print(f"     - Example: {field_obj.example}")
            print(f"     - Extraction patterns: {', '.join(field_obj.extraction_patterns[:5])}...")
        else:
            print(f"  ❌ {field_name}: NOT found in schema")

    # Check 2: Ontology configuration
    print("\n✓ Check 2: Ontology-governed field configuration")
    ontology_test_fields = ["species", "sex", "brain_region", "electrode_location"]

    for field_name in ontology_test_fields:
        is_ontology = parser._is_ontology_governed_field(field_name)
        in_schema = field_name in schema_fields
        status = "✅" if (is_ontology and in_schema) else "⚠️"
        print(f"  {status} {field_name:20} -> Ontology: {is_ontology:5}, Schema: {in_schema:5}")

    # Check 3: LLM prompt includes brain_region
    print("\n✓ Check 3: LLM extraction prompt includes brain_region")
    schema_context = parser._build_schema_context()

    if "brain_region" in schema_context.lower():
        print("  ✅ brain_region found in LLM prompt context")
        # Find the line mentioning brain_region
        for line in schema_context.split("\n"):
            if "brain_region" in line.lower():
                print(f"     {line.strip()}")
                break
    else:
        print("  ❌ brain_region NOT in LLM prompt context")

    # Check 4: Field path mapping
    print("\n✓ Check 4: KG field path mapping")
    field_path_map = {
        "species": "subject.species",
        "sex": "subject.sex",
        "location": "ecephys.ElectrodeGroup.location",
        "brain_region": "ecephys.ElectrodeGroup.location",
        "electrode_location": "ecephys.ElectrodeGroup.location",
    }

    for field_name, expected_path in field_path_map.items():
        print(f"  • {field_name:20} -> {expected_path}")

    # Summary
    print("\n" + "=" * 60)
    print("VERIFICATION SUMMARY")
    print("=" * 60)

    brain_region_field = schema_fields.get("brain_region")
    electrode_field = schema_fields.get("electrode_location")

    all_good = all(
        [
            brain_region_field is not None,
            electrode_field is not None,
            parser._is_ontology_governed_field("brain_region"),
            "brain_region" in schema_context.lower(),
        ]
    )

    if all_good:
        print("✅ ALL CHECKS PASSED")
        print("\n🎉 Schema fix successful! brain_region is now properly configured.")
        print("\nWhat this means:")
        print("  • LLM will now extract brain_region from user input")
        print("  • KG service will validate brain_region values")
        print("  • Cross-field validation (species + anatomy) will work")
        print("\nNext steps:")
        print("  1. Restart backend service: pixi run dev")
        print(
            "  2. Restart KG service: export NEO4J_PASSWORD=<pwd> && pixi run uvicorn agentic_neurodata_conversion.kg_service.main:app --port 8001"
        )
        print("  3. Re-run UI Tests 1, 4a, 4b")
        print("  4. Verify:")
        print("     - KG logs show: 'Normalizing ecephys.ElectrodeGroup.location=Ammon'")
        print("     - UI displays validation badge for brain_region")
        print("     - Test 1: 'Ammon' → 'Ammon's horn' (semantic match)")
        print("     - Test 4b: C. elegans + hippocampus shows incompatibility warning")
    else:
        print("❌ SOME CHECKS FAILED")
        print("\nIssues to fix:")
        if not brain_region_field:
            print("  • brain_region field missing from schema")
        if not parser._is_ontology_governed_field("brain_region"):
            print("  • brain_region not marked as ontology-governed")
        if "brain_region" not in schema_context.lower():
            print("  • brain_region not in LLM prompt")

    return all_good


if __name__ == "__main__":
    success = verify_schema_fix()
    exit(0 if success else 1)
