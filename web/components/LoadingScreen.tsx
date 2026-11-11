/** The signed-in shell while a route is still choosing Home or Start. */
export function LoadingScreen({ label = "Loading" }: { label?: string }) {
  return (
    <div className="rio-loading">
      <header className="rio-nav">
        <div className="rio-nav-row">
          <span className="rio-brand">RIO</span>
        </div>
      </header>
      <main>
        <p className="rio-wait">{label}</p>
      </main>
    </div>
  );
}
