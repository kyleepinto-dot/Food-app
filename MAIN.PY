import flet as ft
import asyncio
from datetime import datetime, timezone
import urllib.error
import urllib.request

from pages.barcode_page import BarcodeScannerController, build_scan_shell
from pages.ai_food_profile_service import fetch_ai_food_profile, get_last_ai_food_profile_error
from pages.home_page import build_home_shell
from pages.meal_suggestion_page import build_meal_suggestion_shell
from pages.meal_suggestion_service import fetch_ai_meal_suggestions, rank_pantry_items
from pages.pantry_page import build_pantry_shell
from pages.me_page import build_me_shell
from pages.ai_image_service import build_ai_food_image_url, build_ai_meal_image_url
from pages.open_food_facts import fetch_food_product, fetch_food_product_by_name
from pages.product_info_page import build_product_info_shell
from pages.theme import ThemeColors


def main(page: ft.Page):
    """Configure app-level state, then render and switch between home/scan views.

    This entrypoint owns navigation and responsive measurements. Individual
    screen components live in page modules and are composed here with callbacks.
    """

    # Global page styling and initial window size.
    # The responsive layout code below still adapts when the window changes.
    page.title = "PantryIQ Connect"
    page.padding = 8
    page.bgcolor = ThemeColors.PAGE_BACKGROUND
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    page.vertical_alignment = ft.MainAxisAlignment.CENTER

    page.window.width = 430
    page.window.height = 900
    page.window.min_width = 390
    page.window.min_height = 760

    # Scanner controller owns camera lifecycle + barcode decoding flow.
    scanner_controller = BarcodeScannerController(page)
    # Track which screen should be displayed by render_current_view().
    # Dict wrapper is used so nested callbacks can mutate active state
    # without introducing nonlocal statements.
    view_state = {
        "current": "home",
        "product": None,
        "recent_products": [],
        "pantry_products": [],
        "ai_profile_cache": {},
        "meal_plan": {"status": "idle", "suggestions": [], "image_urls": [], "selected_index": None},
        "meal_request_version": 0,
        "meal_demo_number": 0,
        "meal_inventory": [],
        "meal_is_dummy": False,
        "profile": {
            "name": "Jamie Carter",
            "membership": "Community Member",
            "message": "Keeping food fresh, sharing what I can.",
            "scan_count": 0,
            "pantry_item_count": 0,
            "food_saved_lbs": 0.0,
            "notifications": "Expiry reminders and scan updates",
            "language": "English (US)",
            "privacy": "Manage shared data preferences",
            "support": "FAQs and contact options",
        },
    }

    def _ai_profile_cache_key(product_name: str, categories: str) -> str:
        return f"{product_name.strip().lower()}|{categories.strip().lower()}"

    def _set_profile_from_cache(product: dict, cached_profile: dict) -> None:
        product["ai_food_profile"] = dict(cached_profile)
        product["ai_food_profile_cached"] = True
        provider_mode = str(cached_profile.get("_provider") or "remote").lower()
        product["ai_food_profile_status"] = "ready_local" if provider_mode == "local" else "ready"

    def _recent_product_key(product: dict) -> str:
        code = str(product.get("code") or "").strip()
        if code:
            return f"code:{code}"
        name = str(product.get("product_name") or product.get("generic_name") or "unknown").strip().lower()
        return f"name:{name}"

    def remember_recent_product(product: dict) -> None:
        if not isinstance(product, dict):
            return

        existing = list(view_state.get("recent_products") or [])
        target_key = _recent_product_key(product)
        deduped = [item for item in existing if isinstance(item, dict) and _recent_product_key(item) != target_key]
        view_state["recent_products"] = [product] + deduped[:4]

    def record_successful_scan() -> None:
        """Update profile impact totals after a successful product lookup."""

        profile = view_state.get("profile")
        if not isinstance(profile, dict):
            return

        profile["scan_count"] = int(profile.get("scan_count") or 0) + 1
        # This is an app-level estimate until the pantry tracks actual weights.
        profile["food_saved_lbs"] = round(float(profile.get("food_saved_lbs") or 0) + 0.7, 1)

    def invalidate_meal_plan() -> None:
        """Discard a plan whenever pantry contents change."""

        view_state["meal_request_version"] = int(view_state.get("meal_request_version") or 0) + 1
        view_state["meal_plan"] = {"status": "idle", "suggestions": [], "image_urls": [], "selected_index": None}

    def build_meal_inventory() -> list[dict]:
        """Enrich pantry rows with their latest AI shelf-life profiles."""

        products_by_key = {
            _recent_product_key(product): product
            for product in view_state.get("recent_products") or []
            if isinstance(product, dict)
        }
        inventory: list[dict] = []
        for pantry_item in view_state.get("pantry_products") or []:
            if not isinstance(pantry_item, dict):
                continue
            enriched_item = dict(pantry_item)
            source_product = products_by_key.get(str(pantry_item.get("key") or ""), {})
            ai_profile = source_product.get("ai_food_profile") if isinstance(source_product, dict) else None
            if isinstance(ai_profile, dict):
                enriched_item["risk"] = str(ai_profile.get("risk") or enriched_item.get("risk") or "Medium Risk")
                enriched_item["shelf_life"] = str(
                    ai_profile.get("shelf_life") or enriched_item.get("shelf_life") or "5-10 days"
                )
            enriched_item.setdefault("risk", "Medium Risk")
            enriched_item.setdefault("shelf_life", "5-10 days")
            inventory.append(enriched_item)
        return inventory

    def build_dummy_meal_inventory(demo_number: int) -> list[dict]:
        """Return a rotating sample pantry so repeated clicks create new demos."""

        demo_sets = [
            [
                ("Baby spinach", "Produce", 1, "1 day", "High Risk"),
                ("Chicken breast", "Meat", 2, "2 days", "High Risk"),
                ("Greek yogurt", "Dairy", 1, "4 days", "Medium Risk"),
                ("Brown rice", "Whole grain", 1, "3 months", "Low Risk"),
            ],
            [
                ("Ripe tomatoes", "Produce", 4, "1 day", "High Risk"),
                ("Black beans", "Protein", 1, "5 days", "Medium Risk"),
                ("Corn tortillas", "Whole grain", 6, "8 days", "Medium Risk"),
                ("Frozen corn", "Vegetable", 1, "2 months", "Low Risk"),
            ],
            [
                ("Fresh mushrooms", "Produce", 1, "2 days", "High Risk"),
                ("Firm tofu", "Plant protein", 1, "4 days", "Medium Risk"),
                ("Broccoli", "Vegetable", 2, "6 days", "Medium Risk"),
                ("Whole-wheat noodles", "Whole grain", 1, "4 months", "Low Risk"),
            ],
        ]
        selected_set = demo_sets[(demo_number - 1) % len(demo_sets)]
        return [
            {
                "key": f"demo:{demo_number}:{index}",
                "name": name,
                "category": category,
                "quantity": quantity,
                "freshness": "Demo item",
                "storage": "Demo pantry",
                "added_at": datetime.now(timezone.utc).isoformat(),
                "shelf_life": shelf_life,
                "risk": risk,
            }
            for index, (name, category, quantity, shelf_life, risk) in enumerate(selected_set)
        ]

    def add_product_to_pantry(quantity_value=1) -> None:
        """Store the selected quantity of the current product, then open Pantry."""

        product = view_state.get("product")
        if not isinstance(product, dict):
            return

        try:
            quantity = max(1, int(str(quantity_value or "1").strip()))
        except (TypeError, ValueError):
            quantity = 1

        product_name = str(product.get("product_name") or product.get("generic_name") or "Unknown product").strip()
        product_key = _recent_product_key(product)
        pantry_products = list(view_state.get("pantry_products") or [])
        ai_profile_value = product.get("ai_food_profile")
        ai_profile = ai_profile_value if isinstance(ai_profile_value, dict) else {}

        for pantry_item in pantry_products:
            if isinstance(pantry_item, dict) and pantry_item.get("key") == product_key:
                pantry_item["quantity"] = int(pantry_item.get("quantity") or 1) + quantity
                if ai_profile:
                    pantry_item["risk"] = str(ai_profile.get("risk") or pantry_item.get("risk") or "Medium Risk")
                    pantry_item["shelf_life"] = str(
                        ai_profile.get("shelf_life") or pantry_item.get("shelf_life") or "5-10 days"
                    )
                break
        else:
            pantry_products.insert(
                0,
                {
                    "key": product_key,
                    "name": product_name,
                    "category": str(product.get("categories") or "Food item"),
                    "quantity": quantity,
                    "freshness": "Freshly added",
                    "storage": "Pantry",
                    "added_at": datetime.now(timezone.utc).isoformat(),
                    "risk": str(ai_profile.get("risk") or "Medium Risk"),
                    "shelf_life": str(ai_profile.get("shelf_life") or "5-10 days"),
                },
            )

        view_state["pantry_products"] = pantry_products
        invalidate_meal_plan()
        profile = view_state.get("profile")
        if isinstance(profile, dict):
            profile["pantry_item_count"] = sum(
                int(item.get("quantity") or 0) for item in pantry_products if isinstance(item, dict)
            )

        show_pantry()

    def change_pantry_quantity(product_key: str, amount: int) -> None:
        """Adjust an existing pantry quantity and remove rows that reach zero."""

        pantry_products = [item for item in view_state.get("pantry_products") or [] if isinstance(item, dict)]
        updated_products: list[dict] = []

        for pantry_item in pantry_products:
            if pantry_item.get("key") == product_key:
                pantry_item["quantity"] = int(pantry_item.get("quantity") or 0) + amount
                if int(pantry_item["quantity"]) <= 0:
                    continue
            updated_products.append(pantry_item)

        view_state["pantry_products"] = updated_products
        invalidate_meal_plan()
        profile = view_state.get("profile")
        if isinstance(profile, dict):
            profile["pantry_item_count"] = sum(int(item.get("quantity") or 0) for item in updated_products)

        if view_state.get("current") == "pantry":
            render_current_view()

    def warm_image_url(url: str) -> bool:
        """Best-effort warm-up so generated image is likely ready by display time."""

        request = urllib.request.Request(
            url,
            headers={
                "User-Agent": "PantryIQ-Connect/1.0 (github.com/kyleepinto-dot/Food-app)",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=12) as response:
                # Read a small chunk to trigger upstream generation without
                # blocking on full image download.
                response.read(256)
            return True
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, ValueError):
            return False

    async def hydrate_ai_image_async(product: dict, barcode_hint: str):
        """Attach AI image URL after initial product page render.

        This keeps first paint fast with Open Food Facts image while allowing
        AI image to appear once available.
        """

        if not isinstance(product, dict):
            return
        if product.get("ai_image_url"):
            return

        food_name = str(product.get("product_name") or product.get("generic_name") or "").strip()
        ai_image_url = build_ai_food_image_url(food_name=food_name, barcode=barcode_hint)
        if not isinstance(ai_image_url, str) or not ai_image_url:
            return

        is_warmed = await asyncio.to_thread(warm_image_url, ai_image_url)
        if not is_warmed:
            return

        product["ai_image_url"] = ai_image_url
        product["show_ai_first"] = True

        # Refresh only when the same product page is currently visible.
        if view_state.get("current") == "product" and view_state.get("product") is product:
            render_current_view()

    async def hydrate_ai_food_profile_async(product: dict):
        """Attach AI-derived risk/shelf/storage profile after initial render."""

        if not isinstance(product, dict):
            return
        if isinstance(product.get("ai_food_profile"), dict):
            return

        product_name = str(product.get("product_name") or product.get("generic_name") or "").strip()
        categories = str(product.get("categories") or "").strip()

        cache_key = _ai_profile_cache_key(product_name, categories)
        profile_cache = view_state.get("ai_profile_cache") or {}
        cached_profile = profile_cache.get(cache_key)
        if isinstance(cached_profile, dict):
            _set_profile_from_cache(product, cached_profile)
            scanner_controller.append_debug("ai_food_profile", "AI profile cache hit")
            if view_state.get("current") == "product" and view_state.get("product") is product:
                render_current_view()
            return

        ai_profile = await asyncio.to_thread(fetch_ai_food_profile, product_name, categories)
        if not isinstance(ai_profile, dict):
            product["ai_food_profile_cached"] = False
            product["ai_food_profile_status"] = "failed"
            reason = get_last_ai_food_profile_error() or "unknown reason"
            scanner_controller.append_debug("ai_food_profile", f"AI profile generation failed ({reason}); using fallback profile")
            if view_state.get("current") == "product" and view_state.get("product") is product:
                render_current_view()
            return

        product["ai_food_profile"] = ai_profile
        product["ai_food_profile_cached"] = False
        profile_cache[cache_key] = dict(ai_profile)
        # Bound memory while keeping a useful recent working set.
        if len(profile_cache) > 120:
            oldest_key = next(iter(profile_cache), None)
            if isinstance(oldest_key, str):
                profile_cache.pop(oldest_key, None)
        view_state["ai_profile_cache"] = profile_cache
        provider_mode = str(ai_profile.get("_provider") or "remote").lower()
        if provider_mode == "remote":
            product["ai_food_profile_status"] = "ready"
            scanner_controller.append_debug("ai_food_profile", "AI profile generation succeeded")
        else:
            product["ai_food_profile_status"] = "ready_local"
            reason = get_last_ai_food_profile_error() or "remote unavailable"
            scanner_controller.append_debug("ai_food_profile", f"Remote AI unavailable ({reason}); local smart profile used")

        # Refresh only when the same product page is currently visible.
        if view_state.get("current") == "product" and view_state.get("product") is product:
            render_current_view()

    async def hydrate_meal_plan_async(inventory: list[dict], request_version: int):
        """Generate several meals, then hydrate their AI photos concurrently."""

        suggestions = await asyncio.to_thread(fetch_ai_meal_suggestions, inventory)
        if request_version != view_state.get("meal_request_version"):
            return

        meal_plan = view_state.get("meal_plan") or {}
        meal_plan["suggestions"] = suggestions
        meal_plan["status"] = "ready" if suggestions else "idle"
        meal_plan["image_urls"] = []
        view_state["meal_plan"] = meal_plan
        if view_state.get("current") == "meals":
            render_current_view()

        if not suggestions:
            return
        image_urls = [
            build_ai_meal_image_url(
                str(suggestion.get("title") or "Healthy pantry meal"),
                [
                    str(ingredient.get("name") or "")
                    for ingredient in suggestion.get("ingredients") or []
                    if isinstance(ingredient, dict)
                ],
            ) or ""
            for suggestion in suggestions
        ]
        warm_results = await asyncio.gather(
            *(asyncio.to_thread(warm_image_url, url) if url else asyncio.sleep(0, result=False) for url in image_urls)
        )
        if request_version != view_state.get("meal_request_version"):
            return

        meal_plan["image_urls"] = [url if warmed else "" for url, warmed in zip(image_urls, warm_results)]
        if view_state.get("current") == "meals":
            render_current_view()

    def get_layout_metrics() -> dict:
        """Return responsive measurements consumed by both screen builders.

        The app uses three breakpoint buckets:
        - desktop: wide layouts with larger typography and camera region
        - tablet: medium shell balancing readability and available space
        - mobile: compact shell tuned for phone portrait defaults
        """

        # Build responsive measurements from the active viewport.
        # This keeps one layout system for phone, tablet, and desktop web.
        viewport_w = page.width or page.window.width or 430
        viewport_h = page.height or page.window.height or 900

        is_desktop = viewport_w >= 1000
        is_tablet = 700 <= viewport_w < 1000

        if is_desktop:
            shell_width = max(980, viewport_w - 16)
            shell_height = max(700, viewport_h - 16)
            title_size = 52
            subtitle_size = 20
            section_title_size = 44
            button_text_size = 26
            camera_height = max(420, shell_height - 250)
        elif is_tablet:
            shell_width = max(680, viewport_w - 20)
            shell_height = max(680, viewport_h - 20)
            title_size = 44
            subtitle_size = 16
            section_title_size = 40
            button_text_size = 24
            camera_height = max(420, shell_height - 250)
        else:
            shell_width = min(390, viewport_w - 24)
            shell_height = min(760, max(660, viewport_h - 24))
            title_size = 37
            subtitle_size = 14
            section_title_size = 34
            button_text_size = 22
            camera_height = 520

        return {
            "is_desktop": is_desktop,
            "is_tablet": is_tablet,
            "shell_width": shell_width,
            "shell_height": shell_height,
            "title_size": title_size,
            "subtitle_size": subtitle_size,
            "section_title_size": section_title_size,
            "button_text_size": button_text_size,
            "camera_height": camera_height,
        }

    def render_current_view():
        """Render only the active screen and clean up camera when needed.

        Centralizing screen switches in one renderer avoids duplicate view
        cleanup logic and makes lifecycle behavior easier to reason about.
        """

        # Centralized rendering keeps navigation predictable and avoids
        # stale controls left on the page.
        if view_state["current"] == "scan":
            page.clean()
            page.add(build_scan_view())
            page.update()
            return

        if view_state["current"] == "product":
            try:
                page.clean()
                page.add(build_product_view())
                page.update()
            except Exception as exc:
                scanner_controller.append_debug("render_product_view_error", f"{type(exc).__name__}: {exc}")
                view_state["current"] = "scan"
                page.clean()
                page.add(build_scan_view())
                page.update()
            return

        if view_state["current"] == "pantry":
            scanner_controller.stop_camera()
            page.clean()
            page.add(build_pantry_view())
            page.update()
            return

        if view_state["current"] == "meals":
            scanner_controller.stop_camera()
            page.clean()
            page.add(build_meal_plan_view())
            page.update()
            return

        if view_state["current"] == "me":
            scanner_controller.stop_camera()
            page.clean()
            page.add(build_me_view())
            page.update()
            return

        # Leaving scan mode should always stop camera access before replacing
        # controls so hardware and stream resources are released promptly.
        scanner_controller.stop_camera()
        page.clean()
        page.add(build_home_view())
        page.update()

    def show_home(_=None):
        """Navigate to the home screen from button/tap handlers."""

        # Small wrapper so page controls can call navigation directly.
        view_state["current"] = "home"
        view_state["product"] = None
        render_current_view()

    def show_scan(_=None):
        """Navigate to the scanner screen from button/tap handlers."""

        # Small wrapper so page controls can call navigation directly.
        view_state["current"] = "scan"
        render_current_view()

    def show_pantry(_=None):
        """Navigate to the pantry screen from button/tap handlers."""

        view_state["current"] = "pantry"
        render_current_view()

    def show_meal_planner(_=None):
        """Open the planner with the user's current pantry inventory."""

        invalidate_meal_plan()
        inventory = build_meal_inventory()
        view_state["meal_inventory"] = inventory
        view_state["meal_is_dummy"] = False
        start_meal_request(inventory)

    def show_dummy_meal_planner(_=None):
        """Open a new rotating dummy pantry page on every button click."""

        invalidate_meal_plan()
        demo_number = int(view_state.get("meal_demo_number") or 0) + 1
        view_state["meal_demo_number"] = demo_number
        inventory = build_dummy_meal_inventory(demo_number)
        view_state["meal_inventory"] = inventory
        view_state["meal_is_dummy"] = True
        start_meal_request(inventory)

    def start_meal_request(inventory: list[dict]) -> None:
        """Render a planner inventory and asynchronously request its meals."""

        meal_plan = view_state.get("meal_plan") or {}
        view_state["current"] = "meals"
        if not inventory:
            render_current_view()
            return
        request_version = int(view_state.get("meal_request_version") or 0) + 1
        view_state["meal_request_version"] = request_version
        meal_plan["status"] = "loading"
        view_state["meal_plan"] = meal_plan
        render_current_view()
        page.run_task(hydrate_meal_plan_async, inventory, request_version)

    def refresh_meal_plan(_=None):
        """Request a new group of meals using the currently displayed inventory."""

        inventory = [item for item in view_state.get("meal_inventory") or [] if isinstance(item, dict)]
        invalidate_meal_plan()
        start_meal_request(inventory)

    def select_meal_suggestion(index: int) -> None:
        """Open complete ingredients and directions for one suggested dish."""

        meal_plan = view_state.get("meal_plan") or {}
        suggestions = meal_plan.get("suggestions") or []
        if 0 <= index < len(suggestions):
            meal_plan["selected_index"] = index
            view_state["meal_plan"] = meal_plan
            render_current_view()

    def show_meal_suggestion_list(_=None) -> None:
        """Return from recipe details to the meal name list."""

        meal_plan = view_state.get("meal_plan") or {}
        meal_plan["selected_index"] = None
        view_state["meal_plan"] = meal_plan
        render_current_view()

    def show_me(_=None):
        """Navigate to the profile screen from button/tap handlers."""

        view_state["current"] = "me"
        render_current_view()

    def show_recent_product(product: dict | None = None):
        # Reopen a previously scanned food details card from quick access.
        target_product = product
        if target_product is None:
            recent_products = view_state.get("recent_products") or []
            target_product = recent_products[0] if recent_products else None

        if target_product is None:
            return
        view_state["product"] = target_product
        view_state["current"] = "product"
        render_current_view()

    def clear_recent_history(_=None):
        # Clear recent scan shortcuts and refresh scan view if visible.
        view_state["recent_products"] = []
        if view_state.get("current") == "scan":
            render_current_view()

    async def on_barcode_detected(barcode: str) -> bool:
        # Query Open Food Facts off-thread so network calls do not block UI.
        scanner_controller.append_debug("open_food_facts_lookup", f"Fetching product for barcode {barcode}")
        product = await asyncio.to_thread(fetch_food_product, barcode)
        if product is None:
            scanner_controller.append_debug("open_food_facts_lookup", "No food product returned from service")
            return False

        try:
            scanner_controller.append_debug("navigation", "Switching from scan view to product view")
            scanner_controller.stop_camera()
            view_state["product"] = product
            remember_recent_product(product)
            record_successful_scan()
            product["ai_food_profile_status"] = "pending"
            view_state["current"] = "product"
            render_current_view()
            page.run_task(hydrate_ai_image_async, product, barcode)
            page.run_task(hydrate_ai_food_profile_async, product)
            scanner_controller.append_debug("navigation", "Product view rendered successfully")
            return True
        except Exception as exc:
            # Keep users on scan page when product view fails to render.
            scanner_controller.append_debug("navigation_error", f"{type(exc).__name__}: {exc}")
            view_state["current"] = "scan"
            render_current_view()
            if scanner_controller.status_text is not None:
                scanner_controller.status_text.value = "Could not open product details"
            if scanner_controller.result_text is not None:
                scanner_controller.result_text.value = f"Please scan again ({exc})"
            page.update()
            return False

    async def on_product_name_detected(product_name_query: str) -> bool:
        # Search Open Food Facts by typed product name when barcode is unknown.
        scanner_controller.append_debug("open_food_facts_name_lookup", f"Searching product for '{product_name_query}'")
        product = await asyncio.to_thread(fetch_food_product_by_name, product_name_query)
        if product is None:
            scanner_controller.append_debug("open_food_facts_name_lookup", "No matching food product returned")
            return False

        try:
            scanner_controller.append_debug("navigation", "Switching from scan view to product view (manual name)")
            scanner_controller.stop_camera()
            view_state["product"] = product
            remember_recent_product(product)
            record_successful_scan()
            product["ai_food_profile_status"] = "pending"
            view_state["current"] = "product"
            render_current_view()
            page.run_task(hydrate_ai_image_async, product, str(product.get("code") or ""))
            page.run_task(hydrate_ai_food_profile_async, product)
            scanner_controller.append_debug("navigation", "Product view rendered successfully (manual name)")
            return True
        except Exception as exc:
            scanner_controller.append_debug("navigation_error", f"{type(exc).__name__}: {exc}")
            view_state["current"] = "scan"
            render_current_view()
            if scanner_controller.status_text is not None:
                scanner_controller.status_text.value = "Could not open product details"
            if scanner_controller.result_text is not None:
                scanner_controller.result_text.value = f"Please try another product name ({exc})"
            page.update()
            return False

    def build_home_view() -> ft.Container:
        """Build the home shell with current metrics and scan navigation."""

        # Home screen UI is implemented in pages/home_page.py.
        metrics = get_layout_metrics()
        return build_home_shell(
            metrics=metrics,
            on_scan_click=show_scan,
            on_pantry_click=show_pantry,
            on_me_click=show_me,
            recent_products=view_state.get("recent_products") or [],
            on_recent_product_click=show_recent_product,
            profile=view_state.get("profile") or {},
        )

    def build_scan_view() -> ft.Container:
        """Build the scan shell and wire controller-driven async callbacks."""

        # Barcode screen UI is implemented in pages/barcode_page.py.
        # This function injects callbacks and stores returned controls.
        metrics = get_layout_metrics()
        controls = build_scan_shell(
            metrics=metrics,
            camera_is_supported=scanner_controller.camera_supported_on_platform(),
            recent_products=view_state.get("recent_products") or [],
            on_back_click=show_home,
            on_home_click=show_home,
            on_pantry_click=show_pantry,
            on_me_click=show_me,
            on_recent_product_click=show_recent_product,
            on_clear_recent_click=clear_recent_history,
            # Async camera APIs are dispatched via page.run_task() so UI
            # remains responsive while camera operations are in-flight.
            on_start_camera=lambda e: page.run_task(scanner_controller.start_camera, e),
            on_stop_camera=lambda _: (scanner_controller.stop_camera(), page.update()),
            on_take_photo=lambda e: page.run_task(scanner_controller.capture_photo_and_scan, e),
            on_manual_search=lambda e: page.run_task(scanner_controller.search_manual_barcode, e),
        )

        scanner_controller.bind_controls(controls)
        scanner_controller.set_barcode_detected_handler(on_barcode_detected)
        scanner_controller.set_product_name_detected_handler(on_product_name_detected)

        return controls["container"]

    def build_product_view() -> ft.Container:
        # Product details screen renders data fetched from Open Food Facts.
        metrics = get_layout_metrics()
        product = view_state["product"] or {}
        return build_product_info_shell(
            metrics=metrics,
            product=product,
            on_back_to_scan_click=show_scan,
            on_home_click=show_home,
            on_scan_click=show_scan,
            on_pantry_click=show_pantry,
            on_me_click=show_me,
            on_add_to_pantry=add_product_to_pantry,
        )

    def build_pantry_view() -> ft.Container:
        # Pantry screen mirrors the app visual language and bottom navigation.
        metrics = get_layout_metrics()
        return build_pantry_shell(
            metrics=metrics,
            on_home_click=show_home,
            on_scan_click=show_scan,
            on_me_click=show_me,
            on_meal_planner_click=show_meal_planner,
            on_dummy_meal_planner_click=show_dummy_meal_planner,
            pantry_products=view_state.get("pantry_products") or [],
            on_quantity_change=change_pantry_quantity,
        )

    def build_meal_plan_view() -> ft.Container:
        # Meal planning stays linked to Pantry while using a dedicated screen.
        metrics = get_layout_metrics()
        inventory = [item for item in view_state.get("meal_inventory") or [] if isinstance(item, dict)]
        return build_meal_suggestion_shell(
            metrics=metrics,
            on_back_click=show_pantry,
            on_home_click=show_home,
            on_scan_click=show_scan,
            on_pantry_click=show_pantry,
            on_me_click=show_me,
            ranked_items=rank_pantry_items(inventory),
            meal_state=view_state.get("meal_plan") or {},
            demo_number=int(view_state.get("meal_demo_number") or 1) if view_state.get("meal_is_dummy") else 0,
            on_meal_click=select_meal_suggestion,
            on_back_to_list_click=show_meal_suggestion_list,
            on_refresh_click=refresh_meal_plan,
        )

    def build_me_view() -> ft.Container:
        # Account/profile screen reuses shared shell styling and nav.
        metrics = get_layout_metrics()
        return build_me_shell(
            metrics=metrics,
            on_home_click=show_home,
            on_scan_click=show_scan,
            on_pantry_click=show_pantry,
            profile=view_state.get("profile") or {},
        )

    # Re-render on resize so responsive metrics are applied immediately.
    page.on_resize = lambda _: render_current_view()
    # Stop camera when the app closes to release camera resources cleanly.
    page.on_close = lambda _: scanner_controller.stop_camera()

    def handle_page_error(e):
        scanner_controller.append_debug("page_error", str(getattr(e, "data", e)))

    page.on_error = handle_page_error
    show_home()


ft.run(main)
