#!/usr/bin/env python3
"""WordPress draft handoff tests. All HTTP is fake; no live site."""

from __future__ import annotations

import io
import json
import re
import sys
import tempfile
import unittest
import urllib.parse
from contextlib import redirect_stderr
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
from wordpress_handoff.handoff import count_words, format_dry_run, run_handoff  # noqa: E402
from wordpress_handoff.packet import parse_packet  # noqa: E402
from wordpress_handoff.payload import build_payload, reject_elementor_fields  # noqa: E402
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


CREDS = {
    "WP_BASE_URL": "https://example.com",
    "WP_USERNAME": "bot",
    "WP_APP_PASSWORD": SECRET,
}

OLD_HTML = "<h2>Old section</h2><p>One two three four.</p>"


def _state_with_post(
    post_id: int = 441,
    slug: str = "old-slug",
    handoff_at: str = "2026-09-02T01:58:55Z",
) -> str:
    return STATE.replace(
        "- review_path:",
        (
            f"- wordpress_post_id: {post_id}\n"
            "- wordpress_status: draft\n"
            f"- wordpress_slug: {slug}\n"
            f"- wordpress_handoff_at: {handoff_at}\n"
            "- wordpress_edit_url: "
            f"https://example.com/wp-admin/post.php?post={post_id}&action=edit\n"
            "- review_path:"
        ),
    )


def _remote_post(
    *,
    post_id: int = 441,
    status: str = "draft",
    slug: str = "old-slug",
    title: str = "Old headline",
    content: str = OLD_HTML,
) -> dict:
    return {
        "id": post_id,
        "status": status,
        "slug": slug,
        "title": {"raw": title, "rendered": title},
        "content": {"raw": content, "rendered": content},
        "excerpt": {"raw": "Old excerpt", "rendered": "Old excerpt"},
    }


def _update_client(
    tmp: Path,
    *,
    post: dict,
    recorder: list,
    slug_hits: list | None = None,
    post_response: dict | None = None,
    status_code: int = 200,
) -> WordPressClient:
    creds = load_credentials(tmp, environ=CREDS)

    def opener(request):
        method = request.get_method()
        url = request.full_url
        path = urllib.parse.urlparse(url).path
        entry = {"method": method, "url": url, "body": request.data}
        recorder.append(entry)
        if method in {"PUT", "PATCH", "DELETE"}:
            raise AssertionError(f"forbidden method {method}")
        if method == "GET" and re.search(r"/posts/\d+$", path):
            if status_code != 200:
                return HttpResponse(status_code, {"code": "rest_post_invalid_id"})
            return HttpResponse(200, post)
        if method == "GET":
            return HttpResponse(200, [] if slug_hits is None else slug_hits)
        if method == "POST":
            payload = json.loads(request.data.decode("utf-8"))
            entry["payload"] = payload
            if not re.search(r"/posts/\d+$", path):
                raise AssertionError(f"update must POST to the post URL, got {url}")
            body = post_response or {
                "id": post["id"],
                "status": "draft",
                "slug": payload.get("slug"),
            }
            return HttpResponse(200, body)
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

    def test_update_refuses_without_existing_post_id(self):
        with tempfile.TemporaryDirectory() as raw:
            tmp = _write_repo(Path(raw))
            recorder: list = []
            client = _update_client(tmp, post=_remote_post(), recorder=recorder)
            with self.assertRaises(HandoffError) as ctx:
                run_handoff(
                    tmp,
                    "bc-20260901-10",
                    update=True,
                    apply=True,
                    client=client,
                    environ=CREDS,
                )
            self.assertIn("wordpress_post_id", str(ctx.exception))
            self.assertIn("will not create", str(ctx.exception))
            self.assertEqual(recorder, [])

    def test_update_refuses_non_draft_statuses(self):
        refused = ("publish", "future", "private", "trash", "inherit")
        for status in refused:
            with self.subTest(status=status):
                with tempfile.TemporaryDirectory() as raw:
                    tmp = _write_repo(Path(raw), state_text=_state_with_post())
                    recorder: list = []
                    client = _update_client(
                        tmp,
                        post=_remote_post(status=status),
                        recorder=recorder,
                    )
                    with self.assertRaises(HandoffError) as ctx:
                        run_handoff(
                            tmp,
                            "bc-20260901-10",
                            update=True,
                            apply=True,
                            client=client,
                            environ=CREDS,
                        )
                    self.assertIn(repr(status), str(ctx.exception))
                    self.assertTrue(all(item["method"] != "POST" for item in recorder))
                    self.assertNotIn(SECRET, str(ctx.exception))

    def test_update_allows_pending_but_sends_only_draft(self):
        with tempfile.TemporaryDirectory() as raw:
            tmp = _write_repo(Path(raw), state_text=_state_with_post())
            recorder: list = []
            client = _update_client(
                tmp,
                post=_remote_post(status="pending"),
                recorder=recorder,
            )
            result = run_handoff(
                tmp,
                "bc-20260901-10",
                update=True,
                apply=True,
                client=client,
                environ=CREDS,
            )
            self.assertEqual(result.mode, "update")
            self.assertEqual(result.wordpress_post_id, 441)
            posts = [item for item in recorder if item["method"] == "POST"]
            self.assertEqual(len(posts), 1)
            self.assertEqual(posts[0]["payload"]["status"], "draft")
            self.assertNotIn("pending", posts[0]["payload"].values())
            self.assertNotIn("publish", posts[0]["payload"].values())

    def test_update_client_refuses_non_draft_payload_without_write(self):
        with tempfile.TemporaryDirectory() as raw:
            tmp = _write_repo(Path(raw), state_text=_state_with_post())
            recorder: list = []
            client = _update_client(tmp, post=_remote_post(), recorder=recorder)
            for status in ("publish", "future", "private", "pending", "trash"):
                with self.subTest(status=status):
                    with self.assertRaises(HandoffError):
                        client.update_draft(441, {"status": status, "title": "x"})
            self.assertEqual(recorder, [])

    def test_update_slug_change_dry_run_and_apply(self):
        with tempfile.TemporaryDirectory() as raw:
            tmp = _write_repo(Path(raw), state_text=_state_with_post())
            recorder: list = []
            client = _update_client(tmp, post=_remote_post(), recorder=recorder)
            dry = run_handoff(
                tmp,
                "bc-20260901-10",
                update=True,
                apply=False,
                slug="naisha-911-rewrite",
                client=client,
                environ=CREDS,
            )
            summary = format_dry_run(dry)
            self.assertIn("post ID 441 will be updated", summary)
            self.assertIn("old: old-slug", summary)
            self.assertIn("new: naisha-911-rewrite", summary)
            self.assertIn(
                "Slug change on unpublished draft: old-slug -> naisha-911-rewrite",
                summary,
            )
            self.assertEqual(dry.payload["status"], "draft")
            self.assertEqual(dry.payload["slug"], "naisha-911-rewrite")
            self.assertTrue(all(item["method"] != "POST" for item in recorder))
            state_path = tmp / "content/state/bc-20260901-10-naisha-911.md"
            self.assertIn("wordpress_slug: old-slug", state_path.read_text())

            apply_recorder: list = []
            apply_client = _update_client(
                tmp, post=_remote_post(), recorder=apply_recorder
            )
            applied = run_handoff(
                tmp,
                "bc-20260901-10",
                update=True,
                apply=True,
                slug="naisha-911-rewrite",
                client=apply_client,
                environ=CREDS,
            )
            self.assertFalse(applied.dry_run)
            posts = [item for item in apply_recorder if item["method"] == "POST"]
            self.assertEqual(len(posts), 1)
            self.assertEqual(posts[0]["payload"]["slug"], "naisha-911-rewrite")
            self.assertEqual(posts[0]["payload"]["status"], "draft")
            written = state_path.read_text(encoding="utf-8")
            self.assertIn("- wordpress_slug: naisha-911-rewrite", written)
            self.assertIn("- wordpress_post_id: 441", written)

    def test_update_does_not_create_a_second_post(self):
        with tempfile.TemporaryDirectory() as raw:
            tmp = _write_repo(Path(raw), state_text=_state_with_post())
            with self.assertRaises(HandoffError) as ctx:
                run_handoff(tmp, "bc-20260901-10", apply=False)
            self.assertEqual(str(ctx.exception), DUPLICATE_MESSAGE)

            recorder: list = []
            client = _update_client(tmp, post=_remote_post(), recorder=recorder)
            run_handoff(
                tmp,
                "bc-20260901-10",
                update=True,
                apply=True,
                client=client,
                environ=CREDS,
            )
            posts = [item for item in recorder if item["method"] == "POST"]
            self.assertEqual(len(posts), 1)
            path = urllib.parse.urlparse(posts[0]["url"]).path
            self.assertTrue(path.endswith("/posts/441"))
            self.assertNotEqual(path.rstrip("/"), "/wp-json/wp/v2/posts")
            self.assertEqual(posts[0]["payload"]["status"], "draft")
            for key in ("title", "content", "excerpt", "slug"):
                self.assertIn(key, posts[0]["payload"])
            gets = [item for item in recorder if item["method"] == "GET"]
            self.assertTrue(any("context=edit" in item["url"] for item in gets))
            self.assertTrue(any("/posts/441" in item["url"] for item in gets))

    def test_update_dry_run_prints_diff_and_makes_no_write(self):
        with tempfile.TemporaryDirectory() as raw:
            tmp = _write_repo(Path(raw), state_text=_state_with_post())
            state_path = tmp / "content/state/bc-20260901-10-naisha-911.md"
            before = state_path.read_text(encoding="utf-8")
            recorder: list = []
            client = _update_client(tmp, post=_remote_post(), recorder=recorder)
            result = run_handoff(
                tmp,
                "bc-20260901-10",
                update=True,
                apply=False,
                client=client,
                environ=CREDS,
            )
            summary = format_dry_run(result)
            self.assertTrue(result.dry_run)
            self.assertEqual(result.mode, "update")
            self.assertEqual(result.wordpress_post_id, 441)
            self.assertIn(
                "UPDATE DRY RUN for bc-20260901-10: post ID 441 will be updated.",
                summary,
            )
            self.assertIn("old: Old headline", summary)
            self.assertIn("new: Naisha said 911 is hers", summary)
            self.assertIn("old: old-slug", summary)
            self.assertIn(
                "new: naisha-911-completely-mine-not-a-skrillex-feature",
                summary,
            )
            self.assertIn(f"  old: {count_words(OLD_HTML)}", summary)
            self.assertIn(
                f"  new: {count_words(result.payload['content'])}",
                summary,
            )
            self.assertIn("    - h2: Old section", summary)
            self.assertIn("    - h3: A subhead", summary)
            self.assertIn('"status": "draft"', summary)
            self.assertNotIn(SECRET, summary)
            self.assertEqual([item["method"] for item in recorder], ["GET"])
            self.assertIn("/posts/441", recorder[0]["url"])
            self.assertIn("context=edit", recorder[0]["url"])
            self.assertEqual(state_path.read_text(encoding="utf-8"), before)

    def test_update_missing_post_refuses(self):
        with tempfile.TemporaryDirectory() as raw:
            tmp = _write_repo(Path(raw), state_text=_state_with_post())
            recorder: list = []
            client = _update_client(
                tmp,
                post=_remote_post(),
                recorder=recorder,
                status_code=404,
            )
            with self.assertRaises(HandoffError) as ctx:
                run_handoff(
                    tmp,
                    "bc-20260901-10",
                    update=True,
                    apply=True,
                    client=client,
                    environ=CREDS,
                )
            self.assertIn("does not exist", str(ctx.exception))
            self.assertTrue(all(item["method"] != "POST" for item in recorder))

    def test_update_slug_collision_refuses_without_post(self):
        with tempfile.TemporaryDirectory() as raw:
            tmp = _write_repo(Path(raw), state_text=_state_with_post())
            recorder: list = []
            client = _update_client(
                tmp,
                post=_remote_post(),
                recorder=recorder,
                slug_hits=[{"id": 99, "slug": "naisha-911-rewrite"}],
            )
            with self.assertRaises(HandoffError) as ctx:
                run_handoff(
                    tmp,
                    "bc-20260901-10",
                    update=True,
                    apply=True,
                    slug="naisha-911-rewrite",
                    client=client,
                    environ=CREDS,
                )
            self.assertIn("already belongs to", str(ctx.exception))
            self.assertIn("99", str(ctx.exception))
            self.assertTrue(all(item["method"] != "POST" for item in recorder))

    def test_update_apply_records_handoff_and_keeps_editorial_status(self):
        with tempfile.TemporaryDirectory() as raw:
            tmp = _write_repo(Path(raw), state_text=_state_with_post())
            recorder: list = []
            client = _update_client(tmp, post=_remote_post(), recorder=recorder)
            result = run_handoff(
                tmp,
                "bc-20260901-10",
                update=True,
                apply=True,
                client=client,
                environ=CREDS,
            )
            self.assertEqual(result.wordpress_post_id, 441)
            self.assertIn("Updated WordPress draft id=441", result.message)
            self.assertIn("READY_FOR_REVIEW", result.message)
            text = (
                tmp / "content/state/bc-20260901-10-naisha-911.md"
            ).read_text(encoding="utf-8")
            self.assertIn("- wordpress_post_id: 441", text)
            self.assertIn("- wordpress_status: draft", text)
            self.assertNotIn("- wordpress_handoff_at: 2026-09-02T01:58:55Z", text)
            self.assertRegex(
                text,
                r"- wordpress_handoff_at: \d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z",
            )
            self.assertIn("updated in place post_id=441", text)
            self.assertEqual(STATUS_RE.search(text).group(1), "READY_FOR_REVIEW")
            self.assertNotIn("status: APPROVED", text)
            self.assertIn("- updated: 2026-09-01", text)
            self.assertNotIn(SECRET, text)

    def test_update_sends_taxonomy_and_skips_elementor_meta(self):
        cfg = {
            **CONFIG,
            "taxonomy": {
                "unmapped_category": "omit",
                "unmapped_tag": "omit",
                "categories": {"Music": 12},
                "tags": {"Naisha": 9},
            },
        }
        with tempfile.TemporaryDirectory() as raw:
            tmp = _write_repo(Path(raw), state_text=_state_with_post(), config=cfg)
            recorder: list = []
            client = _update_client(tmp, post=_remote_post(), recorder=recorder)
            run_handoff(
                tmp,
                "bc-20260901-10",
                update=True,
                apply=True,
                client=client,
                environ=CREDS,
            )
            payload = [item for item in recorder if item["method"] == "POST"][0]["payload"]
            self.assertEqual(payload["categories"], [12])
            self.assertEqual(payload["tags"], [9])
            self.assertEqual(payload["status"], "draft")
            encoded = json.dumps(payload)
            for key in (
                "_elementor_edit_mode",
                "_elementor_data",
                "_elementor_template_type",
            ):
                self.assertNotIn(f'"{key}"', encoded)
            prose = {
                "status": "draft",
                "content": "The draft mentions _elementor_data as a word.",
            }
            reject_elementor_fields(prose)
            blocked: list = []
            guarded = _update_client(tmp, post=_remote_post(), recorder=blocked)
            with self.assertRaises(HandoffError) as ctx:
                guarded.update_draft(
                    441,
                    {
                        "status": "draft",
                        "title": "t",
                        "meta": {
                            "_elementor_edit_mode": "builder",
                            "_elementor_data": "[]",
                            "_elementor_template_type": "wp-post",
                        },
                    },
                )
            self.assertIn("_elementor_data", str(ctx.exception))
            self.assertNotIn("builder", str(ctx.exception))
            self.assertEqual(blocked, [])

    def test_update_refuses_non_draft_response_without_state_write(self):
        with tempfile.TemporaryDirectory() as raw:
            tmp = _write_repo(Path(raw), state_text=_state_with_post())
            state_path = tmp / "content/state/bc-20260901-10-naisha-911.md"
            before = state_path.read_text(encoding="utf-8")
            recorder: list = []
            client = _update_client(
                tmp,
                post=_remote_post(),
                recorder=recorder,
                post_response={"id": 441, "status": "publish", "slug": "old-slug"},
            )
            with self.assertRaises(HandoffError) as ctx:
                run_handoff(
                    tmp,
                    "bc-20260901-10",
                    update=True,
                    apply=True,
                    client=client,
                    environ=CREDS,
                )
            self.assertIn("status=draft", str(ctx.exception))
            self.assertEqual(state_path.read_text(encoding="utf-8"), before)
            self.assertEqual(recorder[-1]["payload"]["status"], "draft")

    def test_update_dry_run_requires_https_and_does_not_leak_secrets(self):
        with tempfile.TemporaryDirectory() as raw:
            tmp = _write_repo(Path(raw), state_text=_state_with_post())
            with self.assertRaises(HandoffError) as ctx:
                run_handoff(
                    tmp,
                    "bc-20260901-10",
                    update=True,
                    apply=False,
                    environ={
                        "WP_BASE_URL": "http://example.com",
                        "WP_USERNAME": "bot",
                        "WP_APP_PASSWORD": SECRET,
                    },
                )
            self.assertIn("HTTPS", str(ctx.exception))
            self.assertNotIn(SECRET, str(ctx.exception))

            def opener(request):
                raise HandoffError(f"upstream said password={SECRET}")

            creds = load_credentials(tmp, environ=CREDS)
            client = WordPressClient(creds, opener=opener)
            with self.assertRaises(HandoffError) as leaked:
                run_handoff(
                    tmp,
                    "bc-20260901-10",
                    update=True,
                    apply=False,
                    client=client,
                    environ=CREDS,
                )
            self.assertNotIn(SECRET, str(leaked.exception))
            self.assertIn("[REDACTED]", str(leaked.exception))

    def test_update_invalid_slug_and_cli_flags(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            with_id = root / "with-id"
            with_id.mkdir()
            tmp = _write_repo(with_id, state_text=_state_with_post())
            with self.assertRaises(HandoffError) as ctx:
                run_handoff(
                    tmp,
                    "bc-20260901-10",
                    update=True,
                    slug="Not A Slug",
                    apply=False,
                )
            self.assertIn("lowercase hyphenated", str(ctx.exception))

            bare_root = root / "bare"
            bare_root.mkdir()
            bare = _write_repo(bare_root)
            err = io.StringIO()
            with redirect_stderr(err):
                missing = main(
                    ["bc-20260901-10", "--update", "--repo-root", str(bare)]
                )
            self.assertEqual(missing, 1)
            self.assertIn("wordpress_post_id", err.getvalue())
            self.assertNotIn(SECRET, err.getvalue())

            err = io.StringIO()
            with redirect_stderr(err):
                slug_only = main(
                    ["bc-20260901-10", "--slug", "new-slug", "--repo-root", str(bare)]
                )
            self.assertEqual(slug_only, 1)
            self.assertIn("--slug", err.getvalue())

            err = io.StringIO()
            with redirect_stderr(err):
                publish = main(
                    [
                        "bc-20260901-10",
                        "--update",
                        "--publish",
                        "--repo-root",
                        str(bare),
                    ]
                )
            self.assertEqual(publish, 1)
            self.assertIn("Drafts only", err.getvalue())


if __name__ == "__main__":
    unittest.main()
