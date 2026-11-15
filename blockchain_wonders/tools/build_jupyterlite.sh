#!/usr/bin/env bash
# Builds a JupyterLite website so participants need nothing but a browser.
# Run from the blockchain_wonders folder:   bash tools/build_jupyterlite.sh
# Then publish the "site" folder (GitHub Pages, a university web server, or
# serve it on the room's network with:  python -m http.server --directory site 8000)
set -e
pip install jupyterlite-core jupyterlite-pyodide-kernel jupyter-server
rm -rf _lite_contents site
mkdir _lite_contents
cp -r wonders ./*.ipynb _lite_contents/
jupyter lite build --contents _lite_contents --output-dir site
rm -rf _lite_contents
echo "Done. Open site/index.html through a web server."
