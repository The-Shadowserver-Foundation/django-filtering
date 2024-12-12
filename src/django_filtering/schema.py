import json


class FilteringOptionsSchema:
    def __init__(self, filterset):
        self.filterset = filterset

    def _get_field(self, field_name):
        return self.filterset._meta.model._meta.get_field(field_name)

    @property
    def schema(self):
        operators = {
            "and": {"type": "operator", "label": "All of..."},
            "or": {"type": "operator", "label": "Any of..."},
            "not": {"type": "operator", "label": "None of..."},
        }
        filters = {}
        for filter_name, lookups in self.filterset.valid_filters.items():
            field = self._get_field(filter_name)
            if field.is_relation:
                # FIXME Ideally we aren't dropping relational fields,
                #       but these are a feature not entirely needed at this time.
                continue
            info = {
                "type": "field",
                "field_type": "string",
                "lookups": lookups,
                "label": field.verbose_name.title(),
            }
            if field.help_text:
                info['description'] = field.help_text
            # TODO nargs
            filters[filter_name] = info
        return {'operators': operators, 'filters': filters}

    def __str__(self):
            return json.dumps(self.schema)


BASE_DEFINITIONS = {
    "and-or-op": {
        "type": "array",
        "prefixItems": [
            { "enum": ["and", "or"] },
            {
                "type": "array",
                "items": {
                    "anyOf": [
                        { "$ref": "#/$defs/filters" },
                        { "$ref": "#/$defs/and-or-op" },
                        { "$ref": "#/$defs/not-op" },
                    ],
                },
            },
        ],
    },
    "not-op": {
        "type": "array",
        "prefixItems": [
            { "const": "not" },
            {
                "oneOf": [
                    { "$ref": "#/$defs/filters" },
                    { "$ref": "#/$defs/and-or-op" },
                    { "$ref": "#/$defs/not-op" },
                ]
            },
        ],
    },
}


class JSONSchema:
    def __init__(self, filterset):
        self.filterset = filterset

    @property
    def schema(self):
        model_name = self.filterset._meta.model._meta.model_name.title()
        # Defines the `$defs` portion of the schema
        definitions = BASE_DEFINITIONS.copy()
        # Listing of all defined fields to produce the `#/$defs/filters` definition
        fields = []
        for filter_name, lookups in self.filterset.valid_filters.items():
            name = f"{filter_name}-filter"
            fields.append(name)
            definitions[name] = {
                "type": "array",
                "prefixItems": [
                    {"const": filter_name},
                    {
                        "type": "object",
                        "properties": {
                            "lookup": {"enum": lookups},
                            "value": {"type": "string"},
                        },
                    },
                ],
            }
        definitions['filters'] = {'anyOf': [{'$ref': f"#/$defs/{n}"} for n in fields]}
        schema = {
            "$id": f"https://example.com/{model_name}.json",  # TODO Provide serving url
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "title": f"{model_name} Schema",
            "$ref": "#/$defs/and-or-op",
            "$defs": definitions,
        }
        return schema

    def __str__(self):
        return json.dumps(self.schema)
