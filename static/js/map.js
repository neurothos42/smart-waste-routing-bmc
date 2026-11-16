document.addEventListener("DOMContentLoaded", function () {
  const map = L.map("map").setView([19.31, 84.79], 14);

  // Load OpenStreetMap tile layer
  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    attribution: "&copy; OpenStreetMap contributors",
  }).addTo(map);

  let routeLayer = null;
  let markerLayers = [];

  function updateMap() {
    fetch("/map-data")
      .then((res) => res.json())
      .then((data) => {
        // Clear previous layers
        markerLayers.forEach((marker) => map.removeLayer(marker));
        markerLayers = [];

        if (routeLayer) {
          map.removeLayer(routeLayer);
          routeLayer = null;
        }

        const statusColors = {
          green: "green",
          yellow: "yellow",
          red: "red",
          purple: "purple",
          orange: "orange", // only if used by backend
        };

        // Draw bin markers
        data.bins.forEach((bin) => {
          const color = statusColors[bin.status] || "gray";
          const marker = L.circleMarker([bin.lat, bin.lng], {
            radius: 8,
            color: color,
            fillColor: color,
            fillOpacity: 0.9,
          }).addTo(map);

          // Highlight BISWM in a different way (e.g., larger radius or thicker border)
          if (bin.status === "purple") {
            marker.setStyle({
              radius: 10,
              weight: 3,
              color: "#800080", // darker purple border
              fillColor: "#DA70D6", // lighter purple fill
              fillOpacity: 0.95,
            });
          }

          marker.bindPopup(
            `<strong>${bin.name}</strong><br>Status: ${bin.status}`,
          );
          markerLayers.push(marker);
        });

        // Draw truck route using real OSM coordinates
        const latlngs = data.route_coords;
        if (latlngs && latlngs.length > 1) {
          routeLayer = L.polyline(latlngs, {
            color: "blue",
            weight: 4,
            opacity: 0.8,
            smoothFactor: 1,
          }).addTo(map);

          map.fitBounds(routeLayer.getBounds());
        }
      })
      .catch((err) => console.error("Map update error:", err));
  }

  updateMap();
  setInterval(updateMap, 5000); // Refresh every 5 seconds
});
