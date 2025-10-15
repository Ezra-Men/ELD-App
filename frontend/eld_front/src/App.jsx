import './App.css'
import React, { useState } from 'react';
import MapComponent from './components/MapComponent';
import EldLogComponent from './components/EldLogComponent';

function App() {
  const [formData, setFormData] = useState({
    currentLocation: 'Chicago, IL',
    pickupLocation: 'St. Louis, MO',
    dropoffLocation: 'Dallas, TX',
    cycleHours: 20
  });
  const [route, setRoute] = useState(null);
  const [eldLogs, setEldLogs] = useState([]);
  const [mapInstance, setMapInstance] = useState(null);

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: name === 'cycleHours' ? parseFloat(value) || 0 : value
    }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      const response = await fetch('http://localhost:8000/api/trips/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(formData)
      });
      const data = await response.json();
      setRoute(data.route);
      setEldLogs(data.eld_logs);
    } catch (error) {
      console.error('Error fetching trip data:', error);
    }
  };

  const handleMapReady = (map) => {
    setMapInstance(map);
  };

  const handleReset = () => {
    setFormData({
      currentLocation: '',
      pickupLocation: '',
      dropoffLocation: '',
      cycleHours: 0
    });
    setRoute(null);
    setEldLogs([]);
    if (mapInstance) {
      mapInstance.setView([39.8283, -98.5795], 4);
    }
  };

  return (
    <div className="container mx-auto p-4 bg-gray-100 min-h-screen">
      <h1 className="text-3xl font-bold mb-6 text-center text-blue-800">Trip Planner</h1>
      <form onSubmit={handleSubmit} className="mb-6 p-4 bg-white rounded-lg shadow-md">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <input
            type="text"
            name="currentLocation"
            placeholder="Current Location"
            value={formData.currentLocation}
            onChange={handleInputChange}
            className="border p-2 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
          <input
            type="text"
            name="pickupLocation"
            placeholder="Pickup Location"
            value={formData.pickupLocation}
            onChange={handleInputChange}
            className="border p-2 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
          <input
            type="text"
            name="dropoffLocation"
            placeholder="Dropoff Location"
            value={formData.dropoffLocation}
            onChange={handleInputChange}
            className="border p-2 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
          <input
            type="number"
            name="cycleHours"
            placeholder="Cycle Hours Used"
            value={formData.cycleHours}
            onChange={handleInputChange}
            className="border p-2 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>
        <div className="mt-4 flex gap-2">
          <button type="submit" className="bg-blue-600 text-white p-2 rounded-lg hover:bg-blue-700">
            Plan Trip
          </button>
          <button type="button" onClick={handleReset} className="bg-gray-500 text-white p-2 rounded-lg hover:bg-gray-600">
            Reset
          </button>
        </div>
      </form>
      <div className="mb-6">
        <MapComponent route={route} onMapReady={handleMapReady} />
      </div>
      <h2 className="text-2xl font-bold mb-4 text-blue-800">ELD Logs</h2>
      <div className="mb-6">
        <EldLogComponent eldLogs={eldLogs} />
      </div>
    </div>
  );
}

export default App;
