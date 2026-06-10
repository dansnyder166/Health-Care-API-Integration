import { useQuery } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";
import { fetchPatient } from "../api/client";
import { formatDate } from "../utils/formatDate";

export default function PatientDetail() {
  const { teamSlug, patientId } = useParams<{
    teamSlug: string;
    patientId: string;
  }>();

  const { data: patient, isLoading, error } = useQuery({
    queryKey: ["patient", teamSlug, patientId],
    queryFn: () => fetchPatient(teamSlug!, patientId!),
  });

  if (isLoading) return <p className="text-gray-500">Loading patient...</p>;
  if (error) return <p className="text-red-600">Error loading patient.</p>;
  if (!patient) return null;

  return (
    <div className="space-y-8">
      <Link
        to={`/teams/${teamSlug}/patients`}
        className="text-sm text-blue-600 hover:text-blue-800"
      >
        &larr; Back to patient list
      </Link>

      <div className="bg-white shadow rounded-lg p-6">
        <h2 className="text-lg font-medium text-gray-900">{patient.name}</h2>
        <dl className="mt-2 grid grid-cols-3 gap-4 text-sm">
          <div>
            <dt className="text-gray-500">MRN</dt>
            <dd className="text-gray-900">{patient.mrn}</dd>
          </div>
          <div>
            <dt className="text-gray-500">Date of Birth</dt>
            <dd className="text-gray-900">{patient.date_of_birth}</dd>
          </div>
          <div>
            <dt className="text-gray-500">Team</dt>
            <dd className="text-gray-900">{patient.team_name}</dd>
          </div>
        </dl>
      </div>

      {/* Allergies */}
      <div className="bg-white shadow rounded-lg p-6">
        <h3 className="text-md font-medium text-gray-900 mb-3">Allergies</h3>
        {patient.allergies.length === 0 ? (
          <p className="text-sm text-gray-500">No known allergies</p>
        ) : (
          <ul className="divide-y divide-gray-100">
            {patient.allergies.map((allergy) => (
              <li key={allergy.id} className="py-2 flex justify-between text-sm">
                <span className="text-gray-900">{allergy.substance}</span>
                <span className="text-gray-500 capitalize">
                  {allergy.criticality ?? "—"}
                </span>
              </li>
            ))}
          </ul>
        )}
      </div>

      {/* Lab Results */}
      <div className="bg-white shadow rounded-lg overflow-hidden">
        <div className="p-6 pb-0">
          <h3 className="text-md font-medium text-gray-900 mb-3">
            Lab Results
          </h3>
        </div>
        {patient.lab_results.length === 0 ? (
          <p className="p-6 pt-0 text-sm text-gray-500">No lab results</p>
        ) : (
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                  Test
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                  Result
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                  Date
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                  Accession #
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {patient.lab_results.map((result) => (
                <tr key={result.id}>
                  <td className="px-6 py-3 whitespace-nowrap text-sm text-gray-900">
                    {result.test_name}
                  </td>
                  <td className="px-6 py-3 whitespace-nowrap text-sm text-gray-900">
                    {result.value} {result.unit}
                  </td>
                  <td className="px-6 py-3 whitespace-nowrap text-sm text-gray-700">
                    {formatDate(result.effective_date)}
                  </td>
                  <td className="px-6 py-3 whitespace-nowrap text-sm text-gray-500">
                    {result.accession_number}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
