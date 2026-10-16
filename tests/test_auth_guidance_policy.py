"""Documentation must preserve the project's explicit auth boundaries."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _policy_documents() -> list[Path]:
    documents = list(ROOT.glob("README*.md"))
    for directory in (
        ROOT / "docs",
        ROOT / "scrap_master" / "guides",
        ROOT / "scrap_master" / "skill",
    ):
        documents.extend(directory.rglob("*.md"))
    return sorted(set(documents))






def test_twitter_operational_docs_explain_the_environment_boundary():
    """Saved cookies help doctor only; direct twitter commands need env vars."""
    operational_docs = (
        ROOT / "README.md",
        ROOT / "docs" / "cookie-export.md",
        ROOT / "docs" / "install.md",
        ROOT / "docs" / "troubleshooting.md",
        ROOT / "scrap_master" / "guides" / "setup-twitter.md",
        ROOT / "scrap_master" / "skill" / "SKILL.md",
        ROOT / "scrap_master" / "skill" / "references" / "social.md",
    )

    for path in operational_docs:
        text = path.read_text(encoding="utf-8")
        assert "TWITTER_AUTH_TOKEN" in text, path.relative_to(ROOT)
        assert "TWITTER_CT0" in text, path.relative_to(ROOT)

    twitter_guide = (
        ROOT / "scrap_master" / "guides" / "setup-twitter.md"
    ).read_text(encoding="utf-8")
    assert "does not run `twitter status`" in twitter_guide
    assert "does not modify the current shell" in twitter_guide
    assert "Export → Header String" in twitter_guide
    assert "cookie JSON" not in twitter_guide
    assert "Copy all" not in twitter_guide

    for expected in (
        "--sync-legacy-twitter",
        "~/.scrap-master/config.yaml",
        "~/.config/xfetch/session.json",
        "~/.config/bird/credentials.env",
    ):
        assert expected in twitter_guide
    assert "By default, only" in twitter_guide
    assert "will not auto-delete" in twitter_guide

    rendered_as_verified = (
        "✅ Twitter/X tweets",
    )
    all_text = "\n".join(
        path.read_text(encoding="utf-8") for path in _policy_documents()
    )
    assert not any(claim in all_text for claim in rendered_as_verified)




def test_public_guidance_never_installs_the_unrelated_pypi_package():
    """Install instructions must use the GitHub URL, not a bare PyPI name."""
    candidates = _policy_documents() + [
        ROOT / "scrap_master" / "integrations" / "mcp_server.py",
    ]
    bare_install = re.compile(
        r"\bpip\s+install(?:\s+--upgrade)?\s+['\"]?scrap-master(?:\[[^\]]+\])?\b",
        re.IGNORECASE,
    )
    violations = []
    for path in candidates:
        for line_number, line in enumerate(
            path.read_text(encoding="utf-8").splitlines(), 1
        ):
            if bare_install.search(line) and (
                "github.com/festomanolo/scrap-master" not in line
            ):
                violations.append(
                    f"{path.relative_to(ROOT)}:{line_number}: {line.strip()}"
                )

    assert not violations, "\n".join(violations)




def test_skill_explains_unverified_backend_state():
    """A null backend is an explicit safety state, not a routing instruction."""
    skills = (
        ROOT / "scrap_master" / "skill" / "SKILL.md",
    )
    for path in skills:
        text = path.read_text(encoding="utf-8")
        assert "active_backend: null" in text, path.relative_to(ROOT)
        assert "Doctor" in text, path.relative_to(ROOT)


def test_video_reference_has_content_level_youtube_fallbacks():
    """Version-only health must not be presented as proof subtitles work."""
    text = (
        ROOT / "scrap_master" / "skill" / "references" / "video.md"
    ).read_text(encoding="utf-8")
    assert "opencli youtube transcript" in text
    assert "retry up to 3 times" in text
    assert "scrap-master transcribe" in text


