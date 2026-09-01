#!/usr/bin/env python3
"""WordPress draft handoff tests. All HTTP is fake; no live site."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

from wordpress_handoff import ALLOWED_WP_STATUS, DUPLICATE_MESSAGE  # noqa: E402
from wordpress_handoff.cli import main  # noqa: E402
from wordpress_handoff.client import HttpResponse, WordPressClient  # noqa: E402
from wordpress_handoff.convert import markdown_to_wp_html  # noqa: E402
from wordpress_handoff.credentials import load_credentials  # noqa: E402
from wordpress_handoff.errors import HandoffError  # noqa: E402
from wordpress_handoff.handoff import run_handoff  # noqa: E402
from wordpress_handoff.packet import parse_packet  # noqa: E402
from wordpress_handoff.payload import build_payload  # noqa: E402
from wordpress_handoff.state import STATUS_RE  # noqa: E402

SECRET = "super-secret-app-password-xyz"
PACKET = """# Fixture headline

## Packet metadata

| Field | Value |
| --- | --- |
| Task ID | bc-20260901-10-fixture |
| State | READY_FOR_REVIEW |

## Proposed headline

Naisha said 911 is hers

## Full draft

She said the project “feels completely mine.”

### A subhead

More body. A **strong** word and an *italic* word.

## Facts requiring final verification

None for this fixture.

## SEO title

seo title unused

## Meta description

meta unused

## Slug

naisha-911-completely-mine-not-a-skrillex-feature

## Excerpt

Three tracks dated 7 August 2026.

## Category

Music

## Tags

Naisha, Skrillex
"""

STATE = """# bc-20260901-10-naisha-911

- status: READY_FOR_REVIEW
- created: 2026-09-01
- updated: 2026-09-01
- beat: Music
- story_type_hypothesis: Feature
- recommendation:
- blocked_reason:
- research_path:
- draft_path:
- review_path: content/ready-for-review/20260901-bc-20260901-10-naisha-911.md

## Log

- 2026-09-01: READY_FOR_REVIEW
"""

CONFIG = {
    "api_path": "/wp-json/wp/v2/posts",
    "timeout_seconds": 5,
    "taxonomy": {
        "unmapped_category": "omit",
        "unmapped_tag": "omit",
        "categories": {},
        "tags": {},
    },
}


def _write_repo(
    tmp: Path,
    *,
    state_text: str = STATE,
    packet: str = PACKET,
    status: str | None = None,
    review_path: str | None = None,
    article_name: str = "20260901-bc-20260901-10-naisha-911.md",
    config: dict | None = None,
    write_article: bool = True,
) -> Path:
    (tmp / "config").mkdir()
    (tmp / "content" / "state").mkdir(parents=True)
    (tmp / "content" / "ready-for-review").mkdir(parents=True)
    cfg = dict(CONFIG if config is None else config)
    (tmp / "config" / "wordpress-handoff.json").write_text(
        json.dumps(cfg), encoding="utf-8"
    )
    text = state_text
    if status:
        text = STATUS_RE.sub(f"- status: {status}", text, count=1)
    if review_path is not None:
        text = text.replace(
            "content/ready-for-review/20260901-bc-20260901-10-naisha-911.md",
            review_path,
        )
    (tmp / "content" / "state" / "bc-20260901-10-naisha-911.md").write_text(
        text, encoding="utf-8"
    )
    if write_article:
        (tmp / "content" / "ready-for-review" / article_name).write_text(
            packet, encoding="utf-8"
        )
    return tmp


def _fake_client(
    tmp: Path,
    *,
    get_body,
    post_body,
    recorder: list,
    credentials=None,
) -> WordPressClient:
    creds = credentials or load_credentials(
        tmp,
        environ={
            "WP_BASE_URL": "https://example.com",
            "WP_USERNAME": "bot",
            "WP_APP_PASSWORD": SECRET,
        },
    )

    def opener(request):
        method = request.get_method()
        url = request.full_url
        recorder.append({"method": method, "url": url, "body": request.data})
        if method in {"PUT", "PATCH", "DELETE"}:
            raise AssertionError(f"forbidden method {method}")
        if method == "GET":
            return HttpResponse(200, get_body)
        if method == "POST":
            payload = json.loads(request.data.decode("utf-8"))
            recorder[-1]["payload"] = payload
            return HttpResponse(201, post_body)
        raise AssertionError(method)

    return WordPressClient(creds, opener=opener)


class HandoffTests(unittest.TestCase):
    def test_ready_for_review_candidate_accepted(self):
        with tempfile.TemporaryDirectory() as raw:
            tmp = _write_repo(Path(raw))
            result = run_handoff(tmp, "bc-20260901-10", apply=False)
            self.assertTrue(result.dry_run)
            self.assertEqual(result.payload["status"], "draft")
            self.assertEqual(
                result.payload["slug"],
                "naisha-911-completely-mine-not-a-skrillex-feature",
            )

    def test_non_ready_candidate_rejected(self):
        with tempfile.TemporaryDirectory() as raw:
            tmp = _write_repo(Path(raw), status="DISCOVERED")
            with self.assertRaises(HandoffError) as ctx:
                run_handoff(tmp, "bc-20260901-10", apply=False)
            self.assertIn("DISCOVERED", str(ctx.exception))
            self.assertIn("READY_FOR_REVIEW", str(ctx.exception))

    def test_missing_article_rejected(self):
        with tempfile.TemporaryDirectory() as raw:
            tmp = _write_repo(Path(raw), write_article=False)
            with self.assertRaises(HandoffError) as ctx:
                run_handoff(tmp, "bc-20260901-10", apply=False)
            self.assertIn("Missing article", str(ctx.exception))

    def test_missing_metadata_rejected(self):
        packet = PACKET.replace("naisha-911-completely-mine-not-a-skrillex-feature", "")
        packet = packet.replace("## Slug\n\n\n", "## Slug\n\n")
        with tempfile.TemporaryDirectory() as raw:
            tmp = _write_repo(Path(raw), packet=packet)
            with self.assertRaises(HandoffError) as ctx:
                run_handoff(tmp, "bc-20260901-10", apply=False)
            self.assertIn("Missing required article metadata", str(ctx.exception))
            self.assertIn("slug", str(ctx.exception))

    def test_dry_run_performs_no_network_write(self):
        with tempfile.TemporaryDirectory() as raw:
            tmp = _write_repo(Path(raw))
            recorder: list = []

            def opener(request):
                recorder.append(request)
                raise AssertionError("network should not run in dry-run")

            creds = load_credentials(
                tmp,
                environ={
                    "WP_BASE_URL": "https://example.com",
                    "WP_USERNAME": "bot",
                    "WP_APP_PASSWORD": SECRET,
                },
            )
            client = WordPressClient(creds, opener=opener)
            result = run_handoff(
                tmp, "bc-20260901-10", apply=False, client=client
            )
            self.assertTrue(result.dry_run)
            self.assertEqual(recorder, [])
            state = (tmp / "content/state/bc-20260901-10-naisha-911.md").read_text()
            self.assertNotIn("wordpress_post_id", state)

    def test_live_mode_requires_https(self):
        with tempfile.TemporaryDirectory() as raw:
            tmp = _write_repo(Path(raw))
            with self.assertRaises(HandoffError) as ctx:
                run_handoff(
                    tmp,
                    "bc-20260901-10",
                    apply=True,
                    environ={
                        "WP_BASE_URL": "http://example.com",
                        "WP_USERNAME": "bot",
                        "WP_APP_PASSWORD": SECRET,
                    },
                )
            self.assertIn("HTTPS", str(ctx.exception))

    def test_payload_always_forces_status_draft(self):
        with tempfile.TemporaryDirectory() as raw:
            tmp = _write_repo(Path(raw))
            packet = parse_packet(
                tmp / "content/ready-for-review/20260901-bc-20260901-10-naisha-911.md"
            )
            config = json.loads(
                (tmp / "config/wordpress-handoff.json").read_text(encoding="utf-8")
            )
            payload = build_payload(packet, config)
            self.assertEqual(payload["status"], ALLOWED_WP_STATUS)
            self.assertEqual(payload["status"], "draft")

    def test_publish_future_private_cannot_be_selected(self):
        with tempfile.TemporaryDirectory() as raw:
            tmp = _write_repo(Path(raw))
            packet = parse_packet(
                tmp / "content/ready-for-review/20260901-bc-20260901-10-naisha-911.md"
            )
            config = json.loads(
                (tmp / "config/wordpress-handoff.json").read_text(encoding="utf-8")
            )
            for status in ("publish", "future", "private", "pending"):
                with self.assertRaises(HandoffError):
                    build_payload(packet, config, status=status)
            self.assertEqual(
                main(["bc-20260901-10", "--status", "publish", "--repo-root", str(tmp)]),
                1,
            )
            self.assertEqual(
                main(["bc-20260901-10", "--publish", "--repo-root", str(tmp)]),
                1,
            )
            self.assertEqual(
                main(["bc-20260901-10", "--future", "--repo-root", str(tmp)]),
                1,
            )
            self.assertEqual(
                main(["bc-20260901-10", "--private", "--repo-root", str(tmp)]),
                1,
            )

    def test_duplicate_repo_wordpress_id_rejected(self):
        state = STATE.replace(
            "- review_path:",
            "- wordpress_post_id: 441\n- review_path:",
        )
        with tempfile.TemporaryDirectory() as raw:
            tmp = _write_repo(Path(raw), state_text=state)
            with self.assertRaises(HandoffError) as ctx:
                run_handoff(tmp, "bc-20260901-10", apply=False)
            self.assertEqual(str(ctx.exception), DUPLICATE_MESSAGE)

    def test_duplicate_slug_response_rejected(self):
        with tempfile.TemporaryDirectory() as raw:
            tmp = _write_repo(Path(raw))
            recorder: list = []
            client = _fake_client(
                tmp,
                get_body=[{"id": 7, "slug": "naisha-911-completely-mine-not-a-skrillex-feature"}],
                post_body={"id": 99, "status": "draft"},
                recorder=recorder,
            )
            with self.assertRaises(HandoffError) as ctx:
                run_handoff(
                    tmp,
                    "bc-20260901-10",
                    apply=True,
                    client=client,
                    environ={
                        "WP_BASE_URL": "https://example.com",
                        "WP_USERNAME": "bot",
                        "WP_APP_PASSWORD": SECRET,
                    },
                )
            self.assertEqual(str(ctx.exception), DUPLICATE_MESSAGE)
            self.assertTrue(all(c["method"] != "POST" for c in recorder))

    def test_missing_credentials_rejected_before_write(self):
        with tempfile.TemporaryDirectory() as raw:
            tmp = _write_repo(Path(raw))
            with self.assertRaises(HandoffError) as ctx:
                run_handoff(
                    tmp,
                    "bc-20260901-10",
                    apply=True,
                    environ={},
                )
            self.assertIn("Missing WordPress credentials", str(ctx.exception))

    def test_credentials_not_leaked_in_errors(self):
        with tempfile.TemporaryDirectory() as raw:
            tmp = _write_repo(Path(raw))

            def opener(request):
                raise HandoffError(f"upstream said password={SECRET}")

            creds = load_credentials(
                tmp,
                environ={
                    "WP_BASE_URL": "https://example.com",
                    "WP_USERNAME": "bot",
                    "WP_APP_PASSWORD": SECRET,
                },
            )
            client = WordPressClient(creds, opener=opener)
            with self.assertRaises(HandoffError) as ctx:
                run_handoff(
                    tmp,
                    "bc-20260901-10",
                    apply=True,
                    client=client,
                    environ={
                        "WP_BASE_URL": "https://example.com",
                        "WP_USERNAME": "bot",
                        "WP_APP_PASSWORD": SECRET,
                    },
                )
            self.assertNotIn(SECRET, str(ctx.exception))
            self.assertIn("[REDACTED]", str(ctx.exception))

    def test_successful_mocked_draft_records_post_id_and_preserves_status(self):
        with tempfile.TemporaryDirectory() as raw:
            tmp = _write_repo(Path(raw))
            recorder: list = []
            client = _fake_client(
                tmp,
                get_body=[],
                post_body={
                    "id": 88,
                    "status": "draft",
                    "slug": "naisha-911-completely-mine-not-a-skrillex-feature",
                    "link": "https://example.com/?p=88",
                },
                recorder=recorder,
            )
            result = run_handoff(
                tmp,
                "bc-20260901-10",
                apply=True,
                client=client,
                environ={
                    "WP_BASE_URL": "https://example.com",
                    "WP_USERNAME": "bot",
                    "WP_APP_PASSWORD": SECRET,
                },
            )
            self.assertEqual(result.wordpress_post_id, 88)
            self.assertEqual(recorder[0]["method"], "GET")
            self.assertEqual(recorder[1]["method"], "POST")
            self.assertEqual(recorder[1]["payload"]["status"], "draft")
            text = (tmp / "content/state/bc-20260901-10-naisha-911.md").read_text()
            self.assertIn("- wordpress_post_id: 88", text)
            self.assertIn("- wordpress_status: draft", text)
            self.assertEqual(STATUS_RE.search(text).group(1), "READY_FOR_REVIEW")
            self.assertNotIn("status: APPROVED", text)

    def test_existing_wordpress_post_never_updated_in_v1(self):
        with tempfile.TemporaryDirectory() as raw:
            tmp = _write_repo(Path(raw))
            recorder: list = []
            client = _fake_client(
                tmp,
                get_body=[],
                post_body={"id": 3, "status": "draft", "slug": "x"},
                recorder=recorder,
            )
            run_handoff(
                tmp,
                "bc-20260901-10",
                apply=True,
                client=client,
                environ={
                    "WP_BASE_URL": "https://example.com",
                    "WP_USERNAME": "bot",
                    "WP_APP_PASSWORD": SECRET,
                },
            )
            methods = [c["method"] for c in recorder]
            self.assertEqual(methods, ["GET", "POST"])
            self.assertNotIn("PUT", methods)
            self.assertNotIn("PATCH", methods)
            with self.assertRaises(HandoffError) as ctx:
                client._request("PUT", "https://example.com/wp-json/wp/v2/posts/3", {})
            self.assertIn("never updated", str(ctx.exception))

    def test_conversion_does_not_rewrite_quotes(self):
        html_out = markdown_to_wp_html(
            'She said the project “feels completely mine.”\n'
        )
        self.assertIn("feels completely mine", html_out)
        self.assertIn("“", html_out)
        self.assertIn("”", html_out)

    def test_unmapped_category_fail_closed_when_configured(self):
        cfg = {
            **CONFIG,
            "taxonomy": {
                "unmapped_category": "fail",
                "unmapped_tag": "omit",
                "categories": {},
                "tags": {},
            },
        }
        with tempfile.TemporaryDirectory() as raw:
            tmp = _write_repo(Path(raw), config=cfg)
            with self.assertRaises(HandoffError) as ctx:
                run_handoff(tmp, "bc-20260901-10", apply=False)
            self.assertIn("Unmapped WordPress category", str(ctx.exception))

    def test_cli_dry_run_exit_zero(self):
        with tempfile.TemporaryDirectory() as raw:
            tmp = _write_repo(Path(raw))
            code = main(["bc-20260901-10", "--repo-root", str(tmp)])
            self.assertEqual(code, 0)


if __name__ == "__main__":
    unittest.main()
