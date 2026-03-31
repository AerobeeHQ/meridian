# Reactor Notes

### Documentation

https://experienceleague.adobe.com/en/docs/experience-platform/tags/home

### Organisations

`CE6D2999554750267F000101@AdobeOrg`

### Companies

`CO9d0207c86586409da0e0808fba656a17`

### Properties

* **AAA Web Property**: `PR5439e4310a364080ab16e35dcec7ace7`

```json
{
  "attributes": {
    "created_at": "2025-12-04T22:19:16.267Z",
    "created_by_display_name": "Joris de Beer",
    "created_by_email": "joris.debeer@maxisdigital.com.au",
    "development": false,
    "domains": [
      "maxisdev.com"
    ],
    "enabled": true,
    "name": "AAA Web Property",
    "platform": "web",
    "rule_component_sequencing_enabled": true,
    "token": "83be834d9281",
    "undefined_vars_return_empty": false,
    "updated_at": "2025-12-04T22:19:16.267Z",
    "updated_by_display_name": "Joris de Beer",
    "updated_by_email": "joris.debeer@maxisdigital.com.au"
  }
}
```

### Search everything

```json
{
  "data": {
    "from": 0,
    "size": 10,
    "query": {
      "attributes.*": {
        "value": "eVar1"
      },
      "relationships.property.data.id": {
        "value": "PR5439e4310a364080ab16e35dcec7ace7"
      },
      "attributes.deleted_at": {
        "exists": false
      },
      "attributes.revision_number": {
        "value": 0
      }
    },
    "sort": [
      {
        "attributes.updated_at": "desc"
      }
    ],
    "resource_types": [
      "rules",
      "rule_components",
      "data_elements",
      "extensions"
    ]
  }
}
```