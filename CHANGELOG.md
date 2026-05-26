## 0.6.0 - 2026-May-26

- Changed: Ensure blank option in form field choices and define empty choice.
- Changed: Make Filter.resolve_field a public method.

## 0.5.0 - 2026-May-24

- Added: FilterSet.has_query_data property provides a convenience check for the presents of query-data.
- Fixed: Translation behavior of flat form to only translate when there are no errors.
- Fixed: Argument assignment for flat filtering form factory's base class.

## 0.4.0 - 2026-May-15

- Fixed: wheel and sdist builds to include Django templates
- Changed: Require Python >= 3.10
- Added: PartialDateRangeLookup for filtering by only part of the range
- Fixed: DateRangeLookup to use the range lookup rather than date
- Fixed: Resolved design flaw in lookup as multiple form fields
- Fixed: Addressed `ruff` errors and increase max line-length
- Fixed: variable name typo in `filters_for_model` generation
- Updated: `ruff-pre-commit`
- Changed: Use the plural module naming convention typically used across Python packages
- Changed: Allow assignment of base class in flat form factory
- Changed: Move form module to package to allow space for additional logic
- Fixed: Made `filterset_factory` minimally functional
- Fixed: Correct flat form initial values for stick filters

## 0.3.2 - 2025-Dec-15

- Fixed: Corrected the choice form field generation for many-to-many relational field (i.e. reverse relational field).

## 0.3.1 - 2025-Dec-15

- Added: Wrote a changelog to keep track of release history.
- Changed: Correct various linting errors caught by ruff.
- Fixed: Corrected the generation of form fields for choice filters, choice fields or relational fields.
- Added: Use pre-commit with ruff to enforce consistency.
- Added: Allow developer to configure hidden fields on the flat form. Also allow the use of a wildcard in hidden fields definition.

## 0.3.0 - 2025-Dec-11

- Changed: Update and fix README code examples.
- Docs: Provide documentation for the included forms and form factories.
- Added: Production of a *flat form* from a filterset. Allows accepting one level of criteria via a Django Form.
- Fixed: Carry over the FilterSet's Meta options for subclassing.
- Docs: Fix query data structure documentation.
- Changed: Use the declarative filters in the testing `lab_app`.
- Added: Use a lookup label from configuration when generating lookups.
- Added: Provide app configuration for settings.
- Added: Created filters via metadata defined fields and lookups.
- Changed: Reorganized testing modules.
