import { useEffect, useRef, useState } from "react";

/**
 * A short-lived status line: `show()` makes it visible for `duration` ms.
 * The timer is cleared on re-show and on unmount.
 */
export function useInlineStatus(duration = 2000): { visible: boolean; show: () => void } {
  const [visible, setVisible] = useState(false);
  const timer = useRef<number | null>(null);

  useEffect(() => {
    return () => {
      if (timer.current !== null) window.clearTimeout(timer.current);
    };
  }, []);

  const show = () => {
    if (timer.current !== null) window.clearTimeout(timer.current);
    setVisible(true);
    timer.current = window.setTimeout(() => setVisible(false), duration);
  };

  return { visible, show };
}
