import React from "react";
import TripForm from "./components/TripForm";

export default function App() {
  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white shadow-sm">
        <div className="max-w-5xl mx-auto px-4 py-4">
          <h1 className="text-xl font-semibold text-gray-800">ELD Trip Planner</h1>
          <p className="text-sm text-gray-500">Django backend · React + Vite frontend</p>
        </div>
      </header>

      <main className="max-w-5xl mx-auto px-4 py-6">
        <TripForm />
      </main>

      <footer className="text-center text-sm text-gray-400 py-6">
        Built for assessment — Ezra
      </footer>
    </div>
  );
}
