import React from "react";

export default function LogViewer({ logs }) {
  if (!logs || logs.length === 0) {
    return <div className="text-sm text-gray-500">No ELD logs yet. After planning a trip, generated PNGs will appear here.</div>;
  }

  return (
    <div className="space-y-4">
      {logs.map((l) => (
        <div key={l.day} className="border rounded p-2">
          <div className="flex items-center justify-between mb-2">
            <div className="font-medium">{l.day}</div>
            <a className="text-xs text-blue-600" href={l.image_url} target="_blank" rel="noreferrer">Open image</a>
          </div>
          <img src={l.image_url} alt={`eld-log-${l.day}`} className="w-full object-contain max-h-72 rounded" />
        </div>
      ))}
    </div>
  );
}
