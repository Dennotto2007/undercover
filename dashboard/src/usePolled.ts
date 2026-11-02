import { useEffect, useState } from "react";

const POLL_MS = 2000;

export interface Polled<T> {
  data: T | null;
  error: string | null;
}

export function usePolled<T>(load: () => Promise<T>): Polled<T> {
  const [polled, setPolled] = useState<Polled<T>>({ data: null, error: null });

  useEffect(() => {
    let active = true;
    const refresh = (): void => {
      load().then(
        (data) => {
          if (active) setPolled({ data, error: null });
        },
        (error: unknown) => {
          if (active) {
            setPolled((current) => ({
              data: current.data,
              error: error instanceof Error ? error.message : String(error),
            }));
          }
        },
      );
    };
    refresh();
    const timer = setInterval(refresh, POLL_MS);
    return () => {
      active = false;
      clearInterval(timer);
    };
  }, [load]);

  return polled;
}
