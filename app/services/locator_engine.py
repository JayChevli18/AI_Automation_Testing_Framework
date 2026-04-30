"""Basic locator resolution strategies for Playwright."""

from __future__ import annotations

from playwright.async_api import Locator, Page


def _accessible_name_from_target(raw: str) -> str:
    """Strip UI prose so role name matches aria-label / visible text (e.g. Sign In link)."""
    lower = raw.strip().lower()
    for noise in (
        " on the login form",
        " on the sign-in form",
        " on sign-in form",
        " at the bottom of the form",
        " in header",
        " in the header",
        " on the page",
        " in page",
    ):
        if lower.endswith(noise):
            lower = lower[: -len(noise)].strip()
            break
    parts = [w for w in lower.split() if w not in ("button", "link")]
    name = " ".join(parts) if parts else lower
    if name.endswith(" submit"):
        name = name[: -len(" submit")].strip()
    return name


class LocatorEngine:
    """Resolve elements using simple role/label/text heuristics."""

    async def resolve(self, page: Page, action: str, target: str) -> tuple[Locator, str]:
        normalized = (target or "").strip()
        if not normalized:
            raise ValueError("Empty target for locator resolution.")

        # click/assert paths: role and text heuristics
        if action in {"hover", "click", "assert_visible", "assert_text"}:
            lower = normalized.lower()
            name = _accessible_name_from_target(normalized)
            words = lower.split()
            # Header "Sign In" is usually a link; the login form often uses a <button>SIGN IN</button>.
            # Only treat sign-in/log-in as a link when the target clearly refers to header/nav (not the form).
            nav_hint = any(
                w in lower
                for w in ("header", "navigation", "nav bar", "top bar", "site menu")
            ) or "link" in words
            if action == "click" and nav_hint and (
                "sign in" in lower
                or "sign-in" in lower
                or "log in" in lower
                or name in ("sign in", "sign-in", "log in")
            ):
                return page.get_by_role("link", name=name or "sign in"), "role_link_signin"
            if "link" in words:
                link_name = name or lower.replace("link", "").strip()
                return page.get_by_role("link", name=link_name), "role_link"
            if "button" in lower:
                return page.get_by_role("button", name=name or lower), "role_button"
            return page.get_by_text(normalized, exact=False), "text"

        # fill path: label / placeholder / basic input fallback.
        if action == "fill":
            lower = normalized.lower()
            if "email" in lower:
                return (
                    page.locator("input[type='email'], input[name*='email'], input[id*='email']"),
                    "input_email",
                )
            if "password" in lower:
                return (
                    page.locator(
                        "input[type='password'], input[name*='password'], input[id*='password']"
                    ),
                    "input_password",
                )
            return page.get_by_label(normalized), "label"

        # Default fallback.
        return page.get_by_text(normalized, exact=False), "text_fallback"

