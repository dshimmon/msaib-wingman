"""Regression coverage for Atlas's theme-independent contrast contract."""

import re
import unittest

from products.atlas.ui.styles import ATLAS_STYLES


def _rgb(hex_color):
    value = hex_color.removeprefix("#")
    return tuple(int(value[index : index + 2], 16) for index in (0, 2, 4))


def _relative_luminance(rgb):
    channels = []
    for value in rgb:
        normalized = value / 255
        channels.append(
            normalized / 12.92
            if normalized <= 0.04045
            else ((normalized + 0.055) / 1.055) ** 2.4
        )
    return 0.2126 * channels[0] + 0.7152 * channels[1] + 0.0722 * channels[2]


def _contrast(first, second):
    lighter, darker = sorted(
        (_relative_luminance(_rgb(first)), _relative_luminance(_rgb(second))),
        reverse=True,
    )
    return (lighter + 0.05) / (darker + 0.05)


class AtlasStyleContractTests(unittest.TestCase):
    def test_dark_theme_alert_regression_has_explicit_foreground(self):
        self.assertIn('[data-testid="stAlert"] p', ATLAS_STYLES)
        self.assertIn(
            '[data-testid="stAlert"] [data-testid="stMarkdownContainer"]',
            ATLAS_STYLES,
        )
        self.assertRegex(
            ATLAS_STYLES,
            re.compile(
                r'\[data-testid="stAlert"\] p,[\s\S]+?'
                r"color: var\(--atlas-ink\) !important;"
            ),
        )

    def test_light_surfaces_pin_text_inputs_and_chat_foregrounds(self):
        for selector in (
            '[data-testid="stWidgetLabel"] p',
            '[data-testid="stCaptionContainer"]',
            '[data-testid="stMetricValue"]',
            '[data-testid="stTextInput"] input',
            '[data-testid="stTextArea"] textarea',
            '[data-testid="stChatInputTextArea"]',
            '[data-testid="stChatMessage"] p',
        ):
            self.assertIn(selector, ATLAS_STYLES)
        self.assertIn(
            "-webkit-text-fill-color: var(--atlas-ink) !important;", ATLAS_STYLES
        )

    def test_controls_pin_nested_text_disabled_and_focus_states(self):
        self.assertIn('[data-testid^="stBaseButton-"] *', ATLAS_STYLES)
        self.assertIn('[data-testid="stBaseButton-primary"] *', ATLAS_STYLES)
        self.assertIn('[data-testid="stBaseButton-primary"] p', ATLAS_STYLES)
        self.assertIn('[data-testid="stBaseButton-primary"]:disabled', ATLAS_STYLES)
        self.assertIn("opacity: 1 !important;", ATLAS_STYLES)
        self.assertIn("outline: 3px solid #ffffff !important;", ATLAS_STYLES)
        self.assertIn(
            "box-shadow: 0 0 0 6px var(--atlas-focus) !important;", ATLAS_STYLES
        )

    def test_intentional_white_text_overrides_follow_general_foregrounds(self):
        general = ATLAS_STYLES.index('[data-testid="stAlert"] p')
        brand = ATLAS_STYLES.index(".atlas-brand,\n.atlas-brand *")
        primary = ATLAS_STYLES.index('[data-testid="stBaseButton-primary"]')
        self.assertGreater(brand, general)
        self.assertGreater(primary, general)
        self.assertIn("color: #ffffff !important;", ATLAS_STYLES[brand:])

    def test_normal_and_control_text_tokens_meet_wcag_aa_on_light_surfaces(self):
        for foreground, background in (
            ("#16253a", "#ffffff"),
            ("#526278", "#ffffff"),
            ("#0b5b95", "#ffffff"),
            ("#ffffff", "#12345b"),
            ("#ffffff", "#667085"),
        ):
            with self.subTest(foreground=foreground, background=background):
                self.assertGreaterEqual(_contrast(foreground, background), 4.5)

    def test_contract_uses_stable_selectors_without_generated_classes(self):
        self.assertIn('[data-testid="stAppViewContainer"]', ATLAS_STYLES)
        self.assertNotRegex(ATLAS_STYLES, r"\.css-[0-9A-Za-z_-]+")
        self.assertNotRegex(ATLAS_STYLES, r"\.st-emotion-cache-[0-9A-Za-z_-]+")


if __name__ == "__main__":
    unittest.main()
