"""
Main CLI interface for knowledge graph operations.

Constitutional compliance: All operations follow constitutional principles.
"""

import typer
import asyncio
import json
from typing import Optional, List
from rich.console import Console
from rich.table import Table
import httpx

app = typer.Typer(help="Knowledge Graph Systems CLI")
console = Console()

BASE_URL = "http://localhost:8000"

@app.command("create-dataset")
def create_dataset(
    title: str = typer.Option(..., help="Dataset title"),
    description: Optional[str] = typer.Option(None, help="Dataset description"),
    nwb_files: str = typer.Option(..., help="Comma-separated list of NWB files"),
    lab_id: Optional[str] = typer.Option(None, help="Lab identifier"),
    protocol_id: Optional[str] = typer.Option(None, help="Protocol identifier")
):
    """Create a new dataset with constitutional compliance."""
    async def create():
        files_list = [f.strip() for f in nwb_files.split(",")]

        payload = {
            "title": title,
            "description": description,
            "nwb_files": files_list,
            "lab_id": lab_id,
            "protocol_id": protocol_id
        }

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(f"{BASE_URL}/datasets", json=payload, timeout=35.0)

                if response.status_code == 201:
                    data = response.json()
                    console.print(f"✅ Dataset created successfully!", style="green")
                    console.print(f"Dataset ID: {data['dataset_id']}")
                    console.print(f"Status: {data['status']}")
                    console.print(f"NWB files: {len(data['nwb_files'])}")
                else:
                    error = response.json()
                    console.print(f"❌ Dataset creation failed:", style="red")
                    console.print(f"Error: {error.get('detail', {}).get('error', 'Unknown error')}")

                    if 'constitutional_violation' in error.get('detail', {}):
                        console.print(f"Constitutional violation: {error['detail']['constitutional_violation']}", style="yellow")

            except httpx.TimeoutException:
                console.print("❌ Request timed out", style="red")
            except Exception as e:
                console.print(f"❌ Error: {str(e)}", style="red")

    asyncio.run(create())

@app.command("sparql-query")
def sparql_query(
    query: str = typer.Option(..., help="SPARQL query string"),
    timeout: int = typer.Option(30, help="Query timeout in seconds"),
    limit: Optional[int] = typer.Option(None, help="Result limit"),
    output_format: str = typer.Option("table", help="Output format: table, json")
):
    """Execute SPARQL query with constitutional compliance."""
    async def execute():
        payload = {
            "query": query,
            "timeout": timeout,
            "limit": limit
        }

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(f"{BASE_URL}/sparql", json=payload, timeout=timeout + 5)

                if response.status_code == 200:
                    data = response.json()

                    console.print(f"✅ Query executed successfully!", style="green")
                    console.print(f"Execution time: {data['execution_time']:.3f}s")
                    console.print(f"Results: {data.get('count', 0)}")

                    if output_format == "json":
                        console.print(json.dumps(data, indent=2))
                    else:
                        # Display as table
                        if data.get("results", {}).get("bindings"):
                            bindings = data["results"]["bindings"]
                            if bindings:
                                vars_list = data["head"]["vars"]
                                table = Table(title="SPARQL Query Results")

                                for var in vars_list:
                                    table.add_column(var, style="cyan")

                                for binding in bindings:
                                    row = [binding.get(var, {}).get("value", "") for var in vars_list]
                                    table.add_row(*row)

                                console.print(table)
                else:
                    error = response.json()
                    console.print(f"❌ Query failed:", style="red")
                    console.print(f"Error: {error.get('detail', {}).get('error', 'Unknown error')}")

            except httpx.TimeoutException:
                console.print("❌ Query timed out", style="red")
            except Exception as e:
                console.print(f"❌ Error: {str(e)}", style="red")

    asyncio.run(execute())

@app.command("list-datasets")
def list_datasets(
    limit: int = typer.Option(10, help="Number of datasets to show"),
    offset: int = typer.Option(0, help="Number of datasets to skip")
):
    """List datasets with pagination."""
    async def list_all():
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    f"{BASE_URL}/datasets?limit={limit}&offset={offset}",
                    timeout=15.0
                )

                if response.status_code == 200:
                    data = response.json()

                    console.print(f"📊 Found {data['total']} datasets (showing {len(data['datasets'])})", style="blue")

                    if data['datasets']:
                        table = Table(title="Datasets")
                        table.add_column("ID", style="cyan")
                        table.add_column("Title", style="green")
                        table.add_column("Files", style="yellow")
                        table.add_column("Status", style="magenta")

                        for dataset in data['datasets']:
                            table.add_row(
                                dataset['dataset_id'][:8] + "...",
                                dataset['title'],
                                str(len(dataset['nwb_files'])),
                                dataset['status']
                            )

                        console.print(table)
                    else:
                        console.print("No datasets found.", style="yellow")
                else:
                    error = response.json()
                    console.print(f"❌ Failed to list datasets:", style="red")
                    console.print(f"Error: {error.get('detail', {}).get('error', 'Unknown error')}")

            except Exception as e:
                console.print(f"❌ Error: {str(e)}", style="red")

    asyncio.run(list_all())

@app.command("server-info")
def server_info():
    """Get server information and constitutional compliance status."""
    async def info():
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(f"{BASE_URL}/", timeout=10.0)

                if response.status_code == 200:
                    data = response.json()

                    console.print("🔧 Knowledge Graph Systems Server", style="bold blue")
                    console.print(f"Version: {data['version']}")

                    console.print("\n📋 Constitutional Compliance:", style="bold green")
                    compliance = data['constitutional_compliance']
                    for key, value in compliance.items():
                        console.print(f"  • {key.replace('_', ' ').title()}: {value}")

                    console.print("\n⚡ Performance Targets:", style="bold yellow")
                    targets = data['performance_targets']
                    for key, value in targets.items():
                        console.print(f"  • {key.replace('_', ' ').title()}: {value}")

            except Exception as e:
                console.print(f"❌ Error connecting to server: {str(e)}", style="red")

    asyncio.run(info())

if __name__ == "__main__":
    app()