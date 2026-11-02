import { api } from "./api";
import { claimTypeLabel, DECISION_LABELS, money } from "./format";
import { StatusChip } from "./StatusChip";
import { usePolled } from "./usePolled";

export function QueuePage() {
  const { data: claims, error } = usePolled(api.listClaims);

  return (
    <main>
      <div className="page-title">
        <h1>Claims queue</h1>
      </div>
      {error && <p role="alert">{error}</p>}
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
