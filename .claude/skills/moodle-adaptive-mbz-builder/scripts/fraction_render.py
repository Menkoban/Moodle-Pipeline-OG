#!/usr/bin/env python3
r"""Render MathJax inline fractions \(\frac{a}{b}\) for the non-Moodle surfaces.

Moodle renders \(\frac{...}{...}\) natively via its MathJax filter. The HTML
preview and the PDF material can't run MathJax, so:
  * to_css   -> a real stacked fraction as an inline-styled <span> (browser)
  * to_slash -> "a/b" (ReportLab-safe, for the PDF material)

Scope: isolated \(\frac{a}{b}\) / \(\dfrac{a}{b}\) tokens with simple, non-nested
numerator/denominator. The surrounding equation stays plain text.
"""
import re

# \( ...\frac{NUM}{DEN}... \) with NUM/DEN free of nested braces
_FRAC_RX = re.compile(r"\\\(\s*\\d?frac\s*\{([^{}]*)\}\s*\{([^{}]*)\}\s*\\\)")

_CSS_TMPL = (
    '<span style="display:inline-block;vertical-align:middle;text-align:center;'
    'margin:0 .15em">'
    '<span style="display:block;border-bottom:1px solid;padding:0 .3em">{num}</span>'
    '<span style="display:block;padding:0 .3em">{den}</span></span>')


def to_slash(text):
    r"""Each \(\frac{a}{b}\) -> 'a/b' (ReportLab-safe)."""
    if not text:
        return text
    return _FRAC_RX.sub(
        lambda m: f"{m.group(1).strip()}/{m.group(2).strip()}", text)


def to_css(text):
    r"""Each \(\frac{a}{b}\) -> an inline-stacked <span> fraction."""
    if not text:
        return text
    return _FRAC_RX.sub(
        lambda m: _CSS_TMPL.format(num=m.group(1).strip(), den=m.group(2).strip()),
        text)
