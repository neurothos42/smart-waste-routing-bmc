// No need of this file

let map = L.map("map").setView([19.3105, 84.7914], 14);

L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
  maxZoom: 19,
}).addTo(map);

let binMarkers = [];
let truckMarker = null;
let routeLine = null;
let truckCoords = [];
let truckIndex = 0;
let isAnimating = false;

// 🎯 Color for bin marker based on Flask logic
function getCircleColor(status) {
  return (
    {
      green: "#2ecc71",
      yellow: "#f1c40f",
      red: "#e74c3c",
      orange: "#e67e22",
      purple: "#9b59b6",
    }[status] || "#3498db"
  );
}

// 🟢 Update bins as colored circle markers
function updateBinMarkers(bins) {
  binMarkers.forEach((marker) => map.removeLayer(marker));
  binMarkers = [];

  bins.forEach((bin) => {
    const circle = L.circleMarker([bin.lat, bin.lng], {
      radius: 10,
      color: getCircleColor(bin.status),
      fillColor: getCircleColor(bin.status),
      fillOpacity: 0.9,
    }).bindPopup(`<b>${bin.name}</b><br>Status: ${bin.status}`);
    circle.addTo(map);
    binMarkers.push(circle);
  });
}

// 🔵 Draw route polyline
function drawRouteLine(coords) {
  if (routeLine) map.removeLayer(routeLine);
  routeLine = L.polyline(coords, { color: "blue", weight: 4 }).addTo(map);
  map.fitBounds(routeLine.getBounds());
}

// 🚛 Setup truck marker
function initTruckMarker(coords) {
  if (truckMarker) map.removeLayer(truckMarker);
  truckMarker = L.circleMarker(coords[0], {
    radius: 12,
    color: "#34495e",
    fillColor: "#34495e",
    fillOpacity: 1,
  })
    .bindPopup("🚛 Waste Truck")
    .addTo(map);
}

// 🚚 Animate truck movement with callback on finish
function animateTruck(onComplete) {
  if (!truckCoords || truckIndex >= truckCoords.length) {
    isAnimating = false;
    if (onComplete) onComplete(); // Trigger callback after truck finishes
    return;
  }

  truckMarker.setLatLng(truckCoords[truckIndex]);
  truckIndex++;

  setTimeout(() => animateTruck(onComplete), 200); // Adjust speed
}

// 🔁 Update every cycle
function fetchAndUpdate() {
  if (isAnimating) return; // Don't trigger another update during animation

  // First trigger simulation logic (and bin waste updates)
  fetch("/graph-data")
    .then(() => fetch("/map-data"))
    .then((res) => res.json())
    .then((data) => {
      if (!data.route_coords || data.route_coords.length === 0) {
        console.log("🟡 No route this cycle.");
        updateBinMarkers(data.bins); // still refresh bin colors
        return;
      }

      updateBinMarkers(data.bins);
      drawRouteLine(data.route_coords);

      truckCoords = data.route_coords.map((p) => [p.lat, p.lng]);
      truckIndex = 0;
      initTruckMarker(truckCoords);

      isAnimating = true;
      animateTruck(() => {
        // ✅ After truck finishes route, refresh colors again
        fetch("/map-data")
          .then((res) => res.json())
          .then((updated) => {
            updateBinMarkers(updated.bins);
          });
      });
    })
    .catch((err) => console.error("Update failed:", err));
}

// ⏲️ Start simulation cycle every 5 seconds
setInterval(fetchAndUpdate, 5000);

// Initial call
fetchAndUpdate();
