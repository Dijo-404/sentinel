/** CSS product-stage mock for landing hero (simulator preview). */
export function HeroStage() {
  return (
    <div className="hero-stage" aria-hidden="true">
      <div className="hero-stage__panel hero-stage__panel--back">
        <div className="hero-stage__bar" />
        <div className="hero-stage__bars">
          <span style={{ height: "42%" }} />
          <span style={{ height: "68%" }} />
          <span style={{ height: "55%" }} />
          <span style={{ height: "80%" }} />
          <span style={{ height: "48%" }} />
        </div>
      </div>
      <div className="hero-stage__panel hero-stage__panel--front">
        <p className="hero-stage__eyebrow">Simulator preview</p>
        <div className="hero-stage__kpis">
          <div>
            <span>Queue</span>
            <strong>24</strong>
          </div>
          <div>
            <span>Waiting</span>
            <strong>6</strong>
          </div>
          <div>
            <span>Verified</span>
            <strong>18</strong>
          </div>
        </div>
        <ul className="hero-stage__rows">
          <li>
            <span className="hero-stage__dot" data-tone="pending" />
            Investigate exception
          </li>
          <li>
            <span className="hero-stage__dot" data-tone="approve" />
            Approve proposal
          </li>
          <li>
            <span className="hero-stage__dot" data-tone="dispatch" />
            Dispatch refund
          </li>
          <li>
            <span className="hero-stage__dot" data-tone="verify" />
            Verify credit
          </li>
        </ul>
      </div>
    </div>
  );
}
