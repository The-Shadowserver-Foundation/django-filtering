# Sticky Filters

A required filter that when present in a `FilterSet`
will produce filter criteria regardless of user input,
unless the user has explcitly overriden the default.
This concept is called a _sticky filter_
because the filter stuck to the filterset like gum on the bottom of a shoe.

A sticky filter is present in the `FilterSet`'s query regardless of the user's input.
It's not until the user sets this filter explicitly
to the _solvent_ value--usually a choice--that the filter
will be removed from the overall query.

For example, say we define a `FilterSet` for a task model
where our desire is that the model's ``status`` field be `'complete'`.
We also want to enable the user to search for `'any'` status,
which will remove the criteria from the query.
We can achieve this by providing a sticky filter
that defaults to the desired value (i.e. `'complete'`),
but does not produce a query filter
when the value results in the solvent value (e.g. empty string or keyword).

    class TaskFilterSet(FilterSet):
        STATUS_CHOICES = [
            ('any', 'Any'),
            ('p', 'Pending'),
            ('c', 'Complete'),
        ]
        status = Filter(
            ChoiceLookup('exact', label='is', choices=STATUS_CHOICES),
            sticky_value='c',
            solvent_value='any',
            label="Status",
        )
        # ...

The two parameters that make a Filter sticky are
`sticky_value` to set the default value for the query
and
`solvent_value` to allow the user to remove the filter from the query.
