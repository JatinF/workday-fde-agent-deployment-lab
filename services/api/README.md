# API

The installed app is `fde_lab.api:create_app`. `services/api/routes.yaml` lists the paths. `fde-lab run-story` fails when that list drifts from the OpenAPI paths.

`GET /story` runs the field story in memory. It does not call Workday.
