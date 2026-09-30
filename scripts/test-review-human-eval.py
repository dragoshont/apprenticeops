#!/usr/bin/env python3
"""Synthetic-only tests for local review. Never opens or labels the real pilot."""
from __future__ import annotations

import copy
import csv
import gzip
import http.client
import io
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import human_review as review


def raw_row(model="private-model", scenario="fixture", rep=0):
    context = "A fictional stationery cupboard has three pencils.\n" + "Complete context. " * 140
    question = "How should we store the pencils?"
    system = "You are a fictional stationery helper."
    prompt = f"--- CONTEXT ---\n{context}\n\n--- TASK ---\n{question}"
    answer = ("Keep the pencils in the drawer. " * 150 +
              "\n<script>NOT EXECUTABLE</script>\nRAW ANSWER END\n")
    row = {
        "model": model, "scenario": scenario, "rep": rep,
        "ollama.parameter_count": 1_000_000_000,
        "distill.input_messages": [{"role": "system", "content": system},
                                  {"role": "user", "content": prompt}],
        "distill.output_message": {"role": "assistant", "content": answer},
        "prompt.full": system + "\n\n" + prompt,
        "distill.input_sha256": review.text_sha(system + "\n\n" + prompt),
        "prompt.user_content_sha256": review.text_sha(prompt),
        "distill.output_sha256": review.text_sha(answer),
        "scenario.context_sha256": review.text_sha(context),
        "scenario.question_sha256": review.text_sha(question),
        "distill.reference_answer": "SEALED GOLD DO NOT EXPOSE",
        "score": 4.98,
    }
    scenario = {"id": scenario, "context": context, "question": question, "class": "guard",
                "gold_answer": "SEALED GOLD DO NOT EXPOSE", "judge_rubric": "HIDDEN RUBRIC"}
    return row, scenario


class PacketTests(unittest.TestCase):
    def test_full_text_and_redaction(self):
        row, scenario = raw_row()
        item = review.make_item(row, scenario)
        self.assertGreater(len(item["answer"]), 2500)
        self.assertGreater(len(item["prompt"]), 1800)
        self.assertEqual(item["answer"], row["distill.output_message"]["content"])
        self.assertEqual(item["prompt"], row["distill.input_messages"][1]["content"])
        self.assertTrue(item["answer"].endswith("RAW ANSWER END\n"))
        serialized = json.dumps(item)
        for hidden in ("private-model", "SEALED GOLD", "HIDDEN RUBRIC", "4.98"):
            self.assertNotIn(hidden, serialized)
        self.assertTrue(item["safety_applicable"])
        scenario["class"] = "test"
        self.assertFalse(review.make_item(row, scenario)["safety_applicable"])

    def test_missing_or_modified_original_refuses(self):
        row, scenario = raw_row()
        for field in ("distill.output_message", "distill.input_messages", "prompt.full"):
            broken = dict(row)
            del broken[field]
            with self.subTest(field=field), self.assertRaises(review.ReviewError):
                review.make_item(broken, scenario)
        broken = copy.deepcopy(row)
        broken["distill.output_message"]["content"] += "changed"
        with self.assertRaisesRegex(review.ReviewError, "hash mismatch"):
            review.make_item(broken, scenario)

    def test_empty_original_answer_is_not_missing(self):
        row, scenario = raw_row()
        row["distill.output_message"]["content"] = ""
        row["distill.output_sha256"] = review.text_sha("")
        self.assertEqual(review.make_item(row, scenario)["answer"], "")

    def test_thought_tags_and_answer_self_identification_are_literal(self):
        row, scenario = raw_row()
        answer = "<think>Full literal thought text.</think>\nI am private-model.\n"
        row["distill.output_message"]["content"] = answer
        row["distill.output_sha256"] = review.text_sha(answer)
        item = review.make_item(row, scenario)
        self.assertEqual(item["answer"], answer)
        self.assertNotIn("model", item)

    def test_fixture_refuses_pilot_path(self):
        with self.assertRaises(review.ReviewError):
            review.prepare_fixture(review.DEFAULT_PACKET)


class StoreTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name) / "fixture"
        review.prepare_fixture(self.directory)
        self.store = review.Store(self.directory)
        self.addCleanup(self.store.close)
        self.state = self.store.setup("operator-fixture", "no")
        self.sid = self.state["session_id"]
        self.ids = list(self.store.items)

    def save(self, index=0, *, revision=None, status="reviewed", answers=None, note="", cursor=1):
        if answers is None:
            answers = {"responsive": "yes", "usable": "unsure", "endorses_destructive": None}
        return self.store.save(self.sid, {
            "revision": self.state["revision"] if revision is None else revision,
            "cursor": cursor,
            "update": {"item_id": self.ids[index],
                       "response": {"status": status, "responses": answers, "note": note}},
        })

    def test_untouched_unsure_and_not_applicable_are_distinct(self):
        self.assertTrue(all(v is None for v in self.state["responses"][self.ids[0]]["responses"].values()))
        self.state = self.save()
        self.assertEqual(self.state["responses"][self.ids[0]]["responses"]["usable"], "unsure")
        report = self.store.export(self.sid)
        self.assertFalse(report["items"][0]["safety_applicable"])
        self.assertIsNone(report["items"][0]["responses"]["endorses_destructive"])
        self.assertEqual(report["items"][1]["status"], "pending")

    def test_applicability_and_complete_response_validation(self):
        with self.assertRaisesRegex(review.ReviewError, "not applicable"):
            self.save(answers={"responsive": "yes", "usable": "yes", "endorses_destructive": "no"})
        with self.assertRaisesRegex(review.ReviewError, "Answer each"):
            self.save(index=1)
        state = self.save(index=1, answers={"responsive": "yes", "usable": "no",
                                         "endorses_destructive": "unsure"})
        self.assertEqual(state["responses"][self.ids[1]]["responses"]["endorses_destructive"], "unsure")

    def test_skip_retains_partial_response_and_note_then_return(self):
        partial = {"responsive": "no", "usable": None, "endorses_destructive": None}
        self.state = self.save(status="skipped", answers=partial, note="Look again later")
        self.assertEqual(self.store.read_state(self.sid)["responses"][self.ids[0]]["status"], "skipped")
        self.state = self.save(cursor=0, note="Now reviewed")
        self.assertEqual(self.state["cursor"], 0)
        self.assertEqual(self.state["responses"][self.ids[0]]["status"], "reviewed")

    def test_resume_restart_and_immutable_provenance(self):
        self.state = self.save(note="Human fixture note")
        self.store.close()
        self.store = review.Store(self.directory)
        self.addCleanup(self.store.close)
        resumed = self.store.setup("OPERATOR-FIXTURE", "yes")
        self.assertEqual(resumed, self.state)
        self.assertFalse(resumed["reviewer"]["independent"])
        self.assertEqual(resumed["reviewer"]["role"], review.SCOPE)
        self.assertEqual(resumed["reviewer"]["seen_prior_scores"], "no")

    def test_reviewers_are_separate(self):
        other = self.store.setup("another reviewer", "yes")
        self.assertNotEqual(other["session_id"], self.sid)
        self.state = self.save()
        self.assertEqual(self.store.read_state(other["session_id"])["revision"], 0)

    def test_stale_revision_does_not_overwrite(self):
        self.state = self.save(note="First tab")
        with self.assertRaisesRegex(review.ReviewError, "Another tab") as caught:
            self.save(revision=0, note="Stale tab")
        self.assertEqual(caught.exception.status, 409)
        self.assertEqual(self.store.read_state(self.sid)["responses"][self.ids[0]]["note"], "First tab")

    def test_simultaneous_saves_have_one_winner(self):
        results = []
        def worker():
            try:
                self.save(revision=0)
                results.append("saved")
            except review.ReviewError as exc:
                results.append(exc.status)
        threads = [threading.Thread(target=worker) for _ in range(2)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        self.assertCountEqual(results, ["saved", 409])

    def test_second_server_process_lock_refuses(self):
        with self.assertRaisesRegex(review.ReviewError, "already open"):
            review.Store(self.directory)

    def test_atomic_replace_failure_preserves_prior_bytes(self):
        path = self.store.session_path(self.sid)
        before = path.read_bytes()
        with patch.object(review.os, "replace", side_effect=OSError("synthetic disk failure")):
            with self.assertRaisesRegex(review.ReviewError, "could not be confirmed"):
                self.save(note="Do not lose me")
        self.assertEqual(path.read_bytes(), before)
        self.assertFalse(list(path.parent.glob(".saving-*")))
        self.assertEqual(self.store.read_state(self.sid)["revision"], 0)

    def test_fsync_failure_is_not_reported_saved(self):
        before = self.store.session_path(self.sid).read_bytes()
        with patch.object(review.os, "fsync", side_effect=OSError("synthetic fsync failure")):
            with self.assertRaises(review.ReviewError):
                self.save()
        self.assertEqual(self.store.session_path(self.sid).read_bytes(), before)

    def test_corruption_and_missing_progress_never_reset(self):
        path = self.store.session_path(self.sid)
        path.write_text("{truncated", encoding="utf-8")
        with self.assertRaises(review.ReviewError):
            self.store.setup("operator-fixture", "no")
        self.assertEqual(path.read_text(), "{truncated")
        path.unlink()
        with self.assertRaises(review.ReviewError):
            self.store.setup("operator-fixture", "no")
        self.assertFalse(path.exists())

    def test_packet_hash_mismatch_refuses_saved_state(self):
        state = copy.deepcopy(self.state)
        state["packet_sha256"] = "0" * 64
        review.atomic_json(self.store.session_path(self.sid), review.envelope(state))
        with self.assertRaisesRegex(review.ReviewError, "different packet"):
            self.store.read_state(self.sid)

    def test_packet_and_sidecar_tampering_refuse(self):
        path = self.directory / "packet.json"
        original = path.read_bytes()
        path.write_bytes(original + b" ")
        with self.assertRaisesRegex(review.ReviewError, "integrity"):
            self.store.read_state(self.sid)
        path.write_bytes(original)
        (self.directory / "private.json").write_text("{}")
        with self.assertRaisesRegex(review.ReviewError, "integrity"):
            self.store.read_state(self.sid)

    def test_unknown_item_and_additional_fields_refuse(self):
        with self.assertRaises(review.ReviewError):
            self.store.save(self.sid, {"revision": 0, "cursor": 1,
                                      "update": {"item_id": "../private.json",
                                                 "response": self.store.blank_response()}})
        with self.assertRaises(review.ReviewError):
            self.store.save(self.sid, {"revision": 0, "cursor": 1, "update": None, "independent": True})

    def test_response_types_and_note_bounds(self):
        for invalid in (False, 1, "not-applicable", "maybe", {"value": "yes"}):
            with self.subTest(invalid=invalid), self.assertRaises(review.ReviewError):
                self.save(answers={"responsive": invalid, "usable": "yes", "endorses_destructive": None})
        with self.assertRaises(review.ReviewError):
            self.save(note="x" * (review.NOTE_LIMIT + 1))
        self.assertEqual(self.store.read_state(self.sid)["revision"], 0)

    def test_failed_initial_setup_can_be_retried_without_fake_saved_state(self):
        with patch.object(review.os, "replace", side_effect=OSError("synthetic initial failure")):
            with self.assertRaises(review.ReviewError):
                self.store.setup("new alias", "yes")
        state = self.store.setup("new alias", "yes")
        self.assertEqual(state["revision"], 0)
        self.assertTrue(all(r["status"] == "pending" for r in state["responses"].values()))

    def test_export_provenance_response_hashes_and_formula_safety(self):
        self.state = self.save(note=" \n=1+1")
        report = self.store.export(self.sid)
        self.assertEqual(report["packet_sha256"], self.store.packet_hash)
        self.assertEqual(report["protocol_id"], review.PROTOCOL["id"])
        self.assertEqual(report["items"][0]["response_sha256"],
                         review.text_sha(self.store.items[self.ids[0]]["answer"]))
        self.assertEqual(report["items"][0]["responses"]["usable"], "unsure")
        self.assertEqual(report["counts"], {"reviewed": 1, "skipped": 0, "pending": 2, "with_unsure": 1})
        self.assertEqual(report["saved_at"], self.state["saved_at"])
        self.assertNotIn("storage_location", report)
        rows = list(csv.DictReader(io.StringIO(review.export_csv(report).decode())))
        self.assertTrue(rows[0]["note"].startswith("'"))
        self.assertEqual(rows[0]["reviewer_id"], self.state["reviewer"]["id"])
        self.assertEqual(rows[0]["safety_applicable"], "False")
        self.assertEqual(rows[0]["endorses_destructive"], "")
        self.assertEqual(rows[1]["status"], "pending")
        self.assertEqual(rows[0]["items_pending"], "2")
        for bad in ("=x", "+x", "-x", "@x", "\ttext", "\rtext", "\ntext", "  =x"):
            self.assertTrue(review.csv_safe(bad).startswith("'"))
        for hidden in ("source_key", "private.json", "model", "gold", "machine_score"):
            self.assertNotIn(hidden, json.dumps(report))


class HTTPTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        path = Path(self.temp.name) / "http-fixture"
        review.prepare_fixture(path)
        self.store = review.Store(path)
        self.addCleanup(self.store.close)
        self.server = review.ReviewServer(self.store, 0)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.addCleanup(self.stop)
        self.origin = self.server.origin
        self.token = self.server.token
        self.state = self.store.setup("HTTP fixture", "unsure")

    def stop(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()

    def request(self, path, method="GET", body=None, headers=None):
        connection = http.client.HTTPConnection("127.0.0.1", self.server.server_port, timeout=3)
        h = {"Origin": self.origin, "X-Review-Token": self.token,
             "X-Review-Session": self.state["session_id"]}
        if body is not None:
            h["Content-Type"] = "application/json"
            if not isinstance(body, bytes):
                body = json.dumps(body).encode()
        for k, value in (headers or {}).items():
            if value is None:
                h.pop(k, None)
            else:
                h[k] = value
        connection.request(method, path, body=body, headers=h)
        response = connection.getresponse()
        result = response.status, dict(response.getheaders()), response.read()
        connection.close()
        return result

    def test_bootstrap_and_full_item_allowlist(self):
        status, headers, body = self.request("/api/bootstrap")
        self.assertEqual(status, 200)
        self.assertIn("frame-ancestors 'none'", headers["Content-Security-Policy"])
        self.assertEqual(headers["Cache-Control"], "no-store")
        self.assertEqual(json.loads(body)["scope"], "synthetic-test-fixture")
        self.assertEqual(json.loads(body)["storage_location"], str(self.store.directory.resolve() / "sessions"))
        item = next(iter(self.store.items.values()))
        status, _, body = self.request("/api/item/" + item["id"])
        data = json.loads(body)
        self.assertEqual(status, 200)
        self.assertEqual(set(data), {"id", "system", "prompt", "answer", "safety_applicable"})
        self.assertEqual(data["answer"], item["answer"])

    def test_no_generic_file_serving_or_query_paths(self):
        for path in ("/private.json", "/packet.json", "/../human_review.py", "/.git/config",
                     "/review.js?other", "/api/state?private", "/api/item/../../private.json"):
            with self.subTest(path=path):
                self.assertEqual(self.request(path)[0], 404)

    def test_cross_origin_host_and_token_guards(self):
        for headers in ({"Origin": "https://example.invalid"},
                        {"Origin": "null"}, {"Host": "example.invalid"},
                        {"Sec-Fetch-Site": "cross-site"}):
            self.assertEqual(self.request("/api/bootstrap", headers=headers)[0], 403)
        for headers in ({"X-Review-Token": None}, {"Origin": None},
                        {"Origin": "https://example.invalid"}):
            self.assertEqual(self.request("/api/setup", "POST",
                                         {"alias": "other", "exposure": "no"}, headers)[0], 403)

    def test_portal_link_allows_only_top_level_entry_navigation(self):
        headers = {"Origin": None, "Sec-Fetch-Site": "cross-site",
                   "Sec-Fetch-Mode": "navigate", "Sec-Fetch-Dest": "document"}
        self.assertEqual(self.request("/", headers=headers)[0], 200)
        for path in ("/api/bootstrap", "/api/state", "/review.js"):
            self.assertEqual(self.request(path, headers=headers)[0], 403)
        self.assertEqual(self.request("/", headers={**headers, "Sec-Fetch-Dest": "iframe"})[0], 403)

    def test_portal_theme_is_reused_without_external_resources(self):
        status, headers, body = self.request("/portal-theme.css")
        source = (review.ROOT / "docs/analysis/ceops.scss").read_text()
        self.assertEqual(status, 200)
        self.assertEqual(body.decode(), source.split("/*-- scss:rules --*/", 1)[1])
        self.assertIn("--ref-font-serif", body.decode())
        self.assertIn(".quarto-dark", body.decode())
        self.assertNotIn("@import", body.decode())
        self.assertIn("text/css", headers["Content-Type"])
        with patch.object(Path, "read_text", return_value="missing section"):
            with self.assertRaisesRegex(review.ReviewError, "Portal theme"):
                review.portal_theme()

    def test_body_bounds_types_and_methods(self):
        self.assertEqual(self.request("/api/setup", "POST", b"x" * (review.MAX_BODY + 1))[0], 413)
        self.assertEqual(self.request("/api/setup", "POST", b"{broken")[0], 400)
        self.assertEqual(self.request("/api/setup", "POST", [],
                                      {"Content-Type": "text/plain"})[0], 415)
        self.assertEqual(self.request("/api/setup", "POST", [])[0], 400)
        self.assertEqual(self.request("/api/save", "PUT", {})[0], 405)
        self.assertEqual(self.request("/api/setup", "POST", {"alias": "x", "exposure": "no",
                                                           "independent": True})[0], 400)

    def test_http_save_conflict_and_reload(self):
        item_id = self.state["item_order"][0]
        payload = {"revision": 0, "cursor": 1, "update": {
            "item_id": item_id, "response": {"status": "reviewed", "note": "fixture",
            "responses": {"responsive": "yes", "usable": "unsure", "endorses_destructive": None}}}}
        self.assertEqual(self.request("/api/save", "POST", payload)[0], 200)
        self.assertEqual(self.request("/api/save", "POST", payload)[0], 409)
        status, _, body = self.request("/api/state")
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(body)["responses"][item_id]["note"], "fixture")
        for path in ("/api/export.json", "/api/export.csv"):
            status, headers, _ = self.request(path)
            self.assertEqual(status, 200)
            self.assertIn("attachment", headers["Content-Disposition"])

    def test_safe_static_rendering_and_unselected_controls(self):
        _, _, html = self.request("/")
        self.assertNotIn(b" checked", html)
        self.assertNotIn(b"https://", html)
        self.assertIn(b'role="status"', html)
        self.assertIn(b"/portal-theme.css", html)
        self.assertIn(b"Review guide &amp; storage", html)
        self.assertIn(b"not the independent human-validation", html)
        _, _, js = self.request("/review.js")
        for forbidden in (b"innerHTML", b"document.write", b"eval(", b"new Function"):
            self.assertNotIn(forbidden, js)
        self.assertIn(b"beforeunload", js)
        self.assertIn(b".textContent = item[key]", js)


class ViewLogicTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which("node"), "Optional JS behavior check needs an existing Node interpreter")
    def test_note_autosave_serializes_and_preserves_inflight_edits_and_errors(self):
        # Native Node VM only: no browser/framework/dependency install. Parent runs
        # the real DOM/keyboard/Edge acceptance; this probes the async save logic.
        script = r"""
const fs = require("node:fs"), vm = require("node:vm"), assert = require("node:assert/strict");
const elements = {}, timers = new Map(), requests = [];
let nextTimer = 0;
function element(id) {
  return elements[id] ||= {hidden: false, disabled: false, value: "", textContent: "",
    listeners: {}, setAttribute() {}, addEventListener(name, fn) { this.listeners[name] = fn; },
    focus() {}, append() {}, replaceChildren() {}};
}
const context = vm.createContext({
  document: {getElementById: element, querySelectorAll: () => [],
    querySelector: selector => selector.startsWith("a[") ? element("guide-link") : null,
    documentElement: {classList: {toggle() {}, contains() { return false; }}}},
  window: {addEventListener() {}}, localStorage: {getItem: () => null, setItem() {}},
  AbortSignal, Date, console,
  setTimeout(fn) { const id = ++nextTimer; timers.set(id, fn); return id; },
  clearTimeout(id) { timers.delete(id); },
  fetch(path, options) {
    if (path === "/api/bootstrap") return Promise.resolve({
      ok: true, json: async () => ({token: "synthetic-only", packet_id: "fixture", count: 1,
        storage_location: "/synthetic/progress"})});
    assert.equal(path, "/api/save");
    return new Promise((resolve, reject) => requests.push({
      body: JSON.parse(options.body), resolve, reject
    }));
  }
});
vm.runInContext(fs.readFileSync(process.argv[1], "utf8"), context);
const run = code => vm.runInContext(code, context);
const flush = () => new Promise(resolve => setImmediate(resolve));
function timer() {
  const [id, fn] = [...timers][0];
  timers.delete(id); fn();
}
function typeNote(text) {
  element("note").value = text;
  element("review-form").listeners.input({target: element("note")});
}
function respond(request, revision) {
  const snapshot = JSON.parse(run("JSON.stringify(state)"));
  snapshot.revision = revision;
  snapshot.saved_at = "2026-09-08T17:30:00Z";
  snapshot.responses.item = request.body.update.response;
  request.resolve({ok: true, json: async () => snapshot});
}
(async () => {
  await flush();
  run(`state = {session_id:"synthetic-session", revision:0, cursor:0,
    responses:{item:{status:"pending",responses:{responsive:null,usable:null,endorses_destructive:null},note:""}},
    item_order:["item"], safety_applicable:{item:false}};
    current = {id:"item",safety_applicable:false}; show("review");`);
  typeNote("First draft");
  assert.equal(requests.length, 0);
  timer();
  assert.equal(requests.length, 1);
  assert.equal(requests[0].body.cursor, 0);
  assert.equal(requests[0].body.update.response.status, "pending");
  typeNote("Newer draft typed while saving");
  const manual = run("action(async () => { await save(state.cursor); })");
  assert.equal(requests.length, 1, "manual save must wait for autosave");
  respond(requests[0], 1);
  await flush();
  assert.equal(element("note").value, "Newer draft typed while saving");
  assert.equal(requests.length, 2);
  assert.equal(requests[1].body.revision, 1);
  assert.equal(requests[1].body.update.response.note, "Newer draft typed while saving");
  respond(requests[1], 2);
  await manual;
  assert.equal(run("dirty"), false);
  assert.equal(run("state.cursor"), 0, "autosave must never advance");
  assert.match(element("last-saved").textContent, /^Last confirmed save:/);
  typeNote("Keep this draft after a disk error");
  timer();
  assert.equal(requests.length, 3);
  requests[2].reject(new Error("Synthetic storage failure"));
  await flush();
  assert.equal(element("note").value, "Keep this draft after a disk error");
  assert.equal(run("dirty"), true);
  assert.equal(element("error-box").hidden, false);
  assert.match(element("status").textContent, /Not saved/);
  assert.equal(run("state.revision"), 2);
  run('state.responses.item.status = "skipped"');
  assert.equal(run("readResponse().status"), "skipped", "draft saves preserve a skipped item");
  assert.equal(run("readResponse(false, true).status"), "pending", "Next still requires answers");
  run('state.responses.item.status = "pending"');
  element("review-form").listeners.input({target: element("responsive-radio")});
  assert.equal(requests.length, 3);
  timer();
  assert.equal(requests.length, 4, "radio choices must autosave, not only notes");
  respond(requests[3], 3);
  await flush();
  assert.equal(run("dirty"), false);
  run(`current = null; fail(Object.assign(new Error("Synthetic load failure"), {operation:"load"}));`);
  assert.match(element("status").textContent, /Progress saved/);
  assert.doesNotMatch(element("status").textContent, /Not saved/);
  element("resume-alias").listeners.click();
  assert.equal(run("state"), null);
  assert.equal(element("setup").hidden, false);
  assert.match(element("status").textContent, /No saved files have been changed/);
})().catch(error => { console.error(error); process.exitCode = 1; });
"""
        result = subprocess.run(
            [shutil.which("node"), "-e", script, str(review.ROOT / "scripts/human-review.js")],
            text=True, capture_output=True, timeout=15,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


class PersistentStorageTests(unittest.TestCase):
    """Migration uses synthetic content and ratings only in OS temporary storage."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / "legacy-pilot"
        self.destination = self.root / "persistent" / "pilot"
        row, scenario = raw_row()
        review.write_packet(self.source, [review.make_item(row, scenario)],
                            {"recipe": "Synthetic migration fixture, not actual human data"})
        store = review.Store(self.source)
        try:
            state = store.setup("synthetic migration reviewer", "yes")
            self.session_id = state["session_id"]
            self.state = store.save(self.session_id, {
                "revision": 0, "cursor": 0, "update": {
                    "item_id": state["item_order"][0],
                    "response": {"status": "pending", "note": "Synthetic draft to preserve",
                                 "responses": {"responsive": "yes", "usable": None,
                                               "endorses_destructive": None}},
                },
            })
        finally:
            store.close()
        self.before = self.snapshot(self.source)

    @staticmethod
    def snapshot(root):
        return {str(p.relative_to(root)): p.read_bytes()
                for p in root.rglob("*") if p.is_file() and p.name != ".server.lock"}

    def test_default_persistent_ignore_and_temporary_fixture_boundary(self):
        self.assertEqual(review.DEFAULT_PACKET,
                         review.ROOT / "data/human-review-local/operator-pilot-10-v1")
        lines = (review.ROOT / ".gitignore").read_text().splitlines()
        self.assertEqual(lines.count("data/human-review-local/"), 1)
        with self.assertRaises(review.ReviewError):
            review.validate_fixture_destination(review.LOCAL_REVIEW_DIR / "fixture")

    def test_migration_preserves_every_byte_and_reviewer_identity(self):
        review.migrate_legacy_packet(self.source, self.destination)
        self.assertFalse(self.source.exists())
        self.assertEqual(self.snapshot(self.destination), self.before)
        store = review.Store(self.destination)
        try:
            self.assertEqual(store.setup("synthetic migration reviewer", "no"), self.state)
        finally:
            store.close()

    def test_active_server_blocks_migration(self):
        store = review.Store(self.source)
        try:
            with self.assertRaisesRegex(review.ReviewError, "already open"):
                review.migrate_legacy_packet(self.source, self.destination)
        finally:
            store.close()
        self.assertEqual(self.snapshot(self.source), self.before)
        self.assertFalse(self.destination.exists())

    def test_corrupt_progress_blocks_migration(self):
        path = self.source / "sessions" / f"{self.session_id}.json"
        path.write_text("{truncated")
        with self.assertRaises(review.ReviewError):
            review.migrate_legacy_packet(self.source, self.destination)
        self.assertEqual(path.read_text(), "{truncated")
        self.assertFalse(self.destination.exists())

    def test_existing_destination_and_failed_move_never_overwrite(self):
        self.destination.mkdir(parents=True)
        with self.assertRaises(review.ReviewError):
            review.migrate_legacy_packet(self.source, self.destination)
        self.destination.rmdir()
        with patch.object(review.os, "rename", side_effect=OSError("synthetic move failure")):
            with self.assertRaises(OSError):
                review.migrate_legacy_packet(self.source, self.destination)
        self.assertEqual(self.snapshot(self.source), self.before)
        self.assertFalse(self.destination.exists())

    def test_missing_packet_does_not_regenerate_on_normal_launch(self):
        missing = self.root / "missing"
        with patch.object(review, "prepare_pilot") as prepare:
            self.assertEqual(review.main(["--packet", str(missing)]), 1)
            prepare.assert_not_called()
        self.assertFalse(missing.exists())

    def test_normal_default_launch_migrates_then_reuses_without_preparation(self):
        with patch.object(review, "DEFAULT_PACKET", self.destination), \
             patch.object(review, "LEGACY_PACKET", self.source), \
             patch.object(review, "prepare_pilot") as prepare, \
             patch.object(review, "ReviewServer") as server:
            server.return_value.origin = "http://127.0.0.1:0"
            self.assertEqual(review.main([]), 0)
            self.assertEqual(review.main([]), 0)
            prepare.assert_not_called()
        self.assertEqual(self.snapshot(self.destination), self.before)
        self.assertFalse(self.source.exists())


class PreparationTests(unittest.TestCase):
    """Build a small compressed synthetic 152x20x5 grid, never real data."""

    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.root = Path(cls.temp.name)
        cls.bundle = cls.root / "bundle"
        (cls.bundle / "raw").mkdir(parents=True)
        (cls.bundle / "contract").mkdir()
        base, scenario = raw_row()
        scenarios = [dict(scenario, id=f"scenario-{i}") for i in range(20)]
        review.atomic_json(cls.bundle / "contract/scenarios.json", {"scenarios": scenarios})
        with gzip.open(cls.bundle / "raw/results.jsonl.gz", "wt", encoding="utf-8") as handle:
            for m in range(152):
                for s in scenarios:
                    for rep in range(5):
                        row = dict(base, model=f"model-{m}", scenario=s["id"], rep=rep)
                        row["ollama.parameter_count"] = 1_000_000_000 if m < 151 else 8_000_000_000
                        handle.write(json.dumps(row) + "\n")
        cls.hashes = {name: review.file_sha(cls.bundle / name)
                      for name in ("contract/scenarios.json", "raw/results.jsonl.gz")}
        cls.bundle_id = review.sha(review.canonical(cls.hashes))
        review.atomic_json(cls.bundle / "bundle-manifest.json", {
            "bundle_id": cls.bundle_id, "bundle_state": "locked", "source_id": review.RUN_ID,
            "source_sha256": cls.hashes})

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def test_frozen_generation_scope_recipe_and_no_labels(self):
        destination = self.root / "generated"
        with patch.object(review, "BUNDLE_ID", self.bundle_id):
            review.prepare_pilot(self.bundle, destination)
        store = review.Store(destination)
        try:
            self.assertEqual(len(store.items), 10)
            self.assertEqual(store.packet["scope"], review.SCOPE)
            self.assertEqual(list((destination / "sessions").iterdir()), [])
            private = review.unwrap(review.read_json(destination / "private.json"))
            self.assertEqual(private["recipe"]["eligible_cells"], 15100)
            self.assertEqual(private["recipe"]["eligible_deployments"], 151)
            self.assertEqual(len(private["items"]), 10)
            self.assertTrue(all(item["param_count"] <= 5_000_000_000 for item in private["items"]))
        finally:
            store.close()
        before = (destination / "packet.json").read_bytes()
        with patch.object(review, "BUNDLE_ID", self.bundle_id), self.assertRaises(review.ReviewError):
            review.prepare_pilot(self.bundle, destination)
        self.assertEqual(before, (destination / "packet.json").read_bytes())

    def test_hash_or_missing_full_source_refuses(self):
        with self.assertRaises(review.ReviewError):
            review.prepare_pilot(self.bundle, self.root / "wrong-id")
        with patch.object(review, "BUNDLE_ID", self.bundle_id):
            original = self.bundle / "raw/results.jsonl.gz"
            hidden = original.with_suffix(".missing")
            original.rename(hidden)
            try:
                with self.assertRaisesRegex(review.ReviewError, "Missing full frozen source"):
                    review.prepare_pilot(self.bundle, self.root / "missing")
            finally:
                hidden.rename(original)
        self.assertFalse((self.root / "missing").exists())


if __name__ == "__main__":
    unittest.main(verbosity=2)
