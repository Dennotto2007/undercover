import { api } from "./api";
import { usePolled } from "./usePolled";

export function InstructionsPage() {
  const { data, error } = usePolled(api.getInstructions);

  return (
    <main>
      <div className="page-title">
        <h1>Agent instructions</h1>
        <span className="muted">Read only</span>
      </div>
      {error && <p role="alert">{error}</p>}
      {data && (
        <section className="panel">
          <p className="instructions">{data.text}</p>
        </section>
      )}
    </main>
  );
}
