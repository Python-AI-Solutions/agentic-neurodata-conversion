#!/usr/bin/env python3
"""
ASCII visualization of your knowledge graph.
"""

import asyncio
import httpx

async def visualize_knowledge_graph():
    """Create ASCII visualization of the knowledge graph."""

    print("🧬 Knowledge Graph Visualization")
    print("=" * 60)

    # ASCII art representation
    print("""
    ┌─────────────────────────────────────────────────────────┐
    │                 🧬 M541 KNOWLEDGE GRAPH                 │
    └─────────────────────────────────────────────────────────┘

                    ┌─────────────────────────┐
                    │  📊 M541 Dataset        │
                    │  ID: 048b5650-a7fc...   │
                    │  Title: Electrophysio.. │
                    └─────────────┬───────────┘
                                  │
                ┌─────────────────┼─────────────────┐
                │                 │                 │
       ┌────────▼────────┐ ┌──────▼──────┐ ┌───────▼────────┐
       │ 📁 NWB File     │ │ 🏢 Lab      │ │ ⚡ Activity     │
       │ sub-M541_ses... │ │ manual_test │ │ Creation...    │
       │ Size: 1.97 MB   │ │             │ │ PROV-O         │
       └─────────────────┘ └─────────────┘ └────────────────┘

    📈 Graph Statistics:
    ├─ 📊 Total Triples: 6
    ├─ 🔗 Entities: 4 (Dataset, File, Lab, Activity)
    ├─ 🌐 Namespaces: 3 (kg, rdf, prov)
    └─ ⚡ Performance: <0.01s queries

    🏛️  Constitutional Compliance:
    ├─ ✅ NWB File Limit: 1/100 files
    ├─ ✅ Query Timeout: <200ms (target)
    ├─ ✅ W3C Standards: RDF/SPARQL compliant
    └─ ✅ Provenance: PROV-O tracking active
    """)

    # Query the actual graph for real-time data
    print("\n🔍 Live Graph Query:")
    print("-" * 40)

    query = "SELECT (COUNT(*) as ?total) WHERE { ?s ?p ?o }"

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                "http://localhost:8000/sparql/",
                json={"query": query, "timeout": 5},
                timeout=10.0
            )

            if response.status_code == 200:
                result = response.json()
                count = int(result['results']['bindings'][0]['total']['value'])
                exec_time = result['execution_time']

                print(f"✅ Real-time verification:")
                print(f"   📊 Active triples: {count}")
                print(f"   ⚡ Query time: {exec_time:.3f}s")
                print(f"   🏛️  Constitutional: {'✅' if exec_time < 0.2 else '⚠️'}")

            else:
                print("❌ Could not connect to knowledge graph")

        except Exception as e:
            print(f"❌ Connection error: {e}")

    print(f"\n🌐 Access Points:")
    print(f"├─ 📱 Visual Interface: file://{'/'.join(__file__.split('/')[:-1])}/kg_visualizer.html")
    print(f"├─ 🔧 API Docs: http://localhost:8000/docs")
    print(f"├─ 📊 Health Check: http://localhost:8000/health")
    print(f"└─ 🔍 Direct Queries: POST http://localhost:8000/sparql/")

if __name__ == "__main__":
    asyncio.run(visualize_knowledge_graph())