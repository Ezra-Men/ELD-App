import React from "react";
import { MapContainer, TileLayer, Polyline, Marker, Popup } from "react-leaflet";
import L from "leaflet";
import "leaflet/dist/leaflet.css";

delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png",
  iconUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png",
  shadowUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png",
});

export default function RouteMap({ route }) {
  if (!route || !route.coordinates || route.coordinates.length === 0) {
    return <div className="text-sm text-gray-500">No route to display yet.</div>;
  }

  const latlngs = route.coordinates.map(([lon, lat]) => [lat, lon]);
  const mid = latlngs[Math.floor(latlngs.length / 2)] || latlngs[0];

  return (
    <div className="h-96 rounded-xl overflow-hidden">
      <MapContainer
        center={mid}
        zoom={5}
        style={{ height: "100%", width: "100%" }}
        scrollWheelZoom={false}
      >
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/">OpenStreetMap</a>'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />
        <Polyline positions={latlngs} weight={5} color="#2563eb" />
        {(route.stops || []).map((s, idx) => (
          <Marker key={idx} position={[s.lat, s.lon]}>
            <Popup>
              <div className="text-sm">
                <strong>{s.type}</strong>
                <div>
                  {s.lat.toFixed(4)}, {s.lon.toFixed(4)}
                </div>
              </div>
            </Popup>
          </Marker>
        ))}
      </MapContainer>
    </div>
  );
}
