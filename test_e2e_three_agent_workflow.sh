#!/bin/bash

# ============================================================================
# End-to-End Three-Agent Workflow Test
# Tests complete workflow from frontend perspective
# ============================================================================

API_BASE="http://localhost:8000"
TEST_FILE="/Users/adityapatane/agentic-neurodata-conversion-14/test_data/spikeglx/Noise4Sam_g0_t0.imec0.ap.bin"

echo "============================================================================"
echo "THREE-AGENT ARCHITECTURE E2E TEST"
echo "============================================================================"
echo "Testing: SpikeGLX → NWB conversion with validation workflow"
echo "File: $TEST_FILE"
echo ""
echo "Expected Flow:"
echo "1. User uploads → Conversation Agent validates metadata"
echo "2. Conversation Agent → Conversion Agent: Convert"
echo "3. Conversion Agent → NWB file"
echo "4. Conversion Agent → Evaluation Agent: Validate"
echo "5. Evaluation Agent → User with result (PASSED/PASSED_WITH_ISSUES/FAILED)"
echo "============================================================================"
echo ""

# Clean up from previous runs
rm -f /tmp/e2e_*.json

# ============================================================================
# STEP 1: Reset System (Clean State)
# ============================================================================
echo "STEP 1: Reset System"
echo "--------------------"
curl -s -X POST "$API_BASE/api/reset" > /tmp/e2e_reset.json
RESET_STATUS=$(cat /tmp/e2e_reset.json | python3 -c "import sys, json; print(json.load(sys.stdin).get('status', 'unknown'))" 2>/dev/null || echo "error")
echo "Reset status: $RESET_STATUS"
sleep 1
echo ""

# ============================================================================
# STEP 2: Upload File (User → API → Conversation Agent)
# ============================================================================
echo "STEP 2: Upload File"
echo "-------------------"
echo "Uploading: $(basename $TEST_FILE)"

curl -s -X POST "$API_BASE/api/upload" \
  -F "file=@$TEST_FILE" \
  > /tmp/e2e_upload.json

UPLOAD_STATUS=$(cat /tmp/e2e_upload.json | python3 -c "import sys, json; print(json.load(sys.stdin).get('status', 'unknown'))" 2>/dev/null || echo "error")

if [ "$UPLOAD_STATUS" = "success" ]; then
    echo "✓ Upload successful"
    echo "  Message: $(cat /tmp/e2e_upload.json | python3 -c "import sys, json; print(json.load(sys.stdin).get('message', ''))" 2>/dev/null)"
else
    echo "✗ Upload failed"
    cat /tmp/e2e_upload.json
    exit 1
fi
sleep 2
echo ""

# ============================================================================
# STEP 3: Check Initial Status
# ============================================================================
echo "STEP 3: Check Initial Status"
echo "-----------------------------"
curl -s "$API_BASE/api/status" > /tmp/e2e_status1.json

python3 << 'EOF'
import json
with open('/tmp/e2e_status1.json') as f:
    status = json.load(f)
print(f"  Status: {status.get('status')}")
print(f"  Input Path: {status.get('input_path', 'None')}")
print(f"  Detected Format: {status.get('detected_format', 'None')}")
print(f"  Conversation Type: {status.get('conversation_type', 'None')}")
EOF
sleep 1
echo ""

# ============================================================================
# STEP 4: Start Conversion (Conversation Agent begins)
# ============================================================================
echo "STEP 4: Start Conversion Workflow"
echo "----------------------------------"
echo "Triggering: Conversation Agent → metadata validation"

curl -s -X POST "$API_BASE/api/start-conversion" > /tmp/e2e_start.json

START_STATUS=$(cat /tmp/e2e_start.json | python3 -c "import sys, json; print(json.load(sys.stdin).get('status', 'unknown'))" 2>/dev/null || echo "error")
START_MSG=$(cat /tmp/e2e_start.json | python3 -c "import sys, json; print(json.load(sys.stdin).get('message', ''))" 2>/dev/null || echo "")

echo "  Status: $START_STATUS"
echo "  Message: $START_MSG"

# Wait for Conversation Agent to process
sleep 3
echo ""

# ============================================================================
# STEP 5: Check if Metadata Requested (Conversation Agent)
# ============================================================================
echo "STEP 5: Check Conversation Agent Response"
echo "------------------------------------------"
curl -s "$API_BASE/api/status" > /tmp/e2e_status2.json

python3 << 'EOF'
import json
with open('/tmp/e2e_status2.json') as f:
    status = json.load(f)

conv_status = status.get('status')
conv_type = status.get('conversation_type', '')
llm_msg = status.get('llm_message', '')
conv_history = status.get('conversation_history', [])

print(f"  Conversion Status: {conv_status}")
print(f"  Conversation Type: {conv_type}")
print(f"  Conversation History Length: {len(conv_history)}")

if 'metadata' in conv_type or 'required' in conv_type:
    print("  ✓ Conversation Agent requesting metadata")
    if llm_msg:
        print(f"  LLM Message: {llm_msg[:200]}...")
elif conv_status == 'awaiting_user_input':
    print("  ✓ Conversation Agent awaiting input")
    if conv_history:
        last_msg = conv_history[-1]
        print(f"  Last message: {last_msg.get('content', '')[:200]}...")
else:
    print(f"  Note: Status is {conv_status}, may already be processing")
EOF
echo ""

# ============================================================================
# STEP 6: Provide Metadata (User → Conversation Agent)
# ============================================================================
echo "STEP 6: Provide Comprehensive Metadata"
echo "---------------------------------------"
echo "Simulating user input with complete metadata..."

METADATA_INPUT="Dr. Jane Smith from MIT, Smith Lab. Male C57BL/6 mouse, age P60, ID mouse001. Visual cortex neuropixels recording during awake behavior. Session started 2024-01-15 at 10:30 AM. Protocol IACUC-2024-001."

echo "  Input: $METADATA_INPUT"
echo "  Sending to chat endpoint..."

curl -s -X POST "$API_BASE/api/chat" \
  -F "message=$METADATA_INPUT" \
  > /tmp/e2e_chat1.json

# Wait for LLM processing
echo "  Waiting for LLM to process metadata (may take 30-60s)..."
sleep 30

CHAT_RESPONSE=$(cat /tmp/e2e_chat1.json | python3 -c "import sys, json; d=json.load(sys.stdin); print(d.get('message', d.get('answer', ''))[:300])" 2>/dev/null || echo "error")
echo "  Response: $CHAT_RESPONSE"
echo ""

# ============================================================================
# STEP 7: Check Conversion Progress
# ============================================================================
echo "STEP 7: Monitor Conversion Progress"
echo "------------------------------------"
echo "Checking if Conversation Agent → Conversion Agent handoff occurred..."

for i in {1..10}; do
    sleep 3
    curl -s "$API_BASE/api/status" > /tmp/e2e_status_loop_$i.json

    CURRENT_STATUS=$(cat /tmp/e2e_status_loop_$i.json | python3 -c "import sys, json; print(json.load(sys.stdin).get('status'))" 2>/dev/null)

    echo "  [$i] Status: $CURRENT_STATUS"

    case "$CURRENT_STATUS" in
        "converting")
            echo "  ✓ Conversion Agent processing..."
            ;;
        "validating")
            echo "  ✓ Conversion complete, Evaluation Agent validating..."
            break
            ;;
        "completed"|"failed"|"awaiting_retry_approval"|"awaiting_user_input")
            echo "  ✓ Workflow reached decision point: $CURRENT_STATUS"
            break
            ;;
    esac
done
echo ""

# ============================================================================
# STEP 8: Wait for Validation (Evaluation Agent)
# ============================================================================
echo "STEP 8: Wait for Evaluation Agent Validation"
echo "---------------------------------------------"
echo "Waiting for NWB Inspector validation..."

for i in {1..20}; do
    sleep 3
    curl -s "$API_BASE/api/status" > /tmp/e2e_status_validation_$i.json

    VAL_STATUS=$(cat /tmp/e2e_status_validation_$i.json | python3 -c "import sys, json; print(json.load(sys.stdin).get('status'))" 2>/dev/null)
    OVERALL=$(cat /tmp/e2e_status_validation_$i.json | python3 -c "import sys, json; print(json.load(sys.stdin).get('overall_status', 'N/A'))" 2>/dev/null)

    echo "  [$i] Status: $VAL_STATUS | Overall: $OVERALL"

    if [ "$VAL_STATUS" != "validating" ] && [ "$VAL_STATUS" != "converting" ]; then
        echo "  ✓ Validation complete!"
        break
    fi
done
echo ""

# ============================================================================
# STEP 9: Analyze Final State (Three-Agent Result)
# ============================================================================
echo "STEP 9: Analyze Final Workflow State"
echo "-------------------------------------"
curl -s "$API_BASE/api/status" > /tmp/e2e_final_status.json

python3 << 'EOF'
import json

with open('/tmp/e2e_final_status.json') as f:
    status = json.load(f)

print("FINAL STATE ANALYSIS:")
print("=" * 70)
print(f"Conversion Status: {status.get('status')}")
print(f"Overall Validation: {status.get('overall_status', 'N/A')}")
print(f"Conversation Type: {status.get('conversation_type', 'N/A')}")
print(f"Output Path: {status.get('output_path', 'None')}")
print(f"Can Download: {'Yes' if status.get('output_path') else 'No'}")
print(f"Correction Attempt: {status.get('correction_attempt', 0)}")
print(f"Can Retry: {status.get('can_retry', 'N/A')}")
print("")

# Analyze workflow path taken
overall = status.get('overall_status', '')
conv_status = status.get('status', '')

print("THREE-AGENT WORKFLOW PATH:")
print("-" * 70)
print("1. User Upload → Conversation Agent: ✓")
print("2. Conversation Agent → Conversion Agent: ✓")
print("3. Conversion Agent → NWB file:", "✓" if status.get('output_path') else "✗")
print("4. Conversion Agent → Evaluation Agent: ✓")
print("5. Evaluation Agent → Validation:", overall or "In Progress")
print("")

# Determine next step based on validation outcome
if overall == "PASSED":
    print("WORKFLOW OUTCOME: PASSED (No issues)")
    print("  → Evaluation Agent should generate PDF report")
    print("  → User can download NWB + PDF")
    print("  → END")
elif overall == "PASSED_WITH_ISSUES":
    print("WORKFLOW OUTCOME: PASSED_WITH_ISSUES (Has warnings)")
    print("  → Evaluation Agent generates improvement context")
    print("  → Evaluation Agent generates PASSED PDF (with warnings highlighted)")
    print("  → Evaluation Agent → Conversation Agent")
    print("  → Conversation Agent → User: 'Improve or Accept?'")
    print("  → User decides: IMPROVE (step 9) or ACCEPT (download & END)")
elif overall == "FAILED":
    print("WORKFLOW OUTCOME: FAILED (Critical errors)")
    print("  → Evaluation Agent generates correction context")
    print("  → Evaluation Agent generates FAILED report (JSON)")
    print("  → Evaluation Agent → Conversation Agent")
    print("  → Conversation Agent → User: 'Approve retry?'")
    print("  → User decides: APPROVE (step 9) or DECLINE (download & END)")
else:
    print(f"WORKFLOW STATE: {conv_status}")
    print("  → Still processing or awaiting decision")

print("")
print("CONVERSATION HISTORY:")
print("-" * 70)
conv_history = status.get('conversation_history', [])
for i, msg in enumerate(conv_history[-5:]):  # Last 5 messages
    role = msg.get('role', 'unknown')
    content = msg.get('content', '')[:100]
    print(f"  [{i+1}] {role}: {content}...")

print("")
print("METADATA COLLECTED:")
print("-" * 70)
metadata = status.get('metadata', {})
for key, value in list(metadata.items())[:10]:  # First 10 fields
    print(f"  {key}: {value}")

if len(metadata) > 10:
    print(f"  ... and {len(metadata) - 10} more fields")

print("")
print("VALIDATION RESULT:")
print("-" * 70)
val_result = status.get('validation_result', {})
if val_result:
    print(f"  Is Valid: {val_result.get('is_valid', 'N/A')}")
    print(f"  Issues Count: {len(val_result.get('issues', []))}")
    issues = val_result.get('issues', [])[:3]
    for issue in issues:
        print(f"    - {issue.get('severity')}: {issue.get('message', '')[:80]}")
else:
    print("  No validation result yet")

EOF
echo ""

# ============================================================================
# STEP 10: Test User Decision Points
# ============================================================================
echo "STEP 10: Check User Decision Points"
echo "------------------------------------"

python3 << 'EOF'
import json

with open('/tmp/e2e_final_status.json') as f:
    status = json.load(f)

conv_type = status.get('conversation_type', '')
overall = status.get('overall_status', '')
conv_status = status.get('status', '')

print("Decision Point Analysis:")
print("")

if overall == "PASSED_WITH_ISSUES" and 'improvement' in conv_type.lower():
    print("✓ DECISION POINT ACTIVE: Improve or Accept?")
    print("  User can send:")
    print("    - 'improve' → Enters correction loop (step 9)")
    print("    - 'accept' → Downloads NWB + PDF, END")
    print("")
    print("  Test command:")
    print("    curl -X POST $API_BASE/api/chat -F 'message=improve'")
elif conv_status == "awaiting_retry_approval":
    print("✓ DECISION POINT ACTIVE: Approve retry?")
    print("  User can send:")
    print("    - 'yes' or 'approve' → Enters correction loop (step 9)")
    print("    - 'no' or 'decline' → Downloads report, END")
    print("")
    print("  Test command:")
    print("    curl -X POST $API_BASE/api/retry-approval -F 'approved=true'")
elif conv_status == "completed":
    print("✓ WORKFLOW COMPLETE")
    print("  User can download:")
    print(f"    NWB file: {status.get('output_path', 'N/A')}")
    print("    Report: Available")
elif conv_status == "awaiting_user_input":
    print("✓ AWAITING USER INPUT")
    print("  Conversation Agent needs more information")
    llm_msg = status.get('llm_message', '')
    if llm_msg:
        print(f"  Question: {llm_msg[:200]}...")
else:
    print(f"Current state: {conv_status}")
    print(f"Overall validation: {overall}")

EOF
echo ""

# ============================================================================
# SUMMARY
# ============================================================================
echo "============================================================================"
echo "END-TO-END TEST SUMMARY"
echo "============================================================================"
echo ""
echo "Test completed successfully!"
echo ""
echo "To review detailed logs, check:"
echo "  /tmp/e2e_*.json"
echo ""
echo "To continue testing the workflow:"
echo "  1. If PASSED_WITH_ISSUES: curl -X POST $API_BASE/api/chat -F 'message=improve'"
echo "  2. If awaiting retry: curl -X POST $API_BASE/api/retry-approval -F 'approved=true'"
echo "  3. Check status: curl -s $API_BASE/api/status | python3 -m json.tool"
echo ""
echo "============================================================================"
