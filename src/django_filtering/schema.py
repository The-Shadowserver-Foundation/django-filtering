import json


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


class JSONEncoder(json.JSONEncoder):
    """
    Overridden to provide encoding for the ``set`` type.
    """

    def default(self, o):
        if isinstance(o, set):
            return list(o)
        return super().default(o)


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
        definitions['filters'] = {"anyOf": [f"#/$defs/{n}" for n in fields]}
        schema = {
            "$id": "https://example.com/exp.json",  # TODO Provide serving url
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "title": f"{model_name} Schema",
            "type": "object",
            "properties": {
              "query": {
                "$ref": "#/$defs/and-or-op"
              }
            },
            "$defs": definitions,
        }
        return schema

    def __str__(self):
        return json.dumps(self.schema, cls=JSONEncoder)
