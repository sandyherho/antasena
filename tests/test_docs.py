"""Every >>> example in the documentation must reproduce its printed output."""
import doctest
import re
from pathlib import Path

import pytest

DOCS = Path(__file__).resolve().parents[1] / "docs"
PAGES = sorted(p for p in DOCS.glob("*.md") if ">>>" in p.read_text(encoding="utf-8"))


@pytest.mark.parametrize("page", PAGES, ids=lambda p: p.name)
def test_documentation_examples(page):
    blocks = re.findall(r"```python\n(.*?)```", page.read_text(encoding="utf-8"), re.S)
    src = "\n\n".join(b for b in blocks if ">>>" in b)
    test = doctest.DocTestParser().get_doctest(src, {}, page.name, str(page), 0)
    runner = doctest.DocTestRunner(optionflags=doctest.ELLIPSIS | doctest.NORMALIZE_WHITESPACE)
    runner.run(test)
    assert runner.failures == 0, f"{runner.failures} failing example(s) in {page.name}"
