import { useEffect, useState } from "react";
import { errorMessage } from "./format";

const POLL_MS = 2000;

export interface Polled<T> {
  data: T | null;
  error: string | null;
}

export function usePolled<T>(
  load: () => Promise<T>,
): Polled<T> & { refresh: () => void } {
  const [polled, setPolled] = useState<Polled<T>>({ data: null, error: null });
  const [refreshes, setRefreshes] = useState(0);

  useEffect(() => {
    let active = true;
    const fetchNow = (): void => {
      load().then(
        (data) => {
          if (active) setPolled({ data, error: null });
        },
        (error: unknown) => {
          if (active) {
            setPolled((current) => ({
              data: current.data,
              error: errorMessage(error),
            }));
          }
        },
      );
    };
    fetchNow();
    const timer = setInterval(fetchNow, POLL_MS);
    return () => {
      active = false;
      clearInterval(timer);
    };
  }, [load, refreshes]);

  return {
    ...polled,
    refresh: () => {
      setRefreshes((count) => count + 1);
    },
  };
}
