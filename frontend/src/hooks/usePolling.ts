import { useEffect, useRef } from "react";

export const usePolling = (
  callback: () => void,
  interval: number,
  enabled: boolean = true
) => {
  const savedCallback = useRef(callback);

  useEffect(() => {
    savedCallback.current = callback;
  }, [callback]);

  useEffect(() => {
    if (!enabled) return;

    const tick = () => savedCallback.current();
    tick(); // Call immediately
    const id = setInterval(tick, interval);
    return () => clearInterval(id);
  }, [interval, enabled]);
};
