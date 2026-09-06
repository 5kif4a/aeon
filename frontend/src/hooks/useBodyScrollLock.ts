import { useEffect } from "react";

/**
 * Freeze the page behind an overlay. iOS ignores `overflow: hidden` on the body for
 * touch scrolling, so the body is pinned with `position: fixed` at its current offset
 * and the offset is restored on unmount; this also stops the page from jumping when
 * the on-screen keyboard opens for a field inside the overlay.
 */
export function useBodyScrollLock(active = true) {
  useEffect(() => {
    if (!active) return;
    const { body } = document;
    const scrollY = window.scrollY;
    const previous = {
      position: body.style.position,
      top: body.style.top,
      left: body.style.left,
      right: body.style.right,
      width: body.style.width,
      overflow: body.style.overflow,
    };
    body.style.position = "fixed";
    body.style.top = `-${scrollY}px`;
    body.style.left = "0";
    body.style.right = "0";
    body.style.width = "100%";
    body.style.overflow = "hidden";
    return () => {
      Object.assign(body.style, previous);
      window.scrollTo({ top: scrollY, left: 0, behavior: "instant" });
    };
  }, [active]);
}
