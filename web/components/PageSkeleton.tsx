import { Nav } from "./Nav";
import { WakeHint } from "./LoadingScreen";

export function SkeletonBlocks({ variant = "cards" }: { variant?: "home" | "cards" | "calendar" }) {
  if (variant === "calendar") {
    return (
      <div className="rio-skel-stack" aria-hidden="true">
        <div className="rio-skel rio-skel-hero" />
        <div className="rio-skel" style={{ height: 40 }} />
        <div className="rio-skel-split">
          <div className="rio-skel rio-skel-card" />
          <div className="rio-skel-cal">
            {Array.from({ length: 35 }, (_, index) => (
              <div key={index} className="rio-skel" />
            ))}
          </div>
        </div>
      </div>
    );
  }
  if (variant === "home") {
    return (
      <div className="rio-skel-stack rio-skel-home" aria-hidden="true">
        <div className="rio-skel rio-skel-hero" />
        <div className="rio-skel-tiles">
          <div className="rio-skel" />
          <div className="rio-skel" />
          <div className="rio-skel" />
          <div className="rio-skel" />
        </div>
        <div className="rio-skel-split">
          <div className="rio-skel rio-skel-card" />
          <div className="rio-skel rio-skel-card" />
        </div>
        <div className="rio-skel-three">
          <div className="rio-skel" />
          <div className="rio-skel" />
          <div className="rio-skel" />
        </div>
      </div>
    );
  }
  return (
    <div className="rio-skel-stack" aria-hidden="true">
      <div className="rio-skel rio-skel-line" />
      <div className="rio-skel rio-skel-card" />
      <div className="rio-skel rio-skel-card" />
    </div>
  );
}

/** First paint for a signed-in route: the page's frame, not a bare "Loading" line. */
export function PageSkeleton({
  title,
  variant = "cards",
  pageClass,
  pending = false,
}: {
  title?: string;
  variant?: "home" | "cards" | "calendar";
  pageClass?: string;
  pending?: boolean;
}) {
  const klass = pageClass || (variant === "home" ? "page-home" : "page-plain");
  return (
    <div className={`${klass} page-skeleton`} aria-busy="true">
      <Nav pending={pending} />
      <main>
        {title ? (
          <header className="rio-hero">
            <h1>{title}</h1>
          </header>
        ) : null}
        <SkeletonBlocks variant={variant} />
        <WakeHint />
      </main>
    </div>
  );
}
