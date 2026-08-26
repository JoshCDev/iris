export function SiteFooter() {
  return (
    <footer className="site-footer">
      <div className="page-shell site-footer__inner">
        <div className="site-footer__main">
          <strong>IRIS</strong>
          <p>
            Demonstration build of rain-aware AWD, leaf-photo triage, and a
            tool-grounded assistant. Leaf output is screening, not a diagnosis.
            Season water and CH4 figures are labelled [simulated].
          </p>
          <small>© 2026 IRIS team · Universitas Kristen Maranatha</small>
        </div>
        <div className="site-footer__contact">
          <span className="qr-slot" aria-hidden="true">
            QR
          </span>
          <span>
            Team contact &amp; docs
            <small>Scan the code at the demo booth.</small>
          </span>
        </div>
      </div>
    </footer>
  );
}
