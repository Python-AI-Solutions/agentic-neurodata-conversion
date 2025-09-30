"""HTML visualization generator.

This module generates self-contained interactive HTML visualizations.
"""

from typing import Any
from pathlib import Path
import json
import math


def generate_visualization(graph_jsonld: str, metadata: dict[str, Any]) -> str:
    """Generate interactive HTML visualization.

    Args:
        graph_jsonld: Knowledge graph in JSON-LD format
        metadata: Metadata about the graph

    Returns:
        Complete HTML string
    """
    # Parse JSON-LD for embedding
    graph_data = json.loads(graph_jsonld) if isinstance(graph_jsonld, str) else graph_jsonld

    # Extract nodes and edges from JSON-LD
    nodes = []
    edges = []

    if isinstance(graph_data, list):
        graph_array = graph_data
    elif '@graph' in graph_data:
        graph_array = graph_data['@graph']
    else:
        graph_array = [graph_data]

    # Process each item in graph
    for item in graph_array:
        if isinstance(item, dict):
            node_id = item.get('@id', '')
            node_type = item.get('@type', ['Unknown'])
            if isinstance(node_type, list):
                node_type = node_type[0] if node_type else 'Unknown'

            # Extract label from ID (clean it up)
            label = node_id.split('/')[-1] if node_id else 'Unknown'
            # Remove leading underscores
            label = label.lstrip('_')

            nodes.append({
                'id': node_id,
                'label': label,
                'type': node_type.split('/')[-1] if isinstance(node_type, str) else 'Unknown'
            })

            # Extract edges from properties
            for key, value in item.items():
                if key.startswith('@'):
                    continue

                # Check if value is a reference (URI)
                if isinstance(value, list):
                    for v in value:
                        if isinstance(v, dict) and '@id' in v:
                            # This is a reference to another node
                            edges.append({
                                'source': node_id,
                                'target': v['@id'],
                                'label': key.split('/')[-1]
                            })

    # Create simplified graph structure
    simple_graph = {
        'nodes': nodes,
        'edges': edges
    }

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>NWB Knowledge Graph</title>
    <style>
        body {{
            margin: 0;
            padding: 0;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif;
            overflow: hidden;
            background: #ffffff;
        }}
        #canvas {{
            display: block;
            cursor: grab;
        }}
        #canvas:active {{
            cursor: grabbing;
        }}
        #info {{
            position: absolute;
            top: 10px;
            right: 10px;
            background: rgba(255, 255, 255, 0.95);
            padding: 15px 20px;
            border-radius: 8px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.15);
            font-size: 13px;
            z-index: 10;
        }}
        #info h3 {{
            margin: 0 0 10px 0;
            font-size: 14px;
            font-weight: 600;
        }}
        #info p {{
            margin: 5px 0;
            color: #666;
        }}
        #controls {{
            position: absolute;
            top: 10px;
            left: 10px;
            background: rgba(255, 255, 255, 0.95);
            padding: 12px 16px;
            border-radius: 8px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.15);
            z-index: 10;
        }}
        button {{
            padding: 6px 12px;
            margin: 2px;
            border: 1px solid #ddd;
            border-radius: 4px;
            background: white;
            cursor: pointer;
            font-size: 12px;
        }}
        button:hover {{
            background: #f5f5f5;
        }}
        #tooltip {{
            position: absolute;
            background: rgba(0, 0, 0, 0.85);
            color: white;
            padding: 8px 12px;
            border-radius: 4px;
            pointer-events: none;
            display: none;
            z-index: 100;
            font-size: 12px;
            max-width: 250px;
            word-wrap: break-word;
        }}
    </style>
</head>
<body>
    <div id="info">
        <h3>Graph Stats</h3>
        <p><strong>Nodes:</strong> {metadata.get('node_count', 0)}</p>
        <p><strong>Edges:</strong> {metadata.get('edge_count', 0)}</p>
    </div>

    <div id="controls">
        <button onclick="zoomIn()">Zoom +</button>
        <button onclick="zoomOut()">Zoom −</button>
        <button onclick="resetView()">Reset</button>
    </div>

    <canvas id="canvas"></canvas>
    <div id="tooltip"></div>

    <script type="application/json" id="graphData">
{json.dumps(simple_graph, indent=2)}
    </script>

    <script>
        const graphData = JSON.parse(document.getElementById('graphData').textContent);
        const canvas = document.getElementById('canvas');
        const ctx = canvas.getContext('2d');
        const tooltip = document.getElementById('tooltip');

        // Resize canvas
        function resizeCanvas() {{
            canvas.width = window.innerWidth;
            canvas.height = window.innerHeight;
        }}
        resizeCanvas();
        window.addEventListener('resize', resizeCanvas);

        // Compute static layout using hierarchical positioning
        function computeStaticLayout(nodes, edges) {{
            // Find root node (most connections or specific type)
            let rootNode = nodes.find(n => n.type === 'NWBFile');
            if (!rootNode) {{
                rootNode = nodes[0];
            }}

            // Build adjacency list
            const adj = {{}};
            nodes.forEach(n => adj[n.id] = []);
            edges.forEach(e => {{
                if (!adj[e.source]) adj[e.source] = [];
                adj[e.source].push(e.target);
            }});

            // BFS to assign levels
            const levels = {{}};
            const queue = [rootNode.id];
            levels[rootNode.id] = 0;
            const visited = new Set([rootNode.id]);

            while (queue.length > 0) {{
                const current = queue.shift();
                const currentLevel = levels[current];

                if (adj[current]) {{
                    adj[current].forEach(neighbor => {{
                        if (!visited.has(neighbor)) {{
                            visited.add(neighbor);
                            levels[neighbor] = currentLevel + 1;
                            queue.push(neighbor);
                        }}
                    }});
                }}
            }}

            // Assign unconnected nodes to max level + 1
            const maxLevel = Math.max(...Object.values(levels));
            nodes.forEach(n => {{
                if (!(n.id in levels)) {{
                    levels[n.id] = maxLevel + 1;
                }}
            }});

            // Group nodes by level
            const nodesByLevel = {{}};
            nodes.forEach(n => {{
                const level = levels[n.id];
                if (!nodesByLevel[level]) nodesByLevel[level] = [];
                nodesByLevel[level].push(n);
            }});

            // Calculate positions
            const width = canvas.width;
            const height = canvas.height;
            const levelCount = Object.keys(nodesByLevel).length;
            const verticalSpacing = height / (levelCount + 1);

            Object.keys(nodesByLevel).forEach(level => {{
                const nodesAtLevel = nodesByLevel[level];
                const horizontalSpacing = width / (nodesAtLevel.length + 1);

                nodesAtLevel.forEach((node, index) => {{
                    node.x = horizontalSpacing * (index + 1);
                    node.y = verticalSpacing * (parseInt(level) + 1);
                    node.radius = 25;
                }});
            }});

            return nodes;
        }}

        let nodes = computeStaticLayout(graphData.nodes, graphData.edges);

        let edges = graphData.edges;

        // Transform state
        let scale = 1.0;
        let offsetX = 0;
        let offsetY = 0;
        let isDragging = false;
        let dragStart = {{ x: 0, y: 0 }};
        let selectedNode = null;

        // Color mapping for node types
        function getNodeColor(type) {{
            const colorMap = {{
                'NWBFile': '#5b8fc9',           // Blue (central node)
                'Group': '#6ab04c',             // Green
                'General': '#6ab04c',           // Green
                'TimeSeries': '#e17055',        // Red/Orange
                'Device': '#6ab04c',            // Green
                'ElectrodeGroup': '#e17055',    // Red
                'Subject': '#9b59b6',           // Purple
                'Analysis': '#f39c12',          // Orange
                'ProcessingModule': '#f39c12',  // Orange
                'Electrodes': '#e17055'         // Red
            }};
            return colorMap[type] || '#95a5a6';  // Gray default
        }}

        // Zoom functions
        function zoomIn() {{
            scale *= 1.2;
            draw();
        }}

        function zoomOut() {{
            scale /= 1.2;
            draw();
        }}

        function resetView() {{
            scale = 1.0;
            offsetX = 0;
            offsetY = 0;
            draw();
        }}

        // Mouse wheel zoom
        canvas.addEventListener('wheel', (e) => {{
            e.preventDefault();
            const delta = e.deltaY > 0 ? 0.9 : 1.1;
            const rect = canvas.getBoundingClientRect();
            const mouseX = e.clientX - rect.left;
            const mouseY = e.clientY - rect.top;

            const oldScale = scale;
            scale *= delta;
            offsetX = mouseX - (mouseX - offsetX) * (scale / oldScale);
            offsetY = mouseY - (mouseY - offsetY) * (scale / oldScale);
            draw();
        }});

        // Mouse drag
        canvas.addEventListener('mousedown', (e) => {{
            isDragging = true;
            dragStart = {{ x: e.clientX - offsetX, y: e.clientY - offsetY }};
        }});

        canvas.addEventListener('mousemove', (e) => {{
            if (isDragging) {{
                offsetX = e.clientX - dragStart.x;
                offsetY = e.clientY - dragStart.y;
                draw();
            }}

            // Tooltip
            const rect = canvas.getBoundingClientRect();
            const mouseX = (e.clientX - rect.left - offsetX) / scale;
            const mouseY = (e.clientY - rect.top - offsetY) / scale;

            let hoverNode = null;
            for (const node of nodes) {{
                const dx = mouseX - node.x;
                const dy = mouseY - node.y;
                if (Math.sqrt(dx*dx + dy*dy) < node.radius) {{
                    hoverNode = node;
                    break;
                }}
            }}

            if (hoverNode) {{
                tooltip.style.display = 'block';
                tooltip.style.left = (e.clientX + 10) + 'px';
                tooltip.style.top = (e.clientY + 10) + 'px';
                tooltip.innerHTML = `<strong>${{hoverNode.label}}</strong><br>Type: ${{hoverNode.type}}`;
                canvas.style.cursor = 'pointer';
            }} else {{
                tooltip.style.display = 'none';
                canvas.style.cursor = isDragging ? 'grabbing' : 'grab';
            }}
        }});

        canvas.addEventListener('mouseup', () => {{
            isDragging = false;
        }});

        canvas.addEventListener('mouseleave', () => {{
            isDragging = false;
            tooltip.style.display = 'none';
        }});


        // Draw function
        function draw() {{
            ctx.clearRect(0, 0, canvas.width, canvas.height);

            ctx.save();
            ctx.translate(offsetX, offsetY);
            ctx.scale(scale, scale);

            // Draw edges
            ctx.strokeStyle = '#aaa';
            ctx.lineWidth = 1.5 / scale;
            edges.forEach(edge => {{
                const source = nodes.find(n => n.id === edge.source);
                const target = nodes.find(n => n.id === edge.target);
                if (source && target) {{
                    // Calculate arrow
                    const dx = target.x - source.x;
                    const dy = target.y - source.y;
                    const angle = Math.atan2(dy, dx);
                    const dist = Math.sqrt(dx*dx + dy*dy);

                    // Shorten to node edge
                    const endX = target.x - Math.cos(angle) * target.radius;
                    const endY = target.y - Math.sin(angle) * target.radius;

                    // Draw line
                    ctx.beginPath();
                    ctx.moveTo(source.x, source.y);
                    ctx.lineTo(endX, endY);
                    ctx.stroke();

                    // Draw arrowhead
                    const arrowSize = 8 / scale;
                    ctx.beginPath();
                    ctx.moveTo(endX, endY);
                    ctx.lineTo(
                        endX - arrowSize * Math.cos(angle - Math.PI / 7),
                        endY - arrowSize * Math.sin(angle - Math.PI / 7)
                    );
                    ctx.lineTo(
                        endX - arrowSize * Math.cos(angle + Math.PI / 7),
                        endY - arrowSize * Math.sin(angle + Math.PI / 7)
                    );
                    ctx.closePath();
                    ctx.fillStyle = '#aaa';
                    ctx.fill();
                }}
            }});

            // Draw nodes
            nodes.forEach(node => {{
                // Node circle with shadow
                ctx.shadowColor = 'rgba(0, 0, 0, 0.2)';
                ctx.shadowBlur = 4 / scale;
                ctx.shadowOffsetX = 2 / scale;
                ctx.shadowOffsetY = 2 / scale;

                ctx.beginPath();
                ctx.arc(node.x, node.y, node.radius / scale, 0, Math.PI * 2);
                ctx.fillStyle = getNodeColor(node.type);
                ctx.fill();

                ctx.shadowColor = 'transparent';
                ctx.strokeStyle = '#fff';
                ctx.lineWidth = 2 / scale;
                ctx.stroke();

                // Label
                ctx.fillStyle = '#333';
                ctx.font = `${{12 / scale}}px Arial`;
                ctx.textAlign = 'center';
                ctx.fillText(node.label, node.x, node.y + node.radius / scale + 15 / scale);
            }});

            ctx.restore();
        }}

        // Initial draw (static)
        draw();

        // Redraw on interaction
        window.addEventListener('resize', () => {{
            resizeCanvas();
            nodes = computeStaticLayout(graphData.nodes, graphData.edges);
            draw();
        }});
    </script>
</body>
</html>"""

    return html