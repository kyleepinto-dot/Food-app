import unittest

from pages.theme import ThemeColors


def _relative_luminance(hex_color: str) -> float:
    channels = [int(hex_color[index:index + 2], 16) / 255 for index in (1, 3, 5)]
    linear = [
        channel / 12.92
        if channel <= 0.04045
        else ((channel + 0.055) / 1.055) ** 2.4
        for channel in channels
    ]
    return (0.2126 * linear[0]) + (0.7152 * linear[1]) + (0.0722 * linear[2])


def _contrast_ratio(foreground: str, background: str) -> float:
    lighter = max(_relative_luminance(foreground), _relative_luminance(background))
    darker = min(_relative_luminance(foreground), _relative_luminance(background))
    return (lighter + 0.05) / (darker + 0.05)


class ThemeContrastTests(unittest.TestCase):
    def test_shared_text_tokens_meet_normal_text_contrast(self):
        pairs = [
            (ThemeColors.TEXT_PRIMARY, ThemeColors.SHELL_BACKGROUND),
            (ThemeColors.TEXT_SECONDARY, ThemeColors.SHELL_BACKGROUND),
            (ThemeColors.TEXT_PLACEHOLDER, ThemeColors.SHELL_BACKGROUND),
            (ThemeColors.TEXT_ON_DARK_SECONDARY, ThemeColors.GREEN_TEXT),
        ]

        for foreground, background in pairs:
            with self.subTest(foreground=foreground, background=background):
                self.assertGreaterEqual(_contrast_ratio(foreground, background), 4.5)
