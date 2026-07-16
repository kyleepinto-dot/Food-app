import flet as ft
import asyncio

from pages.barcode_page import BarcodeScannerController, build_scan_shell
from pages.home_page import build_home_shell
from pages.ai_image_service import build_ai_food_image_url
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
    page.padding = 20
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
    view_state = {"current": "home", "product": None, "recent_product": None}

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
            shell_width = min(980, viewport_w - 90)
            shell_height = min(860, max(700, viewport_h - 60))
            title_size = 52
            subtitle_size = 20
            section_title_size = 44
            button_text_size = 26
            camera_height = max(420, shell_height - 250)
        elif is_tablet:
            shell_width = min(700, viewport_w - 60)
            shell_height = min(820, max(680, viewport_h - 50))
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

    def show_recent_product(_=None):
        # Reopen last scanned food details from the scan page quick-access card.
        if view_state["recent_product"] is None:
            return
        view_state["product"] = view_state["recent_product"]
        view_state["current"] = "product"
        render_current_view()

    async def on_barcode_detected(barcode: str) -> bool:
        # Query Open Food Facts off-thread so network calls do not block UI.
        scanner_controller.append_debug("open_food_facts_lookup", f"Fetching product for barcode {barcode}")
        product = await asyncio.to_thread(fetch_food_product, barcode)
        if product is None:
            scanner_controller.append_debug("open_food_facts_lookup", "No food product returned from service")
            return False

        # Use product name from Open Food Facts as the AI prompt subject.
        # Barcode-derived seed keeps generated images stable for each product.
        food_name = str(product.get("product_name") or product.get("generic_name") or "").strip()
        ai_image_url = build_ai_food_image_url(food_name=food_name, barcode=barcode)
        if isinstance(ai_image_url, str) and ai_image_url:
            product["ai_image_url"] = ai_image_url

        try:
            scanner_controller.append_debug("navigation", "Switching from scan view to product view")
            scanner_controller.stop_camera()
            view_state["product"] = product
            view_state["recent_product"] = product
            view_state["current"] = "product"
            render_current_view()
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

        code_from_match = str(product.get("code") or "").strip()
        prompt_name = str(product.get("product_name") or product.get("generic_name") or product_name_query).strip()
        ai_image_url = build_ai_food_image_url(food_name=prompt_name, barcode=code_from_match)
        if isinstance(ai_image_url, str) and ai_image_url:
            product["ai_image_url"] = ai_image_url

        try:
            scanner_controller.append_debug("navigation", "Switching from scan view to product view (manual name)")
            scanner_controller.stop_camera()
            view_state["product"] = product
            view_state["recent_product"] = product
            view_state["current"] = "product"
            render_current_view()
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
        return build_home_shell(metrics=metrics, on_scan_click=show_scan)

    def build_scan_view() -> ft.Container:
        """Build the scan shell and wire controller-driven async callbacks."""

        # Barcode screen UI is implemented in pages/barcode_page.py.
        # This function injects callbacks and stores returned controls.
        metrics = get_layout_metrics()
        controls = build_scan_shell(
            metrics=metrics,
            camera_is_supported=scanner_controller.camera_supported_on_platform(),
            recent_product=view_state["recent_product"],
            on_back_click=show_home,
            on_recent_product_click=show_recent_product,
            # Async camera APIs are dispatched via page.run_task() so UI
            # remains responsive while camera operations are in-flight.
            on_start_camera=lambda e: page.run_task(scanner_controller.start_camera, e),
            on_stop_camera=lambda e: (scanner_controller.stop_camera(), page.update()),
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
