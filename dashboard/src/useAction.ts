import { useState } from "react";
import { errorMessage } from "./format";

interface ActionState<T> {
  busy: boolean;
  result: T | null;
  error: string | null;
}

export function useAction<T>(
  action: () => Promise<T>,
  onDone?: () => void,
): ActionState<T> & { run: () => void } {
  const [state, setState] = useState<ActionState<T>>({
    busy: false,
    result: null,
    error: null,
  });

  const run = (): void => {
    setState({ busy: true, result: null, error: null });
    action().then(
      (result) => {
        setState({ busy: false, result, error: null });
        onDone?.();
      },
      (error: unknown) => {
        setState({ busy: false, result: null, error: errorMessage(error) });
      },
    );
  };

  return { ...state, run };
}
