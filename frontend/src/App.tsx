import { Routes, Route, Navigate } from "react-router-dom";
import PatientList from "./components/PatientList";
import PatientDetail from "./components/PatientDetail";

export default function App() {
  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white border-b border-gray-200 px-6 py-4">
        <h1 className="text-xl font-semibold text-gray-900">
          Lab Results Dashboard
        </h1>
      </header>
      <main className="max-w-6xl mx-auto px-6 py-8">
        <Routes>
          <Route path="/" element={<Navigate to="/teams/lakewood-memorial/patients" replace />} />
          <Route path="/teams/:teamSlug/patients" element={<PatientList />} />
          <Route path="/teams/:teamSlug/patients/:patientId" element={<PatientDetail />} />
        </Routes>
      </main>
    </div>
  );
}
