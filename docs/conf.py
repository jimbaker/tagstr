import os
import sys

sys.path.insert(0, os.path.abspath("."))

project = "tagstr"
copyright = "2023, Jim Baker"
author = "Jim Baker"
release = "0.0.1"
extensions = [
    "sphinx.ext.doctest",
]
templates_path = ["_templates"]
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]
html_theme = "sphinx_book_theme"
html_static_path = ["_static"]
