# System Architecture

## 1. Dual-Graph Routing Model
The routing engine operates on two graph layers:
1. **Abstract City Graph (`NetworkX`):** Models 10 major collection points in Berhampur with precomputed road distances (in km). All-pairs shortest paths and distances are computed at startup using **Floyd-Warshall** and **Dijkstra** algorithms.
2. **Real Street Network (`OSMnx`):** Maps abstract node-to-node hops onto actual drivable OpenStreetMap road geometry (`osm_graph.graphml`) for realistic polyline rendering in Leaflet.js.

## 2. Dispatch Priority Logic
Each 5-second simulation tick advances bin saturation using stochastic mean fill rates:
- **Tier 1 (Critical Civic Zones):** Railway Station, MKCG Hospital, New Bus Stand, and City Hospital are dispatched immediately upon reaching `>= 70%` fill level.
- **Tier 2 (Predictive Overflow):** Secondary zones are dispatched when projected next-cycle levels reach `>= 100%`.
- **En-Route Opportunistic Pickup:** Any bin along the computed tour with `>= 70%` fill level is emptied if remaining truck payload (`5,000 kg` max) permits.