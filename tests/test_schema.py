import json

import pytest
from jsonschema.protocols import Validator
from model_bakery import baker

from django_filtering import filters
from django_filtering.filterset import FilterSet
from django_filtering.schema import FilteringOptionsSchema, JSONSchema

from tests.lab_app import models
from tests.lab_app.filters import ParticipantFilterSet
from tests.market_app.filters import TopBrandKitchenProductFilterSet


class TestJsonSchema:
    def test_generation_of_schema(self):
        """
        Using the ParticipantScopedFilterSet with filters set in the Meta class,
        expect only those specified fields and lookups to be valid for use.
        """
        valid_filters = {
            "age": ["gte", "lte"],
            "sex": ["exact"],
        }

        class TestFilterSet(FilterSet):
            age = filters.Filter(
                filters.InputLookup('gte', label="greater than or equal to"),
                filters.InputLookup('lte', label="less than or equal to"),
                default_lookup="gte",
                label="Age",
            )
            sex = filters.Filter(
                filters.ChoiceLookup('exact', label='is'),
                default_lookup='exact',
                label="Sex",
            )

            class Meta:
                model = models.Participant

        filterset = TestFilterSet()
        json_schema = JSONSchema(filterset)
        schema = json_schema.schema

        # Check valid json-schema
        # Raises `jsonschema.exceptions.SchemaError` if there is an issue.
        Validator.check_schema(json_schema.schema)

        # Verify expected `$defs`, no more or less definitions
        expected_defs = ['and-or-op', 'not-op', 'filters'] + [f"{n}-filter" for n in valid_filters]
        assert sorted(schema['$defs'].keys()) == sorted(expected_defs)

        # Verify filters defined in the `#/$defs/filters` container
        expected = [{'$ref': f"#/$defs/{n}-filter"} for n in valid_filters]
        assert schema['$defs']['filters']['anyOf'] == expected

        # Look for the particular filters
        expected_age_filter = {
            'type': 'array',
            'prefixItems': [
                {'const': 'age'},
                {
                    'type': 'object',
                    'properties': {
                        'lookup': {'enum': valid_filters['age']},
                        'value': {'type': 'string'}
                    }
                }
            ]
        }
        assert schema['$defs']['age-filter'] == expected_age_filter
        expected_sex_filter = {
            'type': 'array',
            'prefixItems': [
                {'const': 'sex'},
                {
                    'type': 'object',
                    'properties': {
                        'lookup': {'enum': valid_filters['sex']},
                        'value': {'type': 'string'}
                    }
                }
            ]
        }
        assert schema['$defs']['sex-filter'] == expected_sex_filter

    def test_to_json(self):
        filterset = ParticipantFilterSet()
        json_schema = JSONSchema(filterset)

        assert json.dumps(json_schema.schema) == str(json_schema)
        assert json.loads(str(json_schema))


class TestFilteringOptionsSchema:
    def test_generation_of_schema(self):
        valid_filters = {
            "age": {
                "gte": {"type": "input", "label": "greater than or equal to"},
                "lte": {"type": "input", "label": "less than or equal to"},
            },
            "sex": {"exact": {
                "type": "choice",
                "label": "matches",
                "choices": [
                    ('u', 'Unknown',),
                    ('m', 'Male',),
                    ('f', 'Female',),
                    ('i', 'Intersex',),
                ],
            }},
        }

        class TestFilterSet(FilterSet):
            age = filters.Filter(
                filters.InputLookup('gte', label="greater than or equal to"),
                filters.InputLookup('lte', label="less than or equal to"),
                default_lookup="gte",
                label="Age",
            )
            sex = filters.Filter(
                filters.ChoiceLookup('exact', label='matches'),
                default_lookup='exact',
                label="Sex",
            )

            class Meta:
                model = models.Participant

        filterset = TestFilterSet()
        schema = FilteringOptionsSchema(filterset)

        # Check for operators
        expected = ['and', 'or', 'not']
        assert sorted(schema.schema['operators'].keys()) == sorted(expected)

        # Check for the valid FilterSet
        assert sorted(schema.schema['filters'].keys()) == sorted(valid_filters.keys())

        # Check for filters
        expected = {'default_lookup': list(valid_filters['age'].keys())[0], 'lookups': valid_filters['age'], 'label': 'Age'}
        assert schema.schema['filters']['age'] == expected
        expected = {'default_lookup': list(valid_filters['sex'].keys())[0], 'lookups': valid_filters['sex'], 'label': 'Sex'}
        assert schema.schema['filters']['sex'] == expected

    def test_generation_of_schema_w_sticky_filters(self):
        expected_filters = {
            'brand': {
                'default_lookup': 'exact',
                'is_sticky': True,
                'label': 'Brand',
                'lookups': {
                    'exact': {
                        'choices': [
                            ('all', 'All brands'),
                            ('Delta', 'Delta'),
                            ('MOEN', 'MOEN'),
                            ('Glacier Bay', 'Glacier Bay'),
                        ],
                        'label': 'is',
                        'type': 'choice',
                    },
                },
                'sticky_default': ['brand', {'lookup': 'exact', 'value': 'MOEN'}],
            },
            'category': {
                'default_lookup': 'exact',
                'is_sticky': True,
                'label': 'Category',
                'lookups': {
                    'exact': {
                        'choices': [
                            ('Bath', 'Bath'),
                            ('Kitchen', 'Kitchen'),
                            ('Patio', 'Patio'),
                        ],
                        'label': 'equals',
                        'type': 'choice'},
                },
                'sticky_default': ['category', {'lookup': 'exact', 'value': 'Kitchen'}],
            },
            'name': {
                'default_lookup': 'icontains',
                'label': 'Name',
                'lookups': {'icontains': {'label': 'contains', 'type': 'input'}},
            },
        }

        filterset = TopBrandKitchenProductFilterSet()
        schema = FilteringOptionsSchema(filterset)

        # Check for operators
        expected = ['and', 'or', 'not']
        assert sorted(schema.schema['operators'].keys()) == sorted(expected)

        # Check for the valid FilterSet
        assert sorted(schema.schema['filters'].keys()) == sorted(expected_filters.keys())

        # Check for filters
        assert schema.schema['filters']['name'] == expected_filters['name']
        assert schema.schema['filters']['category'] == expected_filters['category']
        assert schema.schema['filters']['brand'] == expected_filters['brand']

    def test_to_json(self):
        filterset = ParticipantFilterSet()
        schema = FilteringOptionsSchema(filterset)

        assert json.dumps(schema.schema) == str(schema)
        assert json.loads(str(schema))

    @pytest.mark.django_db
    def test_with_foreign_relation_field(self):
        participants = [baker.make(models.Participant) for i in range(0, 4)]

        expected_schema = {
            "state": {
                "default_lookup": "exact",
                "label": "State",
                "lookups": {
                    "exact": {
                        "type": "choice",
                        "label": "is",
                        "choices": [
                            (0, 'Drafting'),
                            (10, 'Cancelled'),
                            (20, 'Opened'),
                            (30, 'Reviewing'),
                            (40, 'Closed'),
                        ],
                    },
                },
            },
            "participants": {
                "default_lookup": "exact",
                "label": "Participant",
                "lookups": {
                    "exact": {
                        "type": "choice",
                        "label": "is",
                        "choices": [(p.id, str(p),) for p in participants],
                    },
                },
            }
        }

        class TestFilterSet(FilterSet):
            state = filters.Filter(
                filters.ChoiceLookup('exact', label='is'),
                default_lookup='exact',
                label="State",
            )
            participants = filters.Filter(
                filters.ChoiceLookup('exact', label='is'),
                default_lookup='exact',
                label="Participant",
            )

            class Meta:
                model = models.Study

        filterset = TestFilterSet()
        schema = FilteringOptionsSchema(filterset)

        # Check for the valid FilterSet
        assert sorted(schema.schema['filters'].keys()) == sorted(expected_schema.keys())

        # Check for filters
        for name, info in expected_schema.items():
            assert schema.schema['filters'][name] == info
