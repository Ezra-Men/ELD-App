import React from "react";
import TripForm from "./components/TripForm";

export default function App() {
  return (
    <div className="min-h-screen bg-gray-100 text-gray-800 flex flex-col">
      {/* Header */}
      <header className="bg-gradient-to-r from-blue-600 to-blue-500 text-white shadow-md p-6 rounded-b-2xl">
        <div className="max-w-6xl mx-auto">
          <h1 className="text-3xl font-bold tracking-tight">ELD Trip Planner</h1>
          <p className="text-sm text-blue-100 mt-1">
            Built for Spotter AI Coding Assessment
          </p>
        </div>
      </header>

      {/* Main Content */}
      <main className="flex-1 max-w-6xl mx-auto w-full px-4 sm:px-6 lg:px-8 py-10 space-y-10">
        <TripForm />
      </main>

      {/* Footer */}
      <footer className="text-center text-sm text-gray-500 py-6 border-t mt-8">
        © {new Date().getFullYear()} Ezra Joseph.
      </footer>
    </div>
  );
}
