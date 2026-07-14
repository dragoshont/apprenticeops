import type { Meta, StoryObj } from "@storybook/react";
import { RunnerConnectPage } from "../pages/RunnerConnectPage";

/** Experiment console — connect & pairing flow (design-only preview for
 *  sign-off). Each story is one state from the browser-runner SDD: loopback
 *  pairing, the researched browser-reachability matrix (§3.2), and the opt-in
 *  second-machine LAN profile (§6.7). Toggle Theme in the toolbar; both
 *  neutral-light and charcoal-dark are first-class. */
const meta = {
  title: "CEOps/Experiment/Runner connect",
  component: RunnerConnectPage,
  parameters: { layout: "fullscreen" },
} satisfies Meta<typeof RunnerConnectPage>;

export default meta;
type Story = StoryObj<typeof meta>;

/** First contact: install-and-pair path, no probing until the user asks. */
export const Detect: Story = { args: { phase: "detect" } };

/** A single read-only health check found nothing; honest, no port scanning. */
export const RunnerNotFound: Story = { args: { phase: "not-found" } };

/** Chromium's one-time Local Network Access prompt — permission, not authorization. */
export const LocalNetworkPermission: Story = { args: { phase: "permission" } };

/** Local confirmation ceremony: origin, scopes, phrase, expiry — approved on the Runner. */
export const PairingPending: Story = { args: { phase: "pairing" } };

/** Connected: the Runner's reported capabilities, nothing assumed. */
export const Paired: Story = { args: { phase: "paired" } };

/** Opt-in LAN profile: reach the Runner from a second computer, with the exposure warning. */
export const SecondMachineAccess: Story = { args: { phase: "second-machine" } };

/** Safari has no loopback exception: use the Runner-served local page directly. */
export const SafariFallback: Story = { args: { phase: "safari" } };

/** Token expired / revoked / Runner restarted — runs continue; re-pair to resume control. */
export const PairingExpired: Story = { args: { phase: "expired" } };
