export type ClaimStatus =
  "waiting" | "in_progress" | "waiting_for_sign_off" | "decided";

export type DecisionKind = "approve" | "decline" | "refer";

export interface QueueClaim {
  claim_id: string;
  customer_name: string;
  claim_type: string;
  amount_claimed: number;
  submitted_on: string;
  status: ClaimStatus;
  decision: DecisionKind | null;
  payout: number | null;
  amount_paid: number | null;
}

export interface Item {
  description: string;
  category: string;
  amount: number;
}

export interface ClaimDocument {
  name: string;
  type: string;
  content: string;
}

export interface Decision {
  decision: DecisionKind;
  payout: number;
  reason: string;
  policy_section: string;
  decided_at: string;
}

export interface SignOff {
  handler_id: string;
  handler_name: string;
  signed_off_at: string;
}

export interface Payment {
  amount: number;
  paid_at: string;
}

export interface Claim {
  claim_id: string;
  policy_id: string;
  customer_id: string;
  customer_name: string;
  claim_type: string;
  submitted_on: string;
  incident_date: string;
  incident_location: string;
  summary: string;
  story: string;
  items: Item[];
  amount_claimed: number;
  documents: ClaimDocument[];
  status: ClaimStatus;
  decision: Decision | null;
  sign_off: SignOff | null;
  payment: Payment | null;
}

export interface PlanDetails {
  name: string;
  trip_cancellation_max: number;
  trip_delay_waiting_hours: number;
  trip_delay_max: number;
  baggage_delay_waiting_hours: number;
  baggage_delay_max: number;
  baggage_max: number;
  per_item_limit: number;
  passport_max: number;
  emergency_medical_max: number;
  deductible: number;
}

export interface Policy {
  policy_id: string;
  purchased_on: string;
  trip: {
    destination: string;
    departs_on: string;
    returns_on: string;
    trip_cost: number;
  };
  travelers: string[];
  plan_details: PlanDetails;
  add_on_details: { add_on: string; name: string }[];
}

export interface PreviousClaim {
  claim_id: string;
  incident_date: string;
  summary: string;
  outcome: string;
  amount_paid: number;
}

export interface Customer {
  customer_id: string;
  name: string;
  customer_since: string;
  previous_claims: PreviousClaim[];
}

export interface Handler {
  handler_id: string;
  name: string;
  role: string;
  can_approve_over_limit: boolean;
}

export interface Step {
  step_id: number;
  thread_id: string;
  text: string;
  created_at: string;
}

async function failureMessage(response: Response): Promise<string> {
  try {
    const body = (await response.json()) as { detail: string };
    return body.detail;
  } catch {
    return "The backend did not respond";
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, init);
  if (!response.ok) throw new Error(await failureMessage(response));
  return (await response.json()) as T;
}

function post<T>(path: string, body?: unknown): Promise<T> {
  return request<T>(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

export const api = {
  listClaims: () => request<QueueClaim[]>("/api/claims"),
  getClaim: (claimId: string) => request<Claim>(`/api/claims/${claimId}`),
  getPolicy: (policyId: string) => request<Policy>(`/api/policies/${policyId}`),
  getCustomer: (customerId: string) =>
    request<Customer>(`/api/customers/${customerId}`),
  getInstructions: () => request<{ text: string }>("/api/instructions"),
  listHandlers: () => request<Handler[]>("/api/handlers"),
  listSteps: (claimId: string) =>
    request<Step[]>(`/api/claims/${claimId}/steps`),
  runAgent: (claimId: string) =>
    post<{ status: string }>(`/api/claims/${claimId}/agent-run`),
  workQueue: () => post<{ started: number }>("/api/queue/agent-run"),
  signOff: (claimId: string, handlerId: string) =>
    post<{ status: string }>(`/api/claims/${claimId}/sign-off`, {
      handler_id: handlerId,
    }),
};
