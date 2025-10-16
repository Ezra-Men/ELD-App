import React, { useState } from "react";
import RouteMap from "./RouteMap";
import LogViewer from "./LogViewer";

const API_BASE = import.meta.env.VITE_API_BASE || ""; // e.g. http://localhost:8000

export default function TripForm() {
  const [currentLocation, setCurrentLocation] = useState("");
  const [pickupLocation, setPickupLocation] = useState("");
  const [dropoffLocation, setDropoffLocation] = useState("");
  const [cycleHours, setCycleHours] = useState(0);
  const [loading, setLoading] = useState(false);
  const [route, setRoute] = useState(null);
  const [eldLogs, setEldLogs] = useState([]);
  const [error, setError] = useState(null);

  async function handleSubmit(e) {
    e.preventDefault();
    setError(null);
    setRoute(null);
    setEldLogs([]);
    setLoading(true);

    try {
      const body = {
        currentLocation,
        pickupLocation,
        dropoffLocation,
        cycleHours: Number(cycleHours || 0),
      };

      const res = await fetch(`${API_BASE}/api/trips/`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });

      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        let message =
          data.api_error?.message ||
          data.error ||
          `Unexpected error (${res.status})`;

        if (message.toLowerCase().includes("routable point")) {
          message =
            "Couldn't find a driving route near one of your locations. Try specifying the city and country (e.g. 'Dallas, TX, USA').";
          }

        throw new Error(message);
}


      const data = await res.json();
      // expected keys: route { coordinates: [[lon,lat],...], stops: [...], distance, duration }, eld_logs [{day, image_url}]
      setRoute(data.route || null);
      setEldLogs(data.eld_logs || []);
    } catch (err) {
      console.error(err);
      setError(err.message || "Unknown error");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="space-y-6">
      <form onSubmit={handleSubmit} className="bg-white p-6 rounded-lg shadow-sm grid grid-cols-1 gap-4 md:grid-cols-3">
        <div className="md:col-span-1">
          <label className="block text-sm font-medium text-gray-700">Current location</label>
          <input value={currentLocation} onChange={(e)=>setCurrentLocation(e.target.value)} placeholder="e.g. Lagos, Nigeria" className="mt-1 block w-full rounded-md border-gray-300 shadow-sm" />
        </div>

        <div className="md:col-span-1">
          <label className="block text-sm font-medium text-gray-700">Pickup location</label>
          <input value={pickupLocation} onChange={(e)=>setPickupLocation(e.target.value)} placeholder="Pickup address / city" className="mt-1 block w-full rounded-md border-gray-300 shadow-sm" />
        </div>

        <div className="md:col-span-1">
          <label className="block text-sm font-medium text-gray-700">Dropoff location</label>
          <input value={dropoffLocation} onChange={(e)=>setDropoffLocation(e.target.value)} placeholder="Dropoff address / city" className="mt-1 block w-full rounded-md border-gray-300 shadow-sm" />
        </div>

        <div className="md:col-span-1">
          <label className="block text-sm font-medium text-gray-700">Cycle hours used (hrs)</label>
          <input type="number" value={cycleHours} onChange={(e)=>setCycleHours(e.target.value)} className="mt-1 block w-full rounded-md border-gray-300 shadow-sm" />
        </div>

        <div className="md:col-span-2 flex items-end">
          <button type="submit" disabled={loading} className="inline-flex items-center px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-60">
            {loading ? "Working..." : "Plan Trip"}
          </button>
          <div className="ml-4 text-sm text-gray-500">Allow ~10-30s for geocoding + route generation</div>
        </div>
      </form>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 p-3 rounded">
          <strong>Error:</strong> {error}
        </div>
      )}

      {route && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div className="bg-white p-4 rounded shadow-sm">
            <h2 className="text-lg font-semibold mb-2">Route</h2>
            <RouteMap route={route} />
            <div className="mt-3 text-sm text-gray-600">
              <div>Total distance: {(route.distance || 0).toFixed(1)} mi</div>
              <div>Estimated duration: {(route.duration || 0).toFixed(1)} hrs</div>
            </div>
          </div>

          <div className="bg-white p-4 rounded shadow-sm">
            <h2 className="text-lg font-semibold mb-2">ELD Logs</h2>
            <LogViewer logs={eldLogs} />
          </div>
        </div>
      )}
    </div>
  );
}
