import React, { useState } from "react";
import RouteMap from "./RouteMap";
import LogViewer from "./LogViewer";
import { motion } from "framer-motion";

const API_BASE = import.meta.env.VITE_API_BASE || "";

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

        // Friendly fallback message
        if (message.toLowerCase().includes("routable point")) {
          message =
            "Couldn't find a driving route near one of your locations. Try specifying the city and country (e.g. 'Dallas, TX, USA').";
        }

        throw new Error(message);
      }

      const data = await res.json();
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
    <div className="space-y-8">
      {/* Input Form */}
      <motion.form
        onSubmit={handleSubmit}
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4 }}
        className="bg-white p-8 rounded-2xl shadow-md grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6"
      >
        {[
          {
            label: "Current Location",
            value: currentLocation,
            set: setCurrentLocation,
            placeholder: "Dallas, TX, USA",
          },
          {
            label: "Pickup Location",
            value: pickupLocation,
            set: setPickupLocation,
            placeholder: "New York, NY, USA",
          },
          {
            label: "Dropoff Location",
            value: dropoffLocation,
            set: setDropoffLocation,
            placeholder: "Los Angeles, CA, USA",
          },
          {
            label: "Cycle Hours Used (hrs)",
            value: cycleHours,
            set: setCycleHours,
            type: "number",
            placeholder: "e.g. 7",
          },
        ].map((f, i) => (
          <div key={i}>
            <label className="block text-sm font-semibold text-gray-700 mb-1">
              {f.label}
            </label>
            <input
              type={f.type || "text"}
              value={f.value}
              onChange={(e) => f.set(e.target.value)}
              placeholder={f.placeholder}
              className="w-full rounded-lg border border-gray-300 focus:border-blue-500 focus:ring-blue-500 text-gray-700 p-2.5 shadow-sm"
            />
          </div>
        ))}

        <div className="md:col-span-2 lg:col-span-3 flex justify-center">
          <button
            type="submit"
            disabled={loading}
            className="inline-flex items-center justify-center gap-2 bg-blue-600 hover:bg-blue-700 text-white px-6 py-2.5 rounded-xl font-medium shadow-md transition-all duration-300 disabled:opacity-60"
          >
            {loading ? (
              <>
                <svg
                  className="animate-spin h-5 w-5 text-white"
                  xmlns="http://www.w3.org/2000/svg"
                  fill="none"
                  viewBox="0 0 24 24"
                >
                  <circle
                    className="opacity-25"
                    cx="12"
                    cy="12"
                    r="10"
                    stroke="currentColor"
                    strokeWidth="4"
                  ></circle>
                  <path
                    className="opacity-75"
                    fill="currentColor"
                    d="M4 12a8 8 0 018-8v8z"
                  ></path>
                </svg>
                Calculating Route...
              </>
            ) : (
              "Plan Trip"
            )}
          </button>
        </div>
      </motion.form>

      {/* Error */}
      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 p-4 rounded-lg">
          <strong>Error:</strong> {error}
        </div>
      )}

      {/* Results Grid */}
      {route && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          {/* Map */}
          <div className="bg-white p-6 rounded-2xl shadow-md">
            <h2 className="text-lg font-semibold text-gray-700 mb-3">
              🗺 Route Overview
            </h2>
            <RouteMap route={route} />
            <div className="mt-4 text-sm text-gray-600">
              <p>
                Total Distance:{" "}
                <span className="font-medium">
                  {route.distance.toFixed(1)} mi
                </span>
              </p>
              <p>
                Estimated Duration:{" "}
                <span className="font-medium">
                  {route.duration.toFixed(1)} hrs
                </span>
              </p>
            </div>
          </div>

          {/* Logs */}
          <div className="bg-white p-6 rounded-2xl shadow-md">
            <h2 className="text-lg font-semibold text-gray-700 mb-3">
              📄 Driver Log Sheets
            </h2>
            <LogViewer logs={eldLogs} />
          </div>
        </div>
      )}
    </div>
  );
}
