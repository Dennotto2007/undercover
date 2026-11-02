import { useId, useState } from "react";
import { Alert } from "./Alert";
import { api, type Step } from "./api";
import { useAction } from "./useAction";
import { usePolled } from "./usePolled";

export function RunAgentButton({ claimId }: Readonly<{ claimId: string }>) {
  const runAgent = useAction(() => api.runAgent(claimId));
  const queued = runAgent.busy || runAgent.result !== null;

  return (
    <div className="action">
      <Alert message={runAgent.error} />
      <button type="button" disabled={queued} onClick={runAgent.run}>
        {queued ? "Queued for the agent" : "Run agent"}
      </button>
    </div>
  );
}

export function SignOffPanel({
  claimId,
  onSignedOff,
}: Readonly<{ claimId: string; onSignedOff: () => void }>) {
  const { data: handlers } = usePolled(api.listHandlers);
  const [handlerId, setHandlerId] = useState("");
  const signOff = useAction(() => api.signOff(claimId, handlerId), onSignedOff);
  const pickerId = useId();

  return (
    <div className="sign-off">
      <p className="action-note">
        The payment is blocked until a handler signs off.
      </p>
      <Alert message={signOff.error} />
      <div>
        <label htmlFor={pickerId}>Handler</label>
        <select
          id={pickerId}
          value={handlerId}
          onChange={(event) => {
            setHandlerId(event.target.value);
          }}
        >
          <option value="">Choose a handler</option>
          {handlers
            ?.filter((handler) => handler.can_approve_over_limit)
            .map((handler) => (
              <option key={handler.handler_id} value={handler.handler_id}>
                {handler.name}
              </option>
            ))}
        </select>
      </div>
      <button
        type="button"
        disabled={!handlerId || signOff.busy}
        onClick={signOff.run}
      >
        Sign off and pay
      </button>
    </div>
  );
}

export function StepsPanel({ steps }: Readonly<{ steps: Step[] }>) {
  return (
    <section className="panel" aria-live="polite">
      <h2>Agent activity</h2>
      {steps.length === 0 && (
        <p className="muted">The agent has not worked on this claim yet.</p>
      )}
      <ol className="steps">
        {steps.map((step) => (
          <li key={step.step_id}>
            <span className="id">
              {new Date(step.created_at).toLocaleTimeString("en-US")}
            </span>
            <span>{step.text}</span>
          </li>
        ))}
      </ol>
    </section>
  );
}
