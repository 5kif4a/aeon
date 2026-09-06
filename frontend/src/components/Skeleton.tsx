/** Loading placeholder bar. Size it with width/height utility classes. */
export function Skeleton({ className = "" }: { className?: string }) {
  return (
    <span
      aria-hidden="true"
      className={`bg-surface-strong block animate-pulse rounded-[6px] motion-reduce:animate-none ${className}`}
    />
  );
}
