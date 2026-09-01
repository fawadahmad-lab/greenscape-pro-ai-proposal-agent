interface SkeletonCardProps {
  count?: number;
}

export function SkeletonCard({ count = 3 }: SkeletonCardProps) {
  return (
    <div aria-hidden="true">
      {Array.from({ length: count }).map((_, i) => (
        <div className="skeleton-card" key={i}>
          <div className="skeleton skeleton-line w70" />
          <div className="skeleton skeleton-line w40" />
        </div>
      ))}
    </div>
  );
}
