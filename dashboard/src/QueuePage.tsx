import { Alert } from "./Alert";
import { api } from "./api";
import { claimTypeLabel, DECISION_LABELS, money } from "./format";
import { StatusChip } from "./StatusChip";
import { useAction } from "./useAction";
import { usePolled } from "./usePolled";

const claimCount = (count: number): string =>
  count === 1 ? "1 claim" : `${String(count)} claims`;

export function QueuePage() {
  const { data: claims, error, refresh } = usePolled(api.listClaims);
  const workQueue = useAction(api.workQueue, refresh);
  const anyWaiting = claims?.some((claim) => claim.status === "waiting");

  return (
    <main>
      <div className="page-title">
        <h1>Claims queue</h1>
        <div className="action">
          {workQueue.result ? (
            <p className="action-note" role="status">
              {claimCount(workQueue.result.started)} queued for the agent
            </p>
          ) : (
            <button
              type="button"
              disabled={workQueue.busy || !anyWaiting}
              onClick={workQueue.run}
            >
              Work the queue
            </button>
          )}
        </div>
      </div>
      <Alert message={workQueue.error ?? error} />
      {claims && (
        <section className="panel table-panel">
          <table>
            <thead>
              <tr>
                <th scope="col">Claim</th>
                <th scope="col">Customer</th>
                <th scope="col">Type</th>
                <th scope="col" className="number">
                  Claimed
                </th>
                <th scope="col">Submitted</th>
                <th scope="col">Status</th>
                <th scope="col">Decision</th>
                <th scope="col" className="number">
                  Payout
                </th>
              </tr>
            </thead>
            <tbody>
              {claims.map((claim) => (
                <tr key={claim.claim_id}>
                  <td className="id">
                    <a href={`#/claims/${claim.claim_id}`}>{claim.claim_id}</a>
                  </td>
                  <td>{claim.customer_name}</td>
                  <td>{claimTypeLabel(claim.claim_type)}</td>
                  <td className="number">{money(claim.amount_claimed)}</td>
                  <td className="id">{claim.submitted_on}</td>
                  <td>
                    <StatusChip status={claim.status} />
                  </td>
                  <td>{claim.decision && DECISION_LABELS[claim.decision]}</td>
                  <td className="number">
                    {claim.payout !== null && money(claim.payout)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      )}
    </main>
  );
}
