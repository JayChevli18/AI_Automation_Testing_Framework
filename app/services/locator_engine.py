"""Basic locator resolution strategies for Playwright."""

from __future__ import annotations

import re
from typing import Any

from playwright.async_api import Locator, Page

from app.services.selector_cache import SelectorCache

_ADD_TO_CART_TEXT = re.compile(r"add\s*to\s*cart", re.IGNORECASE)

_ORDINAL_PREFIX_TO_INDEX: dict[str, int] = {
    "first": 0,
    "1st": 0,
    "second": 1,
    "2nd": 1,
    "third": 2,
    "3rd": 2,
    "fourth": 3,
    "4th": 3,
    "fifth": 4,
    "5th": 4,
    "sixth": 5,
    "6th": 5,
    "seventh": 6,
    "7th": 6,
    "eighth": 7,
    "8th": 7,
    "ninth": 8,
    "9th": 8,
    "tenth": 9,
    "10th": 9,
}


def _leading_ordinal_index(lower: str) -> int | None:
    first = lower.strip().lower().split(maxsplit=1)[0] if lower.strip() else ""
    first = first.rstrip(".,;:")
    return _ORDINAL_PREFIX_TO_INDEX.get(first)


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

    @staticmethod
    def build_from_recipe(page: Page, recipe: dict[str, Any]) -> tuple[Locator, str]:
        """Rebuild a locator from a cached recipe."""
        t = recipe.get("t")
        if t == "role":
            loc = page.get_by_role(recipe["role"], name=recipe["name"])
            return loc, f"cached_role_{recipe['role']}"
        if t == "add_to_cart_ordinal":
            idx = int(recipe["index"])
            loc = page.locator("a,button").filter(has_text=_ADD_TO_CART_TEXT).nth(idx)
            return loc, f"add_to_cart_ordinal_{idx}"
        if t == "text":
            return page.get_by_text(recipe["text"], exact=False), "cached_text"
        if t == "label":
            return page.get_by_label(recipe["label"]), "cached_label"
        if t == "locator":
            return page.locator(recipe["selector"]), recipe.get("strategy", "cached_locator")
        raise ValueError(f"Unknown locator recipe type: {t!r}")

    async def resolve(
        self,
        page: Page,
        action: str,
        target: str,
        *,
        cache: SelectorCache | None = None,
        cache_key: str | None = None,
    ) -> tuple[Locator, str, dict[str, Any] | None]:
        normalized = (target or "").strip()
        if not normalized:
            raise ValueError("Empty target for locator resolution.")

        if cache is not None and cache_key:
            cached = cache.get(cache_key)
            if cached:
                loc, strat = self.build_from_recipe(page, cached)
                return loc, strat, cached

        recipe: dict[str, Any] | None = None

        if action in {"hover", "click", "assert_visible", "assert_text"}:
            lower = normalized.lower()
            name = _accessible_name_from_target(normalized)
            words = lower.split()
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
                rname = name or "sign in"
                recipe = {"t": "role", "role": "link", "name": rname}
                return (
                    page.get_by_role("link", name=rname),
                    "role_link_signin",
                    recipe,
                )
            if action in {"click", "hover"} and "add to cart" in lower:
                ord_idx = _leading_ordinal_index(lower)
                if ord_idx is not None:
                    recipe = {"t": "add_to_cart_ordinal", "index": ord_idx}
                    loc = page.locator("a,button").filter(has_text=_ADD_TO_CART_TEXT).nth(ord_idx)
                    return loc, "add_to_cart_ordinal", recipe
            if "link" in words:
                link_name = name or lower.replace("link", "").strip()
                recipe = {"t": "role", "role": "link", "name": link_name}
                return page.get_by_role("link", name=link_name), "role_link", recipe
            if "button" in lower:
                bname = name or lower
                recipe = {"t": "role", "role": "button", "name": bname}
                return page.get_by_role("button", name=bname), "role_button", recipe
            recipe = {"t": "text", "text": normalized}
            return page.get_by_text(normalized, exact=False), "text", recipe

        if action == "fill":
            lower = normalized.lower()
            if "email" in lower:
                sel = "input[type='email'], input[name*='email'], input[id*='email']"
                recipe = {"t": "locator", "selector": sel, "strategy": "input_email"}
                return page.locator(sel), "input_email", recipe
            if "password" in lower:
                sel = "input[type='password'], input[name*='password'], input[id*='password']"
                recipe = {"t": "locator", "selector": sel, "strategy": "input_password"}
                return page.locator(sel), "input_password", recipe
            recipe = {"t": "label", "label": normalized}
            return page.get_by_label(normalized), "label", recipe

        recipe = {"t": "text", "text": normalized}
        return page.get_by_text(normalized, exact=False), "text_fallback", recipe
