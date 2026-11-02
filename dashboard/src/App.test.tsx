import { cleanup, render, screen, within } from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import type { Claim, Customer, Policy, QueueClaim } from "./api";
import { App } from "./App";
import { claimTypeLabel, money } from "./format";

const queueClaim: QueueClaim = {
  claim_id: "CLM-1001",
  customer_name: "Maya Patel",
  claim_type: "trip_delay",
  amount_claimed: 420,
  submitted_on: "2026-06-24",
  status: "waiting",
  decision: null,
  payout: null,
};

const claim: Claim = {
  claim_id: "CLM-1001",
  policy_id: "POL-2001",
  customer_id: "CUS-3001",
  customer_name: "Maya Patel",
  claim_type: "trip_delay",
  submitted_on: "2026-06-24",
  incident_date: "2026-06-18",
  incident_location: "Rome, Italy",
  summary: "Flight home canceled",
  story: "My flight home from Rome was canceled.",
  items: [
    { description: "Airport hotel", category: "accommodation", amount: 245 },
  ],
  amount_claimed: 245,
  documents: [{ name: "Hotel receipt", type: "receipt", content: "Paid $245" }],
  status: "decided",
  decision: {
    decision: "approve",
    payout: 245,
    reason: "The delay is covered.",
    policy_section: "Section 3: Trip Delay",
    decided_at: "2026-11-02T10:00:00+00:00",
  },
  sign_off: {
    handler_id: "HND-01",
    handler_name: "Dana Whitfield",
    signed_off_at: "2026-11-02T10:05:00+00:00",
  },
  payment: { amount: 245, paid_at: "2026-11-02T10:05:00+00:00" },
};

const policy: Policy = {
  policy_id: "POL-2001",
  purchased_on: "2026-04-22",
  trip: {
    destination: "Rome, Italy",
    departs_on: "2026-06-10",
    returns_on: "2026-06-18",
    trip_cost: 3100,
  },
  travelers: ["Maya Patel"],
  plan_details: {
    name: "UnderCover Premium",
    trip_cancellation_max: 5000,
    trip_delay_waiting_hours: 6,
    trip_delay_max: 800,
    baggage_delay_waiting_hours: 12,
    baggage_delay_max: 300,
    baggage_max: 1500,
    per_item_limit: 300,
    passport_max: 250,
    emergency_medical_max: 100000,
    deductible: 50,
  },
  add_on_details: [],
};

const customer: Customer = {
  customer_id: "CUS-3001",
  name: "Maya Patel",
  customer_since: "2023-04-11",
  previous_claims: [
    {
      claim_id: "CLM-0412",
      incident_date: "2024-08-09",
      summary: "Checked bag arrived late",
      outcome: "approved",
      amount_paid: 140,
    },
  ],
};

let responses: Record<string, unknown>;

function reply(url: string): Promise<Response> {
  if (url in responses) {
    return Promise.resolve(new Response(JSON.stringify(responses[url])));
  }
  return Promise.resolve(
    new Response(JSON.stringify({ detail: "Not found" }), { status: 404 }),
  );
}

function renderAt(hash: string): void {
  window.location.hash = hash;
  render(<App />);
}

beforeEach(() => {
  responses = {
    "/api/claims": [queueClaim],
    "/api/claims/CLM-1001": claim,
    "/api/policies/POL-2001": policy,
    "/api/customers/CUS-3001": customer,
    "/api/instructions": { text: "You are the UnderCover Agent." },
  };
  vi.stubGlobal("fetch", vi.fn(reply));
});

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

it("formats money and labels", () => {
  expect(money(1250)).toBe("$1,250.00");
  expect(claimTypeLabel("trip_delay")).toBe("Trip delay");
});

it("shows the queue with where each claim stands", async () => {
  renderAt("#/");
  const link = await screen.findByRole("link", { name: "CLM-1001" });
  expect(link.getAttribute("href")).toBe("#/claims/CLM-1001");
  const row = link.closest("tr");
  expect(row).not.toBeNull();
  const cells = within(row as HTMLElement);
  expect(cells.getByText("Maya Patel")).toBeDefined();
  expect(cells.getByText("$420.00")).toBeDefined();
  expect(cells.getByText("Waiting")).toBeDefined();
});

it("shows a decided claim in full", async () => {
  renderAt("#/claims/CLM-1001");
  expect(await screen.findByText("Approved")).toBeDefined();
  expect(screen.getByText("The delay is covered.")).toBeDefined();
  expect(screen.getByText("Section 3: Trip Delay")).toBeDefined();
  expect(screen.getByText("Dana Whitfield")).toBeDefined();
  expect(screen.getByText("Decided")).toBeDefined();
  expect(
    screen.getByText("My flight home from Rome was canceled."),
  ).toBeDefined();
  expect(screen.getByText("Airport hotel")).toBeDefined();
  expect(screen.getByText("Hotel receipt")).toBeDefined();
  expect(await screen.findByText("UnderCover Premium")).toBeDefined();
  expect(await screen.findByText("CLM-0412")).toBeDefined();
});

it("says when a claim has no decision", async () => {
  responses["/api/claims/CLM-1001"] = {
    ...claim,
    status: "waiting",
    decision: null,
    sign_off: null,
    payment: null,
  };
  responses["/api/customers/CUS-3001"] = { ...customer, previous_claims: [] };
  renderAt("#/claims/CLM-1001");
  expect(
    await screen.findByText("The agent has not decided this claim yet."),
  ).toBeDefined();
  expect(await screen.findByText("No earlier claims.")).toBeDefined();
});

it("shows the instructions read only", async () => {
  renderAt("#/instructions");
  expect(
    await screen.findByText("You are the UnderCover Agent."),
  ).toBeDefined();
  expect(screen.queryByRole("textbox")).toBeNull();
  expect(screen.queryByRole("button")).toBeNull();
});

it("shows the reason when a claim cannot be loaded", async () => {
  renderAt("#/claims/CLM-9999");
  expect((await screen.findByRole("alert")).textContent).toBe("Not found");
});
