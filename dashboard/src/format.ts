import type { ClaimStatus, DecisionKind } from "./api";

const dollars = new Intl.NumberFormat("en-US", {
  style: "currency",
  currency: "USD",
});

export const money = (amount: number): string => dollars.format(amount);

export const STATUS_LABELS: Record<ClaimStatus, string> = {
  waiting: "Waiting",
  in_progress: "In progress",
  waiting_for_sign_off: "Waiting for sign-off",
  decided: "Decided",
};

export const DECISION_LABELS: Record<DecisionKind, string> = {
  approve: "Approved",
  decline: "Declined",
  refer: "Referred",
};

export function claimTypeLabel(claimType: string): string {
  const words = claimType.replaceAll("_", " ");
  return words.charAt(0).toUpperCase() + words.slice(1);
}
