# Contributing

Use Python >=3.11, install the normal wheel, run `python -m unittest discover -s tests -v`, `python examples/demo.py`, and `python examples/benchmark.py`. Tests should independently falsify a model invariant, state boundary or claimed distinction. The small oracle deliberately avoids solver helpers. Keep deterministic order and schema/error compatibility.

Changes to signal semantics need independent ground-truth comparisons and adverse cases. Credit primary-source methods; do not claim unverified competitor omissions, calibrated detection probabilities or actual customers. New runner adapters must separate selection from target outcome access and preserve exact attempt/environment identities. Document resource complexity and UNKNOWN behavior before raising limits.
