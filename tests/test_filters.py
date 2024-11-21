from django_filtering.filters import Q


class TestQ:
    def test_from_query_data(self):
        data = (
            "title",
            {"lookup": "icontains", "value": "stove"},
        )
        q = Q.from_query_data(data)
        expected = Q(("title__icontains", "stove"), _connector=Q.AND)
        assert q == expected

        data = ("not", ("title", {"lookup": "icontains", "value": "stove"}))
        q = Q.from_query_data(data)
        expected = Q(("title__icontains", "stove"), _connector=Q.AND, _negated=True)
        assert q == expected

        data = (
            "not",
            (
                "or",
                (
                    (
                        "title",
                        {"lookup": "icontains", "value": "stove"},
                    ),
                    (
                        "title",
                        {"lookup": "icontains", "value": "oven"},
                    ),
                ),
            ),
        )
        q = Q.from_query_data(data)
        expected = ~(Q(title__icontains="stove") | Q(title__icontains="oven"))
        assert q == expected

        data = (
            "or",
            (
                ("title", {"lookup": "icontains", "value": "stove"}),
                (
                    "and",
                    (
                        ("title", {"lookup": "icontains", "value": "oven"}),
                        ("not", ("title", {"lookup": "icontains", "value": "microwave"})),
                    ),
                ),
            ),
        )
        q = Q.from_query_data(data)
        expected = Q(title__icontains="stove") | (
            Q(title__icontains="oven") & ~Q(title__icontains="microwave")
        )
        assert q == expected

        data = (
            "and",
            (
                ("category", {"lookup": "in", "value": ["Kitchen", "Bath"]}),
                ("stocked", {"lookup": ["year", "gte"], "value": "2024"}),
                (
                    "or",
                    (
                        (
                            "and",
                            (
                                ("title", {"lookup": "icontains", "value": "soap"}),
                                ("title", {"lookup": "icontains", "value": "hand"}),
                                ("not", ("title", {"lookup": "icontains", "value": "lotion"})),
                            ),
                        ),
                        # Note, the missing 'lookup' value, to test default lookup
                        ("brand", {"value": "Safe Soap"}),
                    ),
                ),
            ),
        )
        q = Q.from_query_data(data)
        expected = (
            Q(category__in=["Kitchen", "Bath"])
            & Q(stocked__year__gte="2024")
            & (
                (
                    Q(title__icontains="soap")
                    & Q(title__icontains="hand")
                    & ~Q(title__icontains="lotion")
                )
                | Q(brand__iexact="Safe Soap")
            )
        )
        assert q == expected

    def test_to_query_data(self):
        q = Q(("title__icontains", "stove"), _connector=Q.AND)
        data = q.to_query_data()
        expected = (
            "title",
            {"lookup": "icontains", "value": "stove"},
        )
        assert data == expected

        q = Q(("title__icontains", "stove"), _connector=Q.AND, _negated=True)
        data = q.to_query_data()
        expected = ("not", ("title", {"lookup": "icontains", "value": "stove"}))
        assert data == expected

        q = ~(Q(title__icontains="stove") | Q(title__icontains="oven"))
        data = q.to_query_data()
        expected = (
            "not",
            (
                "or",
                (
                    (
                        "title",
                        {"lookup": "icontains", "value": "stove"},
                    ),
                    (
                        "title",
                        {"lookup": "icontains", "value": "oven"},
                    ),
                ),
            ),
        )
        assert data == expected

        q = Q(title__icontains="stove") | (
            Q(title__icontains="oven") & ~Q(title__icontains="microwave")
        )
        data = q.to_query_data()
        expected = (
            "or",
            (
                ("title", {"lookup": "icontains", "value": "stove"}),
                (
                    "and",
                    (
                        ("title", {"lookup": "icontains", "value": "oven"}),
                        ("not", ("title", {"lookup": "icontains", "value": "microwave"})),
                    ),
                ),
            ),
        )
        assert data == expected

        q = (
            Q(category__in=["Kitchen", "Bath"])
            & Q(stocked__year__gte="2024")
            & (
                (
                    Q(title__icontains="soap")
                    & Q(title__icontains="hand")
                    & ~Q(title__icontains="lotion")
                )
                | Q(brand__iexact="Safe Soap")
            )
        )
        data = Q.to_query_data(q)
        expected = (
            "and",
            (
                ("category", {"lookup": "in", "value": ["Kitchen", "Bath"]}),
                ("stocked", {"lookup": ["year", "gte"], "value": "2024"}),
                (
                    "or",
                    (
                        (
                            "and",
                            (
                                ("title", {"lookup": "icontains", "value": "soap"}),
                                ("title", {"lookup": "icontains", "value": "hand"}),
                                ("not", ("title", {"lookup": "icontains", "value": "lotion"})),
                            ),
                        ),
                        ("brand", {"lookup": "iexact", "value": "Safe Soap"}),
                    ),
                ),
            ),
        )
        assert data == expected
