import {
  ArrowRight,
  Check,
  Clock,
  Copy,
  Cpu,
  Download,
  ExternalLink,
  Info,
  KeyRound,
  Laptop,
  RefreshCw,
  ShieldCheck,
  TriangleAlert,
  Wifi,
} from "lucide-react";
import { StateBadge } from "../components/StateBadge";
import type { EvidenceState } from "../lib/types";

/** Design-only preview of the experiment console's connect / pairing surface.
 *  Grounds the SDD (docs/sdd/ceops-browser-runner.md): loopback-first pairing,
 *  the researched browser-reachability matrix (§3.2), and the opt-in
 *  second-machine LAN profile (§6.7). Honest by construction — every state
 *  names exactly what is and is not authorized, and the browser talks only to a
 *  Runner the user approves locally. */
export type ConnectPhase =
  | "detect"
  | "not-found"
  | "permission"
  | "pairing"
  | "paired"
  | "second-machine"
  | "safari"
  | "expired";

/** One documented fixed loopback port (illustrative in the preview; the SDD
 *  forbids port scanning and mandates a single documented port). */
const PORT = "47615";

const STATUS: Record<ConnectPhase, { state: EvidenceState; label: string }> = {
  detect: { state: "unavailable", label: "Not connected" },
  "not-found": { state: "unavailable", label: "No Runner found" },
  permission: { state: "qualified", label: "Permission needed" },
  pairing: { state: "qualified", label: "Awaiting approval" },
  paired: { state: "verified", label: "Connected" },
  "second-machine": { state: "unavailable", label: "LAN access off" },
  safari: { state: "unavailable", label: "Use local page" },
  expired: { state: "withdrawn", label: "Pairing expired" },
};

function ConsoleBar({ phase }: { phase: ConnectPhase }) {
  const { state, label } = STATUS[phase];
  return (
    <header className="console__bar">
      <span className="console__brand">
        <Cpu size={18} strokeWidth={2} aria-hidden />
        <span className="console__mark">CEOps</span>
        <span className="console__sub">Experiment console</span>
      </span>
      <code className="console__host">experiment.ceops.org</code>
      <span className="console__status" aria-live="polite">
        <StateBadge state={state} label={label} />
      </span>
    </header>
  );
}

function Steps({ active }: { active: 1 | 2 | 3 }) {
  const steps = [
    { n: 1 as const, label: "Install & start the Runner", Icon: Download },
    { n: 2 as const, label: "Connect this browser", Icon: Wifi },
    { n: 3 as const, label: "Approve pairing locally", Icon: KeyRound },
  ];
  return (
    <ol className="steps">
      {steps.map(({ n, label, Icon }) => {
        const cls = n === active ? "is-active" : n < active ? "is-done" : "";
        return (
          <li key={n} className={`step ${cls}`}>
            <span className="step__n" aria-hidden>
              {n < active ? <Check size={14} strokeWidth={2.5} /> : n}
            </span>
            <Icon size={15} strokeWidth={2} aria-hidden className="step__icon" />
            <span className="step__label">{label}</span>
            {n === active && <span className="u-vh">(current step)</span>}
          </li>
        );
      })}
    </ol>
  );
}

function TrustNote() {
  return (
    <p className="boundary connect__trust">
      <ShieldCheck size={16} strokeWidth={2} aria-hidden />
      <span>
        Experiments run on a Runner you install and control. CEOps keeps no
        account and never reaches into your network; this page talks only to a
        Runner you approve locally.
      </span>
    </p>
  );
}

function Detect() {
  return (
    <>
      <p className="eyebrow">Run on your hardware</p>
      <h1 className="connect__title">Connect your CEOps Runner</h1>
      <p className="lede">
        Benchmarks run on a Runner you install on your own computer. Pair this
        page with it once to prepare, run, and export a result — no account, no
        upload.
      </p>
      <Steps active={1} />
      <div className="actions">
        <button type="button" className="btn btn--primary">
          <Wifi size={16} strokeWidth={2} aria-hidden />
          Connect local Runner
        </button>
        <a className="btn" href="#">
          <Download size={16} strokeWidth={2} aria-hidden />
          Install the Runner
        </a>
      </div>
      <TrustNote />
    </>
  );
}

function NotFound() {
  return (
    <>
      <p className="eyebrow">Step 1 — Install &amp; start</p>
      <h1 className="connect__title">No Runner is responding on this computer</h1>
      <p className="lede">
        CEOps made one read-only check on the documented port and found nothing
        listening. It does not scan your ports or your network.
      </p>
      <div className="checklist">
        <ol>
          <li>
            Install and start the CEOps Runner, or run{" "}
            <code>ceops-runner start</code> in a terminal.
          </li>
          <li>
            Confirm it is listening on <code>http://127.0.0.1:{PORT}</code>.
          </li>
          <li>Return here and check again.</li>
        </ol>
      </div>
      <div className="actions">
        <button type="button" className="btn btn--primary">
          <RefreshCw size={16} strokeWidth={2} aria-hidden />
          Check again
        </button>
        <a className="btn" href="#">
          <Download size={16} strokeWidth={2} aria-hidden />
          Install the Runner
        </a>
      </div>
      <TrustNote />
    </>
  );
}

function Permission() {
  return (
    <>
      <p className="eyebrow">Step 2 — Browser permission</p>
      <h1 className="connect__title">Allow this page to reach your local Runner</h1>
      <p className="lede">
        Chrome shows a one-time Local Network Access prompt (Edge is expected to
        match, pending our browser spike). It lets this page talk to the Runner
        on your machine — it is not CEOps authorization, and it never grants
        access to the rest of your network.
      </p>
      <div
        className="promptcard"
        role="img"
        aria-label="Illustration of the browser's Local Network Access permission prompt, offering Allow or Block."
      >
        <p className="promptcard__t">
          <Wifi size={15} strokeWidth={2} aria-hidden />
          experiment.ceops.org wants to connect to a device on your local network
        </p>
        <p className="promptcard__b">CEOps Runner · 127.0.0.1</p>
        <div className="promptcard__row">
          <span className="btn btn--primary" aria-hidden>
            Allow
          </span>
          <span className="btn" aria-hidden>
            Block
          </span>
        </div>
      </div>
      <p className="hint">
        Firefox is expected to connect without this prompt, pending the same
        spike. Safari can’t reach a local Runner from this site — open the
        Runner’s own page instead.
      </p>
      <div className="actions">
        <button type="button" className="btn btn--primary">
          Continue
          <ArrowRight size={16} strokeWidth={2} aria-hidden />
        </button>
        <a className="btn" href="#">
          <ExternalLink size={16} strokeWidth={2} aria-hidden />
          Open local Runner page
        </a>
      </div>
      <TrustNote />
    </>
  );
}

function Pairing() {
  return (
    <>
      <p className="eyebrow">Step 3 — Approve locally</p>
      <h1 className="connect__title">Confirm the pairing in your Runner</h1>
      <p className="lede">
        Your Runner is showing the phrase below. Check it matches, then approve
        there. This page can’t approve itself.
      </p>
      <div className="pairbox">
        <dl className="pairbox__meta">
          <div>
            <dt>Requesting origin</dt>
            <dd>
              <code>https://experiment.ceops.org</code>
            </dd>
          </div>
          <div>
            <dt>Pairing ID</dt>
            <dd className="u-tnum">pr_8f3c…a21</dd>
          </div>
        </dl>
        <div className="pairbox__scopes">
          <span className="scope">runner:read</span>
          <span className="scope">experiment:prepare</span>
          <span className="scope">experiment:execute</span>
          <span className="scope">artifact:export</span>
        </div>
        <p className="pairphrase">
          <span className="u-vh">
            Confirmation phrase: amber, harbor, ninety, drift
          </span>
          <span aria-hidden="true">amber · harbor · ninety · drift</span>
        </p>
        <p className="pairbox__exp">
          <Clock size={14} strokeWidth={2} aria-hidden />
          Expires in 1:52 ·{" "}
          <a href="#">Extend by 5 minutes</a>
        </p>
      </div>
      <div className="actions">
        <button type="button" className="btn" disabled aria-disabled="true">
          Waiting for approval…
        </button>
        <button type="button" className="btn">
          Cancel
        </button>
      </div>
      <TrustNote />
    </>
  );
}

function Paired() {
  return (
    <>
      <p className="eyebrow">Connected</p>
      <h1 className="connect__title">Runner connected</h1>
      <p className="lede">
        You’re paired with your local Runner. This is exactly what it reported —
        nothing is assumed or filled in.
      </p>
      <dl className="capgrid">
        <div>
          <dt>Runner</dt>
          <dd>ceops-runner 0.1.0 · API v1</dd>
        </div>
        <div>
          <dt>Host</dt>
          <dd>
            <code>127.0.0.1:{PORT}</code>
          </dd>
        </div>
        <div>
          <dt>Machine</dt>
          <dd>macOS 15 · arm64 · 64 GB</dd>
        </div>
        <div>
          <dt>Adapters</dt>
          <dd>Ollama 0.30.8 · native ApprenticeOps</dd>
        </div>
        <div>
          <dt>Models</dt>
          <dd>3 present · digests verified</dd>
        </div>
        <div>
          <dt>Judge</dt>
          <dd>local · remote available (confirm per run)</dd>
        </div>
        <div>
          <dt>Session</dt>
          <dd>expires in 11:58 · in-memory token</dd>
        </div>
        <div>
          <dt>Scopes</dt>
          <dd>read · prepare · execute · export</dd>
        </div>
      </dl>
      <div className="actions">
        <button type="button" className="btn btn--primary">
          Prepare an experiment
          <ArrowRight size={16} strokeWidth={2} aria-hidden />
        </button>
        <button type="button" className="btn">
          Revoke pairing
        </button>
      </div>
      <p className="boundary connect__trust">
        <Info size={16} strokeWidth={2} aria-hidden />
        <span>
          Long runs continue on the Runner even if you close this page. Re-pair
          any time to observe or control them.
        </span>
      </p>
    </>
  );
}

function SecondMachine() {
  return (
    <>
      <p className="eyebrow">Optional — another computer</p>
      <h1 className="connect__title">
        Reach this Runner from another computer on your LAN
      </h1>
      <p className="lede">
        Run the Runner on one machine and open its console from a second machine
        on the same network. Plain, LAN-only, no certificates.
      </p>
      <div className="modes">
        <div className="mode">
          <p className="mode__head">
            <Laptop size={16} strokeWidth={2} aria-hidden />
            On the second computer, open
          </p>
          <code className="urlchip">http://workstation.local:{PORT}</code>
          <p className="mode__note">
            or <code>http://192.168.1.50:{PORT}</code> — the Runner serves the
            same console there.
          </p>
        </div>
      </div>
      <p className="warn">
        <TriangleAlert size={16} strokeWidth={2} aria-hidden />
        <span>
          Anyone on your network who can reach this port can try to connect. Only
          the pairing token and your firewall stand in front of it — bind one
          trusted interface and keep it off untrusted networks.
        </span>
      </p>
      <p className="hint">
        Served over plain HTTP on the LAN (no lock icon), and not reachable from
        the public site except in Chromium — open the address directly. Pairing
        is still approved on the Runner’s host: it shows the confirmation phrase
        there, or prints a one-time pairing code you enter on the second computer
        to finish.
      </p>
      <div className="actions">
        <button type="button" className="btn btn--primary">
          <Copy size={16} strokeWidth={2} aria-hidden />
          Copy address
        </button>
        <a className="btn" href="#">
          <ExternalLink size={16} strokeWidth={2} aria-hidden />
          How to enable LAN access
        </a>
      </div>
      <TrustNote />
    </>
  );
}

function Safari() {
  return (
    <>
      <p className="eyebrow">Safari</p>
      <h1 className="connect__title">Open your Runner’s local page</h1>
      <p className="lede">
        Safari doesn’t let this site connect to a Runner on your machine. Your
        Runner serves the very same console locally — open it directly and
        everything works: prepare, run, inspect, export.
      </p>
      <div className="modes">
        <div className="mode">
          <p className="mode__head">
            <ExternalLink size={16} strokeWidth={2} aria-hidden />
            Open on this machine
          </p>
          <code className="urlchip">http://127.0.0.1:{PORT}</code>
        </div>
      </div>
      <p className="hint">
        Same setup, pairing, and results — served by the Runner itself, so there
        is no cross-site restriction. Chrome, Edge, and Firefox can use this site
        directly.
      </p>
      <div className="actions">
        <a className="btn btn--primary" href="#">
          <ExternalLink size={16} strokeWidth={2} aria-hidden />
          Open local Runner
        </a>
      </div>
      <TrustNote />
    </>
  );
}

function Expired() {
  return (
    <>
      <p className="eyebrow">Session ended</p>
      <h1 className="connect__title">This pairing ended</h1>
      <p className="lede">
        The token expired, was revoked, or the Runner restarted. Your experiments
        keep running on the Runner — re-pair to observe or control them again.
        Nothing was lost.
      </p>
      <div className="actions">
        <button type="button" className="btn btn--primary">
          <KeyRound size={16} strokeWidth={2} aria-hidden />
          Pair again
        </button>
        <a className="btn" href="#">
          View what’s still running
        </a>
      </div>
      <TrustNote />
    </>
  );
}

const BODY: Record<ConnectPhase, () => JSX.Element> = {
  detect: Detect,
  "not-found": NotFound,
  permission: Permission,
  pairing: Pairing,
  paired: Paired,
  "second-machine": SecondMachine,
  safari: Safari,
  expired: Expired,
};

export function RunnerConnectPage({
  phase = "detect",
}: {
  phase?: ConnectPhase;
}) {
  const Body = BODY[phase];
  return (
    <div className="console">
      <ConsoleBar phase={phase} />
      <main className="connect">
        <div className="connect__panel">
          <Body />
        </div>
      </main>
    </div>
  );
}
