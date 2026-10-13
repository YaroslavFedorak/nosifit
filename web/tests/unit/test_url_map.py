"""The URL map has one view per URL and method.

With two rules for the same URL and method only the first registered one is
ever reached; the other is dead code that looks alive.
"""

from collections import defaultdict


def test_no_url_is_registered_twice(app):
    views = defaultdict(list)
    for rule in app.url_map.iter_rules():
        for method in rule.methods - {"HEAD", "OPTIONS"}:
            views[(rule.rule, method)].append(rule.endpoint)

    assert {key: endpoints for key, endpoints in views.items() if len(endpoints) > 1} == {}
