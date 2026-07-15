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

    # Text colors by hierarchy.
    # PRIMARY: main content, SECONDARY: supporting copy,
    # TERTIARY/INACTIVE: helper text and non-selected nav items.
    TEXT_PRIMARY = "#111111"
    TEXT_SECONDARY = "#2A2A2A"
    TEXT_TERTIARY = "#303030"
    TEXT_INACTIVE = "#6E6E6E"

    # Component surfaces and accents used by cards, tracker, and preview fallback.
    CARD_BACKGROUND = "#E6EFF3"
    TRACKER_BACKGROUND = "#E9F8F2"
    TRACKER_TEXT = "#0D5F47"
    PROGRESS_TRACK = "#CFEADF"
    DIVIDER = "#DFE3E6"
    PREVIEW_FALLBACK_BACKGROUND = "#F2F4F5"