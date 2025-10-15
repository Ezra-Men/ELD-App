// src/components/MapComponent.jsx
import React, { useEffect, useRef } from 'react';
import L from 'leaflet';

/**
 * MapComponent - Handles map display and route visualization
 * @param {Object} props
 * @param {Object|null} props.route - Route data containing coordinates and stops
 * @param {Function} props.onMapReady - Callback when map is initialized
 */
const MapComponent = ({ route, onMapReady }) => {
  const mapRef = useRef(null);

  // Initialize or update map
  useEffect(() => {
    // Initialize map if not already created
    if (!mapRef.current) {
      const map = L.map('trip-map').setView([39.8283, -98.5795], 4); // Center on USA
      L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
      }).addTo(map);
      mapRef.current = map;

      if (onMapReady) {
        onMapReady(map);
      }
    }

    return () => {
      if (mapRef.current) {
        mapRef.current.remove();
        mapRef.current = null;
      }
    };
  }, [onMapReady]);

  // Update map when route data changes
  useEffect(() => {
    if (!route || !mapRef.current) return;

    const map = mapRef.current;

    // Clear existing route and markers
    map.eachLayer(layer => {
      if (layer instanceof L.Polyline || layer instanceof L.Marker) {
        map.removeLayer(layer);
      }
    });

    // Add route polyline
    if (route.coordinates && route.coordinates.length > 1) {
      L.polyline(
        route.coordinates.map(coord => [coord[1], coord[0]]), // Convert [lon, lat] to [lat, lon]
        { color: '#FF5733', weight: 4, opacity: 0.8 }
      ).addTo(map);
      map.fitBounds(L.polyline(route.coordinates.map(coord => [coord[1], coord[0]])).getBounds());
    }

    // Add stop markers
    if (route.stops) {
      route.stops.forEach(stop => {
        const icon = L.divIcon({
          className: 'custom-marker',
          html: `<span>${stop.type.charAt(0)}</span>`,
          iconSize: [20, 20],
          iconAnchor: [10, 10]
        });
        L.marker([stop.lat, stop.lon], { icon })
          .addTo(map)
          .bindPopup(stop.type);
      });
    }
  }, [route]);

  return (
    <div id="trip-map" className="w-full h-96 rounded-lg overflow-hidden shadow-md" />
  );
};

export default MapComponent;