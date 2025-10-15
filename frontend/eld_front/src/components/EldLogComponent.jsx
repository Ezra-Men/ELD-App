// src/components/EldLogComponent.jsx
import React from 'react';

/**
 * EldLogComponent - Displays ELD log sheets
 * @param {Array} eldLogs - Array of ELD log objects with day and image_url
 */
const EldLogComponent = ({ eldLogs }) => {
  // Display message if no logs are available
  if (!eldLogs || eldLogs.length === 0) {
    return (
      <div className="bg-white p-6 rounded-lg shadow-md text-center">
        <p className="text-gray-500">No ELD logs available. Plan a trip to generate logs.</p>
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
      {eldLogs.map((log, index) => (
        <div key={index} className="bg-white p-4 rounded-lg shadow-md border border-gray-200">
          <h3 className="text-lg font-semibold text-gray-700 mb-2">Day {log.day}</h3>
          <img src={log.image_url} alt={`ELD Log ${log.day}`} className="w-full rounded-lg" />
        </div>
      ))}
    </div>
  );
};

export default EldLogComponent;