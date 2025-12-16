## 0.3.2 - 2025-Dec-15

- Fixed: Corrected the choice form field generation for manytomany relational field (i.e. reverse relational field).

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
