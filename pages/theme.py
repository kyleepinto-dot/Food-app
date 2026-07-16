"""Centralized color tokens used across PantryIQ Connect UI."""


class ThemeColors:
    # App-level surfaces.
    # PAGE_BACKGROUND is outside the rounded shell; SHELL_* styles the card-like
    # app container to stand out from the page backdrop.
    PAGE_BACKGROUND = "#EEF1F3"
    SHELL_BACKGROUND = "#FFFFFF"
    SHELL_SHADOW = "#22000000"

    # Brand and action colors.
    # Keep BRAND_PRIMARY high-contrast against both light surfaces and
    # BRAND_ON_PRIMARY button text for accessibility.
    BRAND_PRIMARY = "#1AA87C"
    BRAND_ON_PRIMARY = "#FFFFFF"

    # Softer yellow accent family shared across pages.
    # These values intentionally avoid neon tones to keep contrast comfortable.
    ACCENT_YELLOW = "#E7C85A"
    ACCENT_YELLOW_SOFT = "#F4E8BB"
    ACCENT_YELLOW_SUBTLE = "#FBF5DF"

    # Green-forward surfaces for food facts pages.
    GREEN_SURFACE = "#E8F4EC"
    GREEN_SURFACE_SOFT = "#D9EEDD"
    GREEN_TEXT = "#1F5A36"

    # Text colors by hierarchy.
    # PRIMARY: main content, SECONDARY: supporting copy,
    # TERTIARY/INACTIVE: helper text and non-selected nav items.
    TEXT_PRIMARY = "#111111"
    TEXT_SECONDARY = "#2A2A2A"
    TEXT_TERTIARY = "#303030"
    TEXT_INACTIVE = "#6E6E6E"

    # Component surfaces and accents used by cards, tracker, and preview fallback.
    CARD_BACKGROUND = "#FAF1CC"
    TRACKER_BACKGROUND = "#F7EDC7"
    TRACKER_TEXT = "#4A3D12"
    PROGRESS_TRACK = "#EADDA6"
    DIVIDER = "#DFE3E6"
    PREVIEW_FALLBACK_BACKGROUND = "#F2F4F5"