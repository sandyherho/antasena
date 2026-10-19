"""Sphinx configuration for the antasena documentation (Read the Docs)."""
import os
import sys

sys.path.insert(0, os.path.abspath("../src"))
import antasena  # noqa: E402

project = "antasena"
author = ("Sandy H. S. Herho, Faruq Khadami, Iwan P. Anwar, Karina A. Sujatmiko, "
          "Sito F. Biosa, Alfita P. Handayani, Dasapta E. Irawan")
copyright = "2026, Bandung Institute of Technology"
version = release = antasena.__version__

extensions = [
    "myst_parser",
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
    "sphinx.ext.viewcode",
    "sphinx.ext.mathjax",
    "sphinx_copybutton",
    "sphinx_design",
]

myst_enable_extensions = ["dollarmath", "amsmath", "colon_fence", "deflist", "attrs_inline"]
myst_heading_anchors = 3
source_suffix = {".md": "markdown", ".rst": "restructuredtext"}
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

autodoc_member_order = "bysource"
autodoc_typehints = "description"
autodoc_mock_imports = ["tkinter"]
autodoc_default_options = {"members": True, "undoc-members": False, "show-inheritance": False}
copybutton_prompt_text = r"\$ |>>> "
copybutton_prompt_is_regexp = True

html_theme = "furo"
html_title = f"antasena {release}"
html_static_path = ["_static"]
html_css_files = ["custom.css"]
html_logo = "_static/logo.svg"
html_favicon = "_static/logo.svg"
html_show_sphinx = False
html_theme_options = {
    "sidebar_hide_name": False,
    "navigation_with_keys": True,
    "source_repository": "https://github.com/sandyherho/antasena/",
    "source_branch": "main",
    "source_directory": "docs/",
    "light_css_variables": {
        "color-brand-primary": "#12385a",
        "color-brand-content": "#1f6f8b",
        "color-admonition-background": "#e8f4f6",
        "font-stack": "Inter, 'Segoe UI', 'Helvetica Neue', Arial, sans-serif",
    },
    "dark_css_variables": {
        "color-brand-primary": "#7cc8d2",
        "color-brand-content": "#4fb3bf",
    },
}
