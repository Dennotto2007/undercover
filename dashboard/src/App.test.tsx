import {
  cleanup,
  fireEvent,
  render,
  screen,
  within,
} from "@testing-library/react";
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

const posted: { url: string; body: RequestInit["body"] }[] = [];

function reply(url: string, init?: RequestInit): Promise<Response> {
  const key = init?.method === "POST" ? `POST ${url}` : url;
  if (init?.method === "POST") posted.push({ url, body: init.body });
  if (key in responses) {
    return Promise.resolve(new Response(JSON.stringify(responses[key])));
  }
  return Promise.resolve(
    new Response(JSON.stringify({ detail: "Not found" }), { status: 404 }),
  );
}

function renderAt(hash: string): void {
  window.location.hash = hash;
  render(<App />);
}

const steps = [
  {
    step_id: 1,
    thread_id: "t1",
    text: "Reading the claim",
    created_at: "2026-11-02T10:00:00+00:00",
  },
];

const waitingClaim: Claim = {
  ...claim,
  status: "waiting",
  decision: null,
  sign_off: null,
  payment: null,
};

const signOffClaim: Claim = {
  ...claim,
  status: "waiting_for_sign_off",
  sign_off: null,
  payment: null,
};

beforeEach(() => {
  posted.length = 0;
  responses = {
    "/api/claims/CLM-1001/steps": steps,
    "/api/handlers": [
      {
        handler_id: "HND-01",
        name: "Dana Whitfield",
        role: "Senior Claims Handler",
        can_approve_over_limit: true,
      },
      {
        handler_id: "HND-02",
        name: "Marcus Oyelaran",
        role: "Claims Handler",
        can_approve_over_limit: false,
      },
    ],
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
  responses["/api/claims/CLM-1001"] = waitingClaim;
  responses["/api/claims/CLM-1001/steps"] = [];
  responses["/api/customers/CUS-3001"] = { ...customer, previous_claims: [] };
  renderAt("#/claims/CLM-1001");
  expect(
    await screen.findByText("The agent has not decided this claim yet."),
  ).toBeDefined();
  expect(await screen.findByText("No earlier claims.")).toBeDefined();
  expect(
    screen.getByText("The agent has not worked on this claim yet."),
  ).toBeDefined();
});

it("shows the agent's steps", async () => {
  renderAt("#/claims/CLM-1001");
  expect(await screen.findByText("Reading the claim")).toBeDefined();
});

it("runs the agent once on a waiting claim", async () => {
  responses["/api/claims/CLM-1001"] = waitingClaim;
  responses["POST /api/claims/CLM-1001/agent-run"] = { status: "queued" };
  renderAt("#/claims/CLM-1001");
  fireEvent.click(await screen.findByRole("button", { name: "Run agent" }));
  const queued = await screen.findByRole("button", {
    name: "Queued for the agent",
  });
  expect((queued as HTMLButtonElement).disabled).toBe(true);
  expect(posted).toEqual([
    { url: "/api/claims/CLM-1001/agent-run", body: undefined },
  ]);
});

it("offers no agent run or sign-off on a decided claim", async () => {
  renderAt("#/claims/CLM-1001");
  await screen.findByText("Approved");
  expect(screen.queryByRole("button")).toBeNull();
  expect(screen.queryByRole("combobox")).toBeNull();
});

it("signs off a claim with the chosen handler", async () => {
  responses["/api/claims/CLM-1001"] = signOffClaim;
  responses["POST /api/claims/CLM-1001/sign-off"] = { status: "decided" };
  renderAt("#/claims/CLM-1001");
  const button = await screen.findByRole("button", {
    name: "Sign off and pay",
  });
  expect((button as HTMLButtonElement).disabled).toBe(true);
  await screen.findByRole("option", { name: "Dana Whitfield" });
  expect(screen.queryByRole("option", { name: "Marcus Oyelaran" })).toBeNull();
  fireEvent.change(screen.getByLabelText("Handler"), {
    target: { value: "HND-01" },
  });
  fireEvent.click(button);
  await vi.waitFor(() => {
    expect(posted).toEqual([
      {
        url: "/api/claims/CLM-1001/sign-off",
        body: JSON.stringify({ handler_id: "HND-01" }),
      },
    ]);
  });
});

it("shows why a sign-off failed", async () => {
  responses["/api/claims/CLM-1001"] = signOffClaim;
  renderAt("#/claims/CLM-1001");
  await screen.findByRole("option", { name: "Dana Whitfield" });
  fireEvent.change(screen.getByLabelText("Handler"), {
    target: { value: "HND-01" },
  });
  fireEvent.click(screen.getByRole("button", { name: "Sign off and pay" }));
  expect((await screen.findByRole("alert")).textContent).toBe("Not found");
});

it("works the queue and says how many claims it queued", async () => {
  responses["POST /api/queue/agent-run"] = { started: 1 };
  renderAt("#/");
  fireEvent.click(
    await screen.findByRole("button", { name: "Work the queue" }),
  );
  expect((await screen.findByRole("status")).textContent).toBe(
    "1 claim queued for the agent",
  );
});

it("shows a plain message when the backend does not respond", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn(() => Promise.resolve(new Response("oops", { status: 500 }))),
  );
  renderAt("#/");
  expect((await screen.findByRole("alert")).textContent).toBe(
    "The backend did not respond",
  );
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
