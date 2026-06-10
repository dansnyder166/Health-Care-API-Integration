import { useQuery } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";
import { fetchPatients } from "../api/client";

export default function PatientList() {
  const { teamSlug } = useParams<{ teamSlug: string }>();

  const { data, isLoading, error } = useQuery({
    queryKey: ["patients", teamSlug],
    queryFn: () => fetchPatients(teamSlug!),
  });

  if (isLoading) return <p className="text-gray-500">Loading patients...</p>;
  if (error) return <p className="text-red-600">Error loading patients.</p>;

  const patients = data?.results ?? [];

  return (
    <div>
      <h2 className="text-lg font-medium text-gray-900 mb-4">Patients</h2>
      <div className="bg-white shadow rounded-lg overflow-hidden">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                Name
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                MRN
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                Date of Birth
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                Team
              </th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {patients.map((patient) => (
              <tr key={patient.id} className="hover:bg-gray-50">
                <td className="px-6 py-4 whitespace-nowrap">
                  <Link
                    to={`/teams/${teamSlug}/patients/${patient.id}`}
                    className="text-blue-600 hover:text-blue-800"
                  >
                    {patient.name}
                  </Link>
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-700">
                  {patient.mrn}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-700">
                  {patient.date_of_birth}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-700">
                  {patient.team_name}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
