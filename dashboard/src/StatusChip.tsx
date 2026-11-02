import type { ClaimStatus } from "./api";
import { STATUS_LABELS } from "./format";

export function StatusChip({ status }: Readonly<{ status: ClaimStatus }>) {
  return <span className={`chip chip-${status}`}>{STATUS_LABELS[status]}</span>;
}
