#!/usr/bin/env python3
#
# Trio documentation build configuration file, created by
# sphinx-quickstart on Sat Jan 21 19:11:14 2017.
#
# This file is execfile()d with the current directory set to its
# containing dir.
#
# Note that not all possible configuration values are present in this
# autogenerated file.
#
# All configuration values have a default; values that are commented out
# serve to show the default.

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#
from __future__ import annotations

import collections.abc
import glob
import os
import sys
from pathlib import Path
from typing import TYPE_CHECKING, cast

from sphinx.util.inventory import _InventoryItem
from sphinx.util.logging import getLogger

if TYPE_CHECKING:
    from sphinx.application import Sphinx
    from sphinx.util.typing import Inventory

# For our local_customization module
sys.path.insert(0, os.path.abspath("."))

# Enable reloading with `typing.TYPE_CHECKING` being True
os.environ["SPHINX_AUTODOC_RELOAD_MODULES"] = "1"

# Handle writing newsfragments into the history file.
# We want to keep files unchanged when testing locally.
# So immediately revert the contents after running towncrier,
# then substitute when Sphinx wants to read it in.
history_file = Path("history.rst")

history_new: str | None
if glob.glob("../../newsfragments/*.*.rst"):
    print("-- Found newsfragments; running towncrier --", flush=True)
    history_orig = history_file.read_bytes()
    import subprocess

    # In case changes were staged, preserve indexed version.
    # This grabs the hash of the current staged version.
    history_staged = subprocess.run(
        ["git", "rev-parse", "--verify", ":docs/source/history.rst"],
        check=True,
        cwd="../..",
        stdout=subprocess.PIPE,
        encoding="ascii",
    ).stdout.strip()
    try:
        subprocess.run(
            ["towncrier", "--keep", "--date", "not released yet"],
            cwd="../..",
            check=True,
        )
        history_new = history_file.read_text("utf8")
    finally:
        # Make sure this reverts even if a failure occurred.
        # Restore whatever was staged.
        print(f"Restoring history.rst = {history_staged}")
        subprocess.run(
            [
                "git",
                "update-index",
                "--cacheinfo",
                f"100644,{history_staged},docs/source/history.rst",
            ],
            cwd="../..",
            check=False,
        )
        # And restore the working copy.
        history_file.write_bytes(history_orig)
    del history_orig  # We don't need this any more.
else:
    # Leave it as is.
    history_new = None


def on_read_source(app: Sphinx, docname: str, content: list[str]) -> None:
    """Substitute the modified history file."""
    if docname == "history" and history_new is not None:
        # This is a 1-item list with the file contents.
        content[0] = history_new


# Sphinx is very finicky, and somewhat buggy, so we have several different
# methods to help it resolve links.
# 1. The ones that are not possible to fix are added to `nitpick_ignore`
# 2. some can be resolved with a simple alias in `autodoc_type_aliases`,
#    even if that is primarily meant for TypeAliases
# 3. autodoc_process_signature is hooked up to an event, and we use it for
#    whole-sale replacing types in signatures where internal details are not
#    relevant or hard to read.
# 4. add_intersphinx manually modifies the intersphinx mappings after
#    objects.inv has been parsed, to resolve bugs and version differences
#    that causes some objects to be looked up incorrectly.
# 5. docs/source/typevars.py handles redirecting `typing_extensions` objects to `typing`, and linking `TypeVar`s to `typing.TypeVar` instead of sphinx wanting to link them to their individual definitions.
# It's possible there's better methods for resolving some of the above
# problems, but this works for now:tm:

# Warn about all references to unknown targets
nitpicky = True
# Except for these ones, which we expect to point to unknown targets:
nitpick_ignore = [
    ("py:class", "CapacityLimiter-like object"),
    ("py:class", "bytes-like"),
    # Was removed but still shows up in changelog
    ("py:class", "trio.lowlevel.RunLocal"),
    # trio.abc is documented at random places scattered throughout the docs
    ("py:mod", "trio.abc"),
    ("py:exc", "Anything else"),
    ("py:class", "async function"),
    ("py:class", "sync function"),
    # these do not have documentation on python.org
    # nor entries in objects.inv
    ("py:class", "socket.AddressFamily"),
    ("py:class", "socket.SocketKind"),
]
autodoc_inherit_docstrings = False
default_role = "obj"


# A dictionary for users defined type aliases that maps a type name to the full-qualified object name. It is used to keep type aliases not evaluated in the document.
# https://www.sphinx-doc.org/en/master/usage/extensions/autodoc.html#confval-autodoc_type_aliases
# but it can also be used to help resolve various linking problems
autodoc_type_aliases = {
    # SSLListener.accept's return type is seen as trio._ssl.SSLStream
    "SSLStream": "trio.SSLStream",
}


# https://www.sphinx-doc.org/en/master/usage/extensions/autodoc.html#event-autodoc-process-signature
def autodoc_process_signature(
    app: Sphinx,
    what: str,
    name: str,
    obj: object,
    options: object,
    signature: str,
    return_annotation: str,
) -> tuple[str, str]:
    """Modify found signatures to fix various issues."""
    if signature is not None:
        signature = signature.replace("~_contextvars.Context", "~contextvars.Context")
        if name == "trio.lowlevel.RunVar":  # Typevar is not useful here.
            signature = signature.replace(": ~trio._core._local.T", "")
        if "_NoValue" in signature:
            # Strip the type from the union, make it look like = ...
            signature = signature.replace(" | type[trio._core._local._NoValue]", "")
            signature = signature.replace("<class 'trio._core._local._NoValue'>", "...")
        if "DTLS" in name:
            signature = signature.replace("SSL.Context", "OpenSSL.SSL.Context")
        # Don't specify PathLike[str] | PathLike[bytes], this is just for humans.
        signature = signature.replace("StrOrBytesPath", "str | bytes | os.PathLike")

    return signature, return_annotation


# currently undocumented things
logger = getLogger("trio")
UNDOCUMENTED = {
    "trio.CancelScope.relative_deadline",
    "trio.MemorySendChannel",
    "trio.MemoryReceiveChannel",
    "trio.MemoryChannelStatistics",
    "trio.SocketStream.aclose",
    "trio.SocketStream.receive_some",
    "trio.SocketStream.send_all",
    "trio.SocketStream.send_eof",
    "trio.SocketStream.wait_send_all_might_not_block",
    "trio._subprocess.HasFileno.fileno",
    "trio.lowlevel.ParkingLot.broken_by",
}


def autodoc_process_docstring(
    app: Sphinx,
    what: str,
    name: str,
    obj: object,
    options: object,
    lines: list[str],
) -> None:
    if not lines:
        # TODO: document these and remove them from here
        if name in UNDOCUMENTED:
            return

        logger.warning(f"{name} has no docstring")
    else:
        if name in UNDOCUMENTED:
            logger.warning("outdated list of undocumented things")


def setup(app: Sphinx) -> None:
    # Add our custom styling to make our documentation better!
    app.add_css_file("styles.css")
    app.connect("autodoc-process-signature", autodoc_process_signature)
    app.connect("autodoc-process-docstring", autodoc_process_docstring)

    # After Intersphinx runs, add additional mappings.
    app.connect("builder-inited", add_intersphinx, priority=1000)
    app.connect("source-read", on_read_source)


html_context = {"current_version": os.environ.get("READTHEDOCS_VERSION_NAME")}

# -- General configuration ------------------------------------------------

# If your documentation needs a minimal Sphinx version, state it here.
#
# needs_sphinx = '1.0'

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.intersphinx",
    "sphinx.ext.coverage",
    "sphinx.ext.napoleon",
    "sphinxcontrib_trio",
    "sphinxcontrib.jquery",
    "hoverxref.extension",
    "sphinx_codeautolink",
    "local_customization",
    "typevars",
]

intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
    "outcome": ("https://outcome.readthedocs.io/en/latest/", None),
    "pyopenssl": ("https://www.pyopenssl.org/en/stable/", None),
    "sniffio": ("https://sniffio.readthedocs.io/en/latest/", None),
    "trio-util": ("https://trio-util.readthedocs.io/en/latest/", None),
    "flake8-async": ("https://flake8-async.readthedocs.io/en/latest/", None),
}

# See https://sphinx-hoverxref.readthedocs.io/en/latest/configuration.html
hoverxref_auto_ref = True
hoverxref_domains = ["py"]
# Set the default style (tooltip) for all types to silence logging.
# See https://github.com/readthedocs/sphinx-hoverxref/issues/211
hoverxref_role_types = {
    "attr": "tooltip",
    "class": "tooltip",
    "const": "tooltip",
    "exc": "tooltip",
    "func": "tooltip",
    "meth": "tooltip",
    "mod": "tooltip",
    "obj": "tooltip",
    "ref": "tooltip",
    "data": "tooltip",
}

# See https://sphinx-codeautolink.readthedocs.io/en/latest/reference.html#configuration
codeautolink_autodoc_inject = False
codeautolink_global_preface = """
import trio
from trio import *
"""


def add_intersphinx(app: Sphinx) -> None:
    """Add some specific intersphinx mappings.

    Hooked up to builder-inited. app.builder.env.interpshinx_inventory is not an official API, so this may break on new sphinx versions.
    """

    def add_mapping(
        reftype: str,
        library: str,
        obj: str,
        version: str = "3.12",
        target: str | None = None,
    ) -> None:
        """helper function"""
        url_version = "3" if version == "3.12" else version
        if target is None:
            target = f"{library}.{obj}"

        # sphinx doing fancy caching stuff makes this attribute invisible
        # to type checkers
        inventory = app.builder.env.intersphinx_inventory  # type: ignore[attr-defined]
        assert isinstance(inventory, dict)
        inventory = cast("Inventory", inventory)

        inventory[f"py:{reftype}"][f"{target}"] = _InventoryItem(
            project_name="Python",
            project_version=version,
            uri=f"https://docs.python.org/{url_version}/library/{library}.html/{obj}",
            display_name="-",
        )

    # This has been removed in Py3.12, so add a link to the 3.11 version with deprecation warnings.
    add_mapping("method", "pathlib", "Path.link_to", "3.11")

    # defined in py:data in objects.inv, but sphinx looks for a py:class
    # see https://github.com/sphinx-doc/sphinx/issues/10974
    # to dump the objects.inv for the stdlib, you can run
    # python -m sphinx.ext.intersphinx http://docs.python.org/3/objects.inv
    add_mapping("class", "math", "inf")
    add_mapping("class", "types", "FrameType")

    # new in py3.12, and need target because sphinx is unable to look up
    # the module of the object if compiling on <3.12
    if not hasattr(collections.abc, "Buffer"):
        add_mapping("class", "collections.abc", "Buffer", target="Buffer")


autodoc_member_order = "bysource"

# Add any paths that contain templates here, relative to this directory.
templates_path = ["_templates"]

# The suffix(es) of source filenames.
# You can specify multiple suffix as a list of string:
#
# source_suffix = ['.rst', '.md']
source_suffix = ".rst"

# The master toctree document.
master_doc = "index"

# General information about the project.
project = "Trio"
copyright = "2017, Nathaniel J. Smith"  # noqa: A001 # Name shadows builtin
author = "Nathaniel J. Smith"

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
import importlib.metadata

version = importlib.metadata.version("trio")
# The full version, including alpha/beta/rc tags.
release = version

html_favicon = "_static/favicon-32.png"
html_logo = "../../logo/wordmark-transparent.svg"
# & down below in html_theme_options we set logo_only=True

# The language for content autogenerated by Sphinx. Refer to documentation
# for a list of supported languages.
#
# This is also used if you do content translation via gettext catalogs.
# Usually you set "language" from the command line for these cases.
language = "en"

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This patterns also effect to html_static_path and html_extra_path
exclude_patterns: list[str] = []

# The name of the Pygments (syntax highlighting) style to use.
pygments_style = "default"

highlight_language = "python3"

# If true, `todo` and `todoList` produce output, else they produce nothing.
todo_include_todos = False

# This avoids a warning by the epub builder that it can't figure out
# the MIME type for our favicon.
suppress_warnings = ["epub.unknown_project_files"]


# -- Options for HTML output ----------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#
# html_theme = 'alabaster'

# We have to set this ourselves, not only because it's useful for local
# testing, but also because if we don't then RTD will throw away our
# html_theme_options.
html_theme = "sphinx_rtd_theme"

# Theme options are theme-specific and customize the look and feel of a theme
# further.  For a list of options available for each theme, see the
# documentation.
#
html_theme_options = {
    # default is 2
    # show deeper nesting in the RTD theme's sidebar TOC
    # https://stackoverflow.com/questions/27669376/
    # I'm not 100% sure this actually does anything with our current
    # versions/settings...
    "navigation_depth": 4,
    "logo_only": True,
    "prev_next_buttons_location": "both",
    "style_nav_header_background": "#d2e7fa",
}

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ["_static"]


# -- Options for HTMLHelp output ------------------------------------------

# Output file base name for HTML help builder.
htmlhelp_basename = "Triodoc"


# -- Options for LaTeX output ---------------------------------------------

latex_elements: dict[str, object] = {
    # The paper size ('letterpaper' or 'a4paper').
    #
    # 'papersize': 'letterpaper',
    # The font size ('10pt', '11pt' or '12pt').
    #
    # 'pointsize': '10pt',
    # Additional stuff for the LaTeX preamble.
    #
    # 'preamble': '',
    # Latex figure (float) alignment
    #
    # 'figure_align': 'htbp',
}

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title,
#  author, documentclass [howto, manual, or own class]).
latex_documents = [
    (master_doc, "Trio.tex", "Trio Documentation", "Nathaniel J. Smith", "manual"),
]


# -- Options for manual page output ---------------------------------------

# One entry per manual page. List of tuples
# (source start file, name, description, authors, manual section).
man_pages = [(master_doc, "trio", "Trio Documentation", [author], 1)]


# -- Options for Texinfo output -------------------------------------------

# Grouping the document tree into Texinfo files. List of tuples
# (source start file, target name, title, author,
#  dir menu entry, description, category)
texinfo_documents = [
    (
        master_doc,
        "Trio",
        "Trio Documentation",
        author,
        "Trio",
        "One line description of project.",
        "Miscellaneous",
    ),
]
