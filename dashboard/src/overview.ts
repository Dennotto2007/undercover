import type { ClaimStatus, DecisionKind, QueueClaim } from "./api";

export type StatusFilter = ClaimStatus | "all";

export interface Summary {
  total: number;
  approved: number;
  declined: number;
  referred: number;
  notDecided: number;
  awaitingSignOff: number;
  paid: number;
  heldForSignOff: number;
}

export interface TypeCount {
  claimType: string;
  count: number;
  share: number;
}

const sum = (amounts: number[]): number =>
  amounts.reduce((total, amount) => total + amount, 0);

/** Count each outcome. A decision on an in progress claim is not final yet. */
export function summarize(claims: QueueClaim[]): Summary {
  const held = claims.filter((c) => c.status === "waiting_for_sign_off");
  const finished = claims.filter(
    (c) => c.status === "decided" || c.status === "waiting_for_sign_off",
  );
  const count = (kind: DecisionKind): number =>
    finished.filter((c) => c.decision === kind).length;

  return {
    total: claims.length,
    approved: count("approve"),
    declined: count("decline"),
    referred: count("refer"),
    notDecided: claims.length - finished.length,
    awaitingSignOff: held.length,
    paid: sum(claims.map((c) => c.amount_paid ?? 0)),
    heldForSignOff: sum(held.map((c) => c.payout ?? 0)),
  };
}

export function withStatus(
  claims: QueueClaim[],
  status: StatusFilter,
): QueueClaim[] {
  return status === "all" ? claims : claims.filter((c) => c.status === status);
}

/** Count claims by type, largest first. */
export function countByType(claims: QueueClaim[]): TypeCount[] {
  const counts = new Map<string, number>();
  for (const { claim_type: claimType } of claims) {
    counts.set(claimType, (counts.get(claimType) ?? 0) + 1);
  }
  return [...counts]
    .map(([claimType, count]) => ({
      claimType,
      count,
      share: count / claims.length,
    }))
    .sort(
      (a, b) => b.count - a.count || a.claimType.localeCompare(b.claimType),
    );
}
