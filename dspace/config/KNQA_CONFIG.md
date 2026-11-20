# KNQA backend configuration

This branch (`knqa-backend`) is official DSpace plus a few KNQA configuration changes. Everything
else is unchanged upstream code, so DSpace releases merge cleanly. This file lists every KNQA change,
so an upgrade can check them.

## Files KNQA adds (no merge conflicts possible)

| File | Purpose |
|---|---|
| `controlled-vocabularies/knqa_types.xml` | KNQA document types for Describe → Type (`dc.type`) |
| `local.cfg.knqa-production.EXAMPLE` | Production `local.cfg` template |
| `KNQA_CONFIG.md` | This file |
| `../../knqa/knqa_types_to_oai.py` | Keeps the OAI export in step with `knqa_types.xml` |
| `../../docker-compose.override.yml` | Local Docker development settings |

## Upstream files KNQA edits

| File | Change | Marker |
|---|---|---|
| `submission-forms.xml` | The `dc.type` field in `traditionalpageone` and `publicationStep` uses the `knqa_types` vocabulary (onebox, closed, single value) instead of the `common_types` dropdown | `<!-- KNQA: document types … -->` |
| `crosswalks/oai/metadataFormats/oai_openaire.xsl` | Generated block mapping each KNQA type to a COAR resource type URI and OpenAIRE `resourceTypeGeneral` | `<!-- KNQA types … -->` … `<!-- end KNQA types -->` |

Settings that must be in the server's `local.cfg` (they're already in the template):
`user.registration = false`, `feedback.recipient`, `oai.identifier.prefix`, and
`vocabulary.plugin.knqa_types.hierarchy.store = false` and `vocabulary.plugin.knqa_types.hierarchy.preloadLevel = 2`.

## Document types (`knqa_types`)

- Clicking Describe → Type opens a picker: a search box ("standard", "report") above the groups
  (already expanded: `hierarchy.preloadLevel = 2`). Only listed types are accepted; groups
  (`selectable="false"`) can't be chosen.
- Items store only the type label, e.g. `dc.type = Occupational standard`. The search "Item type"
  filter and the homepage "Research Papers" and "Reports" tiles use these labels; the tiles' lists are in
  the Angular theme (`src/themes/knqa/app/home-page/repository-insights/repository-insights.component.ts`).
- Every type has `<hasNote>COAR: <type></hasNote>`, which names the COAR resource type it is exported as
  through OAI-PMH (`oai_openaire`). The `<type>` must be one the crosswalk already maps (e.g. `report`,
  `text`, `technical documentation`, `research report`); `COAR: other` uses the crosswalk's default.

**Adding a type:**
1. Copy a `<node>` inside the right group in `knqa_types.xml`, and give it a new unique `id`
   (`knqa_<group>_<name>`), a `label`, and a `COAR:` note.
2. From the repository root, run `python3 knqa/knqa_types_to_oai.py`. It rewrites the KNQA block in
   `oai_openaire.xsl`, and fails if a label is duplicated or a COAR type is unknown.
3. If it's a paper or report type, add it to the homepage tile lists in the Angular theme.
4. On the server, copy both files into `/dspace/config/...` and restart `dspace-backend`.

**Never change an `id`.** A label can be renamed, but items keep the old text, so update them with
batch metadata editing.

## On a DSpace upgrade

```bash
OLD=dspace-9.4; NEW=dspace-9.x      # previous and new release tags
# Did upstream change the files KNQA edits? Re-check our edits still fit.
git diff $OLD $NEW --stat -- dspace/config/submission-forms.xml \
    dspace/config/crosswalks/oai/metadataFormats/oai_openaire.xsl
# After the merge: the KNQA OAI block must still be current
python3 knqa/knqa_types_to_oai.py --check
```
If the merge conflicts in `oai_openaire.xsl`, take the upstream version and run
`python3 knqa/knqa_types_to_oai.py` to regenerate the KNQA block.
