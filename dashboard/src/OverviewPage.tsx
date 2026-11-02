import { useState } from "react";
import { Alert } from "./Alert";
import { api, type QueueClaim } from "./api";
import { claimTypeLabel, money, STATUS_LABELS, STATUSES } from "./format";
import {
  countByType,
  summarize,
  withStatus,
  type StatusFilter,
  type TypeCount,
} from "./overview";
import { usePolled } from "./usePolled";

const FILTERS: { value: StatusFilter; label: string }[] = [
  { value: "all", label: "All" },
  ...STATUSES.map((status) => ({
    value: status,
    label: STATUS_LABELS[status],
  })),
];

function Stat({
  label,
  value,
  note,
}: Readonly<{ label: string; value: number; note?: string }>) {
  return (
    <div className="panel stat">
      <dt>{label}</dt>
      <dd className="stat-value">{value}</dd>
      {note && <dd className="stat-note muted">{note}</dd>}
    </div>
  );
}

function ClaimTypeBars({ rows }: Readonly<{ rows: TypeCount[] }>) {
  const largest = Math.max(...rows.map((row) => row.count));

  return (
    <table className="bars">
      <caption className="visually-hidden">Number of claims by type</caption>
      <thead className="visually-hidden">
        <tr>
          <th scope="col">Type</th>
          <th scope="col">Claims and share</th>
        </tr>
      </thead>
      <tbody>
        {rows.map((row) => (
          <tr key={row.claimType}>
            <th scope="row">{claimTypeLabel(row.claimType)}</th>
            <td>
              <div className="bar-row">
                <span
                  className="bar"
                  style={{
                    width: `calc((100% - 6rem) * ${String(row.count / largest)})`,
                  }}
                />
                <span className="number">{row.count}</span>
                <span className="number muted">
                  {Math.round(row.share * 100)}%
                </span>
              </div>
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function Overview({ claims }: Readonly<{ claims: QueueClaim[] }>) {
  const [filter, setFilter] = useState<StatusFilter>("all");
  const summary = summarize(claims);
  const rows = countByType(withStatus(claims, filter));

  return (
    <>
      <section className="panel hero">
        <div>
          <h2>Total payouts</h2>
          <p className="hero-value">
            {money(summary.paid + summary.heldForSignOff)}
          </p>
        </div>
        <dl className="facts">
          <dt>Paid</dt>
          <dd className="number">{money(summary.paid)}</dd>
          <dt>Waiting for sign-off</dt>
          <dd className="number">{money(summary.heldForSignOff)}</dd>
        </dl>
      </section>
      <dl className="stats">
        <Stat label="Claims" value={summary.total} />
        <Stat
          label="Approved"
          value={summary.approved}
          note={`${String(summary.awaitingSignOff)} waiting for sign-off`}
        />
        <Stat label="Declined" value={summary.declined} />
        <Stat label="Referred" value={summary.referred} />
        <Stat label="Not decided yet" value={summary.notDecided} />
      </dl>
      <h2>Claims by type</h2>
      <div className="filters" role="group" aria-label="Filter by status">
        {FILTERS.map(({ value, label }) => (
          <button
            key={value}
            type="button"
            aria-pressed={filter === value}
            onClick={() => {
              setFilter(value);
            }}
          >
            {label}{" "}
            <span className="id">{withStatus(claims, value).length}</span>
          </button>
        ))}
      </div>
      <section className="panel">
        {rows.length > 0 ? (
          <ClaimTypeBars rows={rows} />
        ) : (
          <p className="muted action-note">No claims have this status.</p>
        )}
      </section>
    </>
  );
}

export function OverviewPage() {
  const { data: claims, error } = usePolled(api.listClaims);

  return (
    <main>
      <div className="page-title">
        <h1>Overview</h1>
      </div>
      <Alert message={error} />
      {claims && <Overview claims={claims} />}
    </main>
  );
}
