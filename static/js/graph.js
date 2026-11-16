let graphData = null;

async function fetchGraphData() {
  const res = await fetch("/graph-data");
  graphData = await res.json();
  drawGraph();
}

function drawGraph() {
  const shortLabels = {
    "MKCG Hospital": "MKCG_001",
    BMC: "BMC_002",
    "Khallikote University": "KU_003",
    "Railway Station": "RailS_004",
    "City Hospital": "CityH_005",
    "New Bus Stand": "NewBS_006",
    "Ganesh Market": "GMarket_007",
    "Janata City Centre": "JanataCC_008",
    "Kamapalli Square": "Kamapalli_009",
    BISWM: "BISWM_010",
  };

  // Nodes with position, label, color
  const nodes = Object.entries(graphData.positions).map(([id, pos]) => {
    const label = shortLabels[id] || id;
    const level = graphData.bin_status[id]?.level ?? 0;
    const color = graphData.bin_status[id]?.color ?? "gray";
    return {
      id,
      x: pos[0],
      y: pos[1],
      label: `${label} (${level}%)`,
      color,
    };
  });

  // Default graph edges (gray)
  const edges = graphData.edges.map(([u, v]) => ({
    x: [graphData.positions[u][0], graphData.positions[v][0], null],
    y: [graphData.positions[u][1], graphData.positions[v][1], null],
  }));

  // Route edges (highlighted in blue)
  const routeEdges = graphData.route_edges.map(([u, v]) => ({
    x: [graphData.positions[u][0], graphData.positions[v][0], null],
    y: [graphData.positions[u][1], graphData.positions[v][1], null],
  }));

  const edgeTrace = {
    type: "scatter",
    mode: "lines",
    x: edges.flatMap((e) => e.x),
    y: edges.flatMap((e) => e.y),
    line: { color: "#ccc", width: 2 },
    hoverinfo: "none",
  };

  const routeTrace = {
    type: "scatter",
    mode: "lines",
    x: routeEdges.flatMap((e) => e.x),
    y: routeEdges.flatMap((e) => e.y),
    line: { color: "blue", width: 5 },
    hoverinfo: "none",
  };

  const nodeTrace = {
    type: "scatter",
    mode: "markers+text",
    x: nodes.map((n) => n.x),
    y: nodes.map((n) => n.y),
    text: nodes.map((n) => n.label),
    textposition: "bottom center",
    marker: {
      size: 20,
      color: nodes.map((n) => n.color),
      line: { color: "#333", width: 1 },
    },
    hovertext: nodes.map((n) => `${n.label}<br>Status: ${n.color}`),
    hoverinfo: "text",
  };

  const layout = {
    title: "♻️ Smart Waste Collection - Graph View",
    showlegend: false,
    margin: { l: 20, r: 20, t: 40, b: 20 },
    xaxis: { visible: false, fixedrange: false },
    yaxis: { visible: false, autorange: "reversed", fixedrange: false },
    dragmode: "pan",
    height: 700,
  };

  // Use Plotly.react to update without flicker
  Plotly.react("graph", [edgeTrace, routeTrace, nodeTrace], layout);

  // 🔍 Log the incoming dispatch info from the server
  console.log("📦 Received dispatch info:", graphData.dispatch_info);

  // ✅ Update the dispatch info panel
  const dispatchDiv = document.getElementById("dispatch-info");
  if (dispatchDiv) {
    if (graphData.dispatch_info && graphData.dispatch_info.trim() !== "") {
      dispatchDiv.innerHTML = `<div style="white-space: pre-line; font-family: monospace; margin: 0;">${graphData.dispatch_info}</div>`;
      console.log("✅ Dispatch info updated in DOM.");
    } else {
      dispatchDiv.innerHTML = "🚫 No dispatch info available this cycle.";
      console.warn("⚠️ Dispatch info is empty.");
    }
  } else {
    console.error("❌ dispatch-info div not found in DOM.");
  }
}

// Initial draw + auto update every 5 seconds
fetchGraphData();
setInterval(fetchGraphData, 5000);
