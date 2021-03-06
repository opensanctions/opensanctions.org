# OpenSanctions.org

This repository contains the home page for OpenSanctions.org, an open-source repository of sanctions data, politically exposed persons, and other entities of interest.

OpenSanctions uses [Follow the Money](https://docs.alephdata.org/developers/followthemoney), a JSON-based anti-corruption data model, as a common target for all crawlers. Additonal exports into CSV and Excel formats are planned.

## Data sources

We collect data sources for this project [in this spreadsheet](https://docs.google.com/spreadsheets/d/1zHP91a-KT-MW-3s2Xb9-wPVhxTiPO1ZqJ90v4COswRY/edit#gid=0). Please feel free to create issues to suggest additional data sources, but read `CONTRIBUTING.md` before writing the needed code.

## Running

_This is currently undergoing a refactor._

```python
opensanction crawl <crawler>
```

