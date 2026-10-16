"""Typeset every equation in the built HTML docs with MathJax 4 and fail on any error.

Usage (after ``sphinx-build -b html docs docs/_build/html``)::

    npm install --no-save @mathjax/src@4
    python tools/check_math.py docs/_build/html

Requires Node.js. The equations are extracted exactly as Sphinx emits them,
then typeset with the same TeX packages MathJax loads in the browser.
"""
import html
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

JS = r"""
import {mathjax} from '@mathjax/src/mjs/mathjax.js';
import {TeX} from '@mathjax/src/mjs/input/tex.js';
import {SVG} from '@mathjax/src/mjs/output/svg.js';
import {liteAdaptor} from '@mathjax/src/mjs/adaptors/liteAdaptor.js';
import {RegisterHTMLHandler} from '@mathjax/src/mjs/handlers/html.js';
import '@mathjax/src/mjs/input/tex/base/BaseConfiguration.js';
import '@mathjax/src/mjs/input/tex/ams/AmsConfiguration.js';
import '@mathjax/src/mjs/input/tex/newcommand/NewcommandConfiguration.js';
import fs from 'fs';
RegisterHTMLHandler(liteAdaptor());
const tex = new TeX({packages: ['base', 'ams', 'newcommand'], formatError: (j, e) => { throw e; }});
const doc = mathjax.document('', {InputJax: tex, OutputJax: new SVG({fontCache: 'none'})});
const items = JSON.parse(fs.readFileSync(process.argv[2]));
let bad = 0;
for (const it of items) {
  try { doc.convert(it.tex, {display: it.display}); }
  catch (e) { bad++; console.log(`ERROR ${it.page}: ${e.message} :: ${it.tex}`); }
}
console.log(`${items.length} equations typeset, ${bad} errors`);
process.exit(bad ? 1 : 0);
"""


def main(build_dir: str) -> int:
    items, strays = [], []
    for page in sorted(Path(build_dir).glob("*.html")):
        text = page.read_text(encoding="utf-8")
        for m in re.finditer(r'class="math notranslate nohighlight">(.*?)</(span|div)>', text, re.S):
            s = html.unescape(m.group(1)).strip()
            items.append({"page": page.name, "tex": s[2:-2], "display": not s.startswith("\\(")})
        body = re.sub(r"<pre.*?</pre>|<code.*?</code>|<script.*?</script>|<style.*?</style>", "",
                      text, flags=re.S)
        plain = html.unescape(re.sub(r"<[^>]+>", "", body))
        strays += [f"{page.name}: {m.group(0)}" for m in re.finditer(r"\$[^$\n]{1,60}\$", plain)]
    for s in strays:
        print("UNRENDERED", s)
    with tempfile.TemporaryDirectory() as tmp:
        data = Path(tmp) / "math.json"
        data.write_text(json.dumps(items))
        script = Path.cwd() / "check_math_tmp.mjs"   # resolve node_modules from the repo root
        script.write_text(JS)
        try:
            rc = subprocess.call(["node", str(script), str(data)])
        finally:
            script.unlink()
    return 1 if (rc or strays) else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "docs/_build/html"))
