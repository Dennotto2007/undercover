import { useCallback } from "react";
import { api, type Claim, type Customer, type Policy } from "./api";
import { claimTypeLabel, DECISION_LABELS, money } from "./format";
import { StatusChip } from "./StatusChip";
import { usePolled } from "./usePolled";

function ClaimDetails({ claim }: Readonly<{ claim: Claim }>) {
  return (
    <div className="column">
      <section className="panel">
        <h2>{claim.summary}</h2>
        <p>
          {claimTypeLabel(claim.claim_type)} in {claim.incident_location}.
          Incident on <span className="id">{claim.incident_date}</span>,
          submitted on <span className="id">{claim.submitted_on}</span>.
        </p>
        <blockquote className="quote">{claim.story}</blockquote>
      </section>
      <section className="panel table-panel">
        <h2>Items claimed</h2>
        <table>
          <thead>
            <tr>
              <th scope="col">Item</th>
              <th scope="col">Category</th>
              <th scope="col" className="number">
                Amount
              </th>
            </tr>
          </thead>
          <tbody>
            {claim.items.map((item) => (
              <tr key={item.description}>
                <td className="wrap">{item.description}</td>
                <td>{claimTypeLabel(item.category)}</td>
                <td className="number">{money(item.amount)}</td>
              </tr>
            ))}
          </tbody>
          <tfoot>
            <tr>
              <th scope="row" colSpan={2}>
                Total claimed
              </th>
              <td className="number">{money(claim.amount_claimed)}</td>
            </tr>
          </tfoot>
        </table>
      </section>
      <section className="panel">
        <h2>Documents</h2>
        {claim.documents.map((document) => (
          <article className="document" key={document.name}>
            <h3>{document.name}</h3>
            <p>{document.content}</p>
          </article>
        ))}
      </section>
    </div>
  );
}

function DecisionPanel({ claim }: Readonly<{ claim: Claim }>) {
  const { decision } = claim;
  return (
    <section className="panel">
      <h2>Decision</h2>
      {decision ? (
        <>
          <p className="decision-kind">{DECISION_LABELS[decision.decision]}</p>
          <p>{decision.reason}</p>
          <dl className="facts">
            <dt>Policy section</dt>
            <dd>{decision.policy_section}</dd>
            <dt>Payout</dt>
            <dd className="number">{money(decision.payout)}</dd>
            {claim.payment && (
              <>
                <dt>Paid</dt>
                <dd className="number">{money(claim.payment.amount)}</dd>
              </>
            )}
            {claim.sign_off && (
              <>
                <dt>Signed off by</dt>
                <dd>{claim.sign_off.handler_name}</dd>
              </>
            )}
          </dl>
        </>
      ) : (
        <p className="muted">The agent has not decided this claim yet.</p>
      )}
    </section>
  );
}

function PolicyPanel({ policy }: Readonly<{ policy: Policy }>) {
  const plan = policy.plan_details;
  return (
    <section className="panel">
      <h2>Policy</h2>
      <dl className="facts">
        <dt>Policy</dt>
        <dd className="id">{policy.policy_id}</dd>
        <dt>Plan</dt>
        <dd>{plan.name}</dd>
        <dt>Add-ons</dt>
        <dd>{policy.add_on_details.map((a) => a.name).join(", ") || "None"}</dd>
        <dt>Bought on</dt>
        <dd className="id">{policy.purchased_on}</dd>
        <dt>Trip</dt>
        <dd>{policy.trip.destination}</dd>
        <dt>Dates</dt>
        <dd className="id">
          {policy.trip.departs_on} to {policy.trip.returns_on}
        </dd>
        <dt>Trip cost</dt>
        <dd className="number">{money(policy.trip.trip_cost)}</dd>
        <dt>Travelers</dt>
        <dd>{policy.travelers.join(", ")}</dd>
      </dl>
      <h3 className="document">Plan limits</h3>
      <dl className="facts">
        <dt>Trip cancellation and interruption</dt>
        <dd className="number">{money(plan.trip_cancellation_max)}</dd>
        <dt>Trip delay, after {plan.trip_delay_waiting_hours} hours</dt>
        <dd className="number">{money(plan.trip_delay_max)}</dd>
        <dt>Baggage delay, after {plan.baggage_delay_waiting_hours} hours</dt>
        <dd className="number">{money(plan.baggage_delay_max)}</dd>
        <dt>Baggage and personal effects</dt>
        <dd className="number">{money(plan.baggage_max)}</dd>
        <dt>Per item</dt>
        <dd className="number">{money(plan.per_item_limit)}</dd>
        <dt>Passport and travel documents</dt>
        <dd className="number">{money(plan.passport_max)}</dd>
        <dt>Emergency medical</dt>
        <dd className="number">{money(plan.emergency_medical_max)}</dd>
        <dt>Deductible</dt>
        <dd className="number">{money(plan.deductible)}</dd>
      </dl>
    </section>
  );
}

function HistoryPanel({ customer }: Readonly<{ customer: Customer }>) {
  return (
    <section className="panel">
      <h2>Claim history</h2>
      <p>
        {customer.name}, a customer since{" "}
        <span className="id">{customer.customer_since}</span>.
      </p>
      {customer.previous_claims.length === 0 && (
        <p className="muted">No earlier claims.</p>
      )}
      {customer.previous_claims.map((previous) => (
        <article className="document" key={previous.claim_id}>
          <h3 className="id">{previous.claim_id}</h3>
          <p>{previous.summary}</p>
          <p className="muted">
            <span className="id">{previous.incident_date}</span>,{" "}
            {previous.outcome}, {money(previous.amount_paid)} paid
          </p>
        </article>
      ))}
    </section>
  );
}

function ClaimRecords({ claim }: Readonly<{ claim: Claim }>) {
  const { policy_id: policyId, customer_id: customerId } = claim;
  const loadPolicy = useCallback(() => api.getPolicy(policyId), [policyId]);
  const loadCustomer = useCallback(
    () => api.getCustomer(customerId),
    [customerId],
  );
  const { data: policy } = usePolled(loadPolicy);
  const { data: customer } = usePolled(loadCustomer);

  return (
    <>
      {policy && <PolicyPanel policy={policy} />}
      {customer && <HistoryPanel customer={customer} />}
    </>
  );
}

export function ClaimPage({ claimId }: Readonly<{ claimId: string }>) {
  const loadClaim = useCallback(() => api.getClaim(claimId), [claimId]);
  const { data: claim, error } = usePolled(loadClaim);

  return (
    <main>
      <div className="page-title">
        <h1 className="id">{claimId}</h1>
        {claim && <span>{claim.customer_name}</span>}
        {claim && <StatusChip status={claim.status} />}
      </div>
      {error && <p role="alert">{error}</p>}
      {claim && (
        <div className="claim-layout">
          <ClaimDetails claim={claim} />
          <div className="column">
            <DecisionPanel claim={claim} />
            <ClaimRecords claim={claim} />
          </div>
        </div>
      )}
    </main>
  );
}
