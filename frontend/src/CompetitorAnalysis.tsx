import { ArrowUpRight } from "lucide-react";
import {
  availabilityLabels,
  comparisons,
  evidenceLabels,
  mixpanelSources,
  mixpanelStrengths,
  mixpanelVerifiedDate,
  productGaps,
  pulseosDifferentiators,
  type Availability,
} from "./competitorAnalysisData";
import "./CompetitorAnalysis.css";

const verifiedDateLabel = new Intl.DateTimeFormat("en-GB", {
  day: "numeric",
  month: "long",
  year: "numeric",
  timeZone: "UTC",
}).format(new Date(mixpanelVerifiedDate));

function SourceLink({ label, url }: { label: string; url: string }) {
  return (
    <a className="competitor-source-link" href={url} target="_blank" rel="noreferrer">
      {label} <ArrowUpRight size={13} aria-hidden="true" />
    </a>
  );
}

function AvailabilityBadge({ status }: { status: Availability }) {
  return <span className={`competitor-badge competitor-status-${status}`}>{availabilityLabels[status]}</span>;
}

export default function CompetitorAnalysis() {
  return (
    <div className="competitor-page">
      <section className="panel competitor-overview" aria-labelledby="competitor-overview">
        <h2 id="competitor-overview">Overview</h2>
        <div className="competitor-pair">
          <div className="competitor-position">
            <h3>Mixpanel</h3>
            <p className="competitor-category">Product Analytics</p>
            <p>Mixpanel helps product teams measure how users behave after instrumentation. Its reporting centres on events, users and properties.</p>
            <div className="competitor-links">
              <SourceLink label="mixpanel.com" url="https://mixpanel.com/" />
              <SourceLink {...mixpanelSources.product} />
            </div>
          </div>
          <div className="competitor-position">
            <h3>PulseOS</h3>
            <p className="competitor-category">Product Intelligence</p>
            <p>PulseOS helps product teams investigate evidence from uploaded events, customer reviews and documents in a single workspace.</p>
          </div>
        </div>
      </section>

      <section className="panel competitor-matrix" aria-labelledby="competitor-matrix">
        <h2 id="competitor-matrix">Feature Comparison Matrix</h2>
        <p>Mixpanel sources last verified on <time dateTime={mixpanelVerifiedDate}>{verifiedDateLabel}</time>.</p>
        <table className="competitor-table" role="table" aria-labelledby="competitor-matrix">
          <thead role="rowgroup">
            <tr role="row">
              <th scope="col" role="columnheader">Capability</th>
              <th scope="col" role="columnheader">Mixpanel</th>
              <th scope="col" role="columnheader">PulseOS</th>
              <th scope="col" role="columnheader">Comparison</th>
            </tr>
          </thead>
          <tbody role="rowgroup">
            {comparisons.map(({ capability, mixpanel, pulseos, comparison }) => (
              <tr key={capability} role="row">
                <th scope="row" role="rowheader">{capability}</th>
                <td role="cell">
                  <span className="competitor-mobile-label" aria-hidden="true">Mixpanel</span>
                  <AvailabilityBadge status={mixpanel.status} />
                  <p>{mixpanel.detail}</p>
                  <small className="competitor-evidence">{evidenceLabels[mixpanel.evidence]}</small>
                  <SourceLink {...mixpanelSources[mixpanel.source]} />
                </td>
                <td role="cell">
                  <span className="competitor-mobile-label" aria-hidden="true">PulseOS</span>
                  <AvailabilityBadge status={pulseos.status} />
                  <p>{pulseos.detail}</p>
                </td>
                <td role="cell" className="competitor-row-comparison">
                  <span className="competitor-mobile-label" aria-hidden="true">Comparison</span>
                  <p>{comparison}</p>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        <details className="competitor-methodology">
          <summary>How capabilities were assessed</summary>
          <p>PulseOS entries are based on accessible workspace modules and their implementation. Mixpanel entries use the linked official documentation and product pages.</p>
          <dl>
            <div><dt>Available</dt><dd>The product supports the core workflow described in the row.</dd></div>
            <div><dt>Partially Available</dt><dd>The product covers part of the workflow or uses a partner integration.</dd></div>
            <div><dt>Not Available</dt><dd>The assessed product implementation lacks the capability described in the row.</dd></div>
            <div><dt>Needs Verification</dt><dd>The sources establish a related workflow. The native capability still needs confirmation.</dd></div>
          </dl>
          <p>Verified entries are stated directly in the source. Inferred entries draw a comparison from a documented integration. Unconfirmed entries link to the nearest relevant evidence.</p>
        </details>
      </section>

      <div className="competitor-pair competitor-findings">
        <section className="panel" aria-labelledby="competitor-strengths">
          <h2 id="competitor-strengths">Mixpanel Strengths</h2>
          <ul className="competitor-findings-list">
            {mixpanelStrengths.map(({ title, detail, sources }) => (
              <li key={title}>
                <h3>{title}</h3>
                <p>{detail}</p>
                <div className="competitor-links">
                  {sources.map((source) => <SourceLink key={source.url} {...source} />)}
                </div>
              </li>
            ))}
          </ul>
        </section>
        <section className="panel" aria-labelledby="competitor-differentiators">
          <h2 id="competitor-differentiators">PulseOS Differentiators</h2>
          <ul className="competitor-findings-list">
            {pulseosDifferentiators.map(({ title, detail }) => (
              <li key={title}>
                <h3>{title}</h3>
                <p>{detail}</p>
              </li>
            ))}
          </ul>
        </section>
      </div>

      <section aria-labelledby="competitor-gaps">
        <h2 id="competitor-gaps">Product Gaps</h2>
        <p>These recommendations are ordered by priority for product teams using PulseOS.</p>
        <div className="competitor-pair competitor-gap-grid">
          {productGaps.map(({ title, priority, reason, impact, improvement }) => (
            <article className="panel competitor-gap" key={title}>
              <div className="competitor-gap-heading">
                <h3>{title}</h3>
                <span className={`competitor-badge competitor-priority-${priority.toLowerCase()}`}>{priority} priority</span>
              </div>
              <dl>
                <div><dt>Why it matters</dt><dd>{reason}</dd></div>
                <div><dt>User impact</dt><dd>{impact}</dd></div>
                <div><dt>Suggested improvement</dt><dd>{improvement}</dd></div>
              </dl>
            </article>
          ))}
        </div>
      </section>

      <section className="panel competitor-conclusion" aria-labelledby="competitor-conclusion">
        <h2 id="competitor-conclusion">Final Competitive Positioning</h2>
        <p>Mixpanel is strongest for teams with instrumented products that need flexible behavioural reports, conversion and retention analysis, and shared projects.</p>
        <p>PulseOS suits product teams that already have event exports, customer reviews and product documents and want to investigate those signals together. The highest-priority opportunities are ongoing event collection and shared workspaces with role-based access.</p>
      </section>
    </div>
  );
}
