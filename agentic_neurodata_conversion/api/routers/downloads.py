"""Downloads router for NWB file and report download endpoints.

Handles:
- NWB file downloads (HDF5 format)
- Evaluation report downloads (HTML, PDF, JSON)
- HTML report viewing in browser
"""

import json
import logging
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, HTMLResponse

from agentic_neurodata_conversion.api.dependencies import get_or_create_mcp_server

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/api", tags=["downloads"])


@router.get("/download/nwb")
async def download_nwb():
    """Download the converted NWB file.

    Returns the converted NWB file in HDF5 format. The file must have been
    successfully converted before it can be downloaded.

    Returns:
        FileResponse with NWB file (application/x-hdf5)

    Raises:
        HTTPException 404: If no NWB file is available or conversion not complete
    """
    mcp_server = get_or_create_mcp_server()

    if not mcp_server.global_state.output_path:
        raise HTTPException(
            status_code=404,
            detail="No NWB file available for download",
        )

    output_path = Path(mcp_server.global_state.output_path)

    if not output_path.exists():
        raise HTTPException(
            status_code=404,
            detail="NWB file not found",
        )

    return FileResponse(
        path=str(output_path),
        media_type="application/x-hdf5",
        filename=output_path.name,
    )


@router.get("/reports/view")
async def view_html_report():
    """View the HTML evaluation report in browser.

    Displays the HTML evaluation report directly in the browser with full
    formatting and interactive elements. If a workflow trace is available,
    the report is regenerated to include detailed provenance information.

    Returns:
        HTMLResponse with formatted report content

    Raises:
        HTTPException 404: If no report is available or conversion not complete
    """
    mcp_server = get_or_create_mcp_server()

    if not mcp_server.global_state.output_path:
        raise HTTPException(
            status_code=404,
            detail="No conversion output available",
        )

    output_path_str = str(mcp_server.global_state.output_path).strip()
    if not output_path_str:
        raise HTTPException(
            status_code=404,
            detail="Output path is empty",
        )

    # Find the HTML report file
    output_dir = Path(output_path_str).parent
    output_stem = Path(output_path_str).stem
    html_report = output_dir / f"{output_stem}_evaluation_report.html"

    # Check if workflow_trace JSON exists
    workflow_trace_path = output_dir / f"{output_stem}_workflow_trace.json"

    if html_report.exists():
        # Check if we need to regenerate the report with workflow_trace
        if workflow_trace_path.exists():
            # Load workflow_trace
            with open(workflow_trace_path) as f:
                workflow_trace = json.load(f)

            # Check if the workflow_trace has metadata_provenance
            if "metadata_provenance" in workflow_trace:
                # Regenerate the HTML report with the correct workflow_trace
                from agentic_neurodata_conversion.agents.evaluation_agent import EvaluationAgent
                from agentic_neurodata_conversion.services.report_service import ReportService

                # Extract file info from NWB file
                nwb_path = mcp_server.global_state.output_path
                eval_agent = EvaluationAgent()
                file_info = eval_agent._extract_file_info(nwb_path)

                # MERGE BACK the original provenance from workflow_trace
                # This preserves the detailed AI-parsed provenance instead of generic "file-extracted"
                if "metadata_provenance" in workflow_trace:
                    file_info["_workflow_provenance"] = workflow_trace["metadata_provenance"]

                # Create validation result with file info
                validation_result: dict[str, Any] = {
                    "overall_status": (
                        mcp_server.global_state.overall_status.value
                        if mcp_server.global_state.overall_status
                        else "UNKNOWN"
                    ),
                    "nwb_file_path": str(nwb_path),
                    "file_info": file_info,
                    "issues": [],
                    "issue_counts": {},
                }

                # Regenerate HTML report with workflow_trace
                report_service = ReportService()
                report_service.generate_html_report(
                    html_report,
                    validation_result,
                    None,  # llm_analysis
                    workflow_trace,
                )

                logger.info(f"Regenerated HTML report with workflow_trace from {workflow_trace_path}")

        # Read and return HTML content directly for browser display
        with open(html_report, encoding="utf-8") as f:
            html_content = f.read()
        return HTMLResponse(content=html_content)

    raise HTTPException(
        status_code=404,
        detail="No HTML report available. Report may not have been generated yet.",
    )


@router.get("/download/report")
async def download_report():
    """Download the evaluation report (HTML, PDF, or JSON).

    Attempts to provide the evaluation report in the following order of preference:
    1. HTML format (primary, most readable)
    2. PDF format (portable, printable)
    3. JSON format (machine-readable, correction context)

    Returns:
        FileResponse with report file in available format

    Raises:
        HTTPException 404: If no report file is available
    """
    mcp_server = get_or_create_mcp_server()

    if not mcp_server.global_state.output_path:
        raise HTTPException(
            status_code=404,
            detail="No conversion output available",
        )

    output_path_str = str(mcp_server.global_state.output_path).strip()
    if not output_path_str:
        raise HTTPException(
            status_code=404,
            detail="Output path is empty",
        )

    # Find the report file
    output_dir = Path(output_path_str).parent
    output_stem = Path(output_path_str).stem

    # Try HTML first (primary format)
    html_report = output_dir / f"{output_stem}_evaluation_report.html"
    if html_report.exists():
        return FileResponse(
            path=str(html_report),
            media_type="text/html",
            filename=html_report.name,
        )

    # Try JSON
    json_report = output_dir / f"{output_stem}_correction_context.json"
    if json_report.exists():
        return FileResponse(
            path=str(json_report),
            media_type="application/json",
            filename=json_report.name,
        )

    raise HTTPException(
        status_code=404,
        detail="No report file available for download",
    )
