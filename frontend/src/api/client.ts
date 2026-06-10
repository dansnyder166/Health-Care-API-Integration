const API_BASE = "/api";

export interface Patient {
  id: number;
  mrn: string;
  name: string;
  date_of_birth: string;
  team_name: string;
}

export interface LabResult {
  id: number;
  accession_number: string;
  test_name: string;
  test_code: string;
  value: string;
  unit: string;
  effective_date: string;
  observation_data: Record<string, any>;
}

export interface Allergy {
  id: number;
  substance: string;
  criticality: string | null;
}

export interface PatientDetail extends Patient {
  allergies: Allergy[];
  lab_results: LabResult[];
}

export interface PaginatedResponse<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

export async function fetchPatients(
  teamSlug: string
): Promise<PaginatedResponse<Patient>> {
  const res = await fetch(`${API_BASE}/teams/${teamSlug}/patients/`);
  if (!res.ok) throw new Error("Failed to fetch patients");
  return res.json();
}

export async function fetchPatient(
  teamSlug: string,
  patientId: string
): Promise<PatientDetail> {
  const res = await fetch(
    `${API_BASE}/teams/${teamSlug}/patients/${patientId}/`
  );
  if (!res.ok) throw new Error("Failed to fetch patient");
  return res.json();
}
