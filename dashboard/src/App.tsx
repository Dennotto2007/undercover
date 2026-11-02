import { useSyncExternalStore } from "react";
import { ClaimPage } from "./ClaimPage";
import { InstructionsPage } from "./InstructionsPage";
import { OverviewPage } from "./OverviewPage";
import { QueuePage } from "./QueuePage";
import "./theme.css";

const CLAIM_ROUTE = /^#\/claims\/([\w-]+)$/;

function subscribeToHash(onChange: () => void): () => void {
  window.addEventListener("hashchange", onChange);
  return () => {
    window.removeEventListener("hashchange", onChange);
  };
}

const currentHash = (): string => window.location.hash;

function Page({ hash }: Readonly<{ hash: string }>) {
  const claimId = CLAIM_ROUTE.exec(hash)?.[1];
  if (claimId) return <ClaimPage key={claimId} claimId={claimId} />;
  if (hash === "#/queue") return <QueuePage />;
  if (hash === "#/instructions") return <InstructionsPage />;
  return <OverviewPage />;
}

export function App() {
  const hash = useSyncExternalStore(subscribeToHash, currentHash);

  return (
    <div className="shell">
      <header className="masthead">
        <a className="brand" href="#/">
          UnderCover
        </a>
        <span className="tagline">Claims dashboard</span>
        <nav aria-label="Main">
          <a href="#/">Overview</a>
          <a href="#/queue">Queue</a>
          <a href="#/instructions">Instructions</a>
        </nav>
      </header>
      <Page hash={hash} />
    </div>
  );
}
