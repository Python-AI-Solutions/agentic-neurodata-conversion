from mcp_server import analyze_data, handoff


def test_with_mcp_layer():
    analyze_data("dummy_dataset")
    result = handoff("dummy_dataset", "out_test.nwb")
    assert result["return_code"] == 0
