# Reactor Notes

### Documentation

https://experienceleague.adobe.com/en/docs/experience-platform/tags/home

### Organisations

`<ORG_ID>@AdobeOrg`

### Companies

`<COMPANY_ID>`

### Properties

* **Your Web Property**: `<PROPERTY_ID>`

```json
{
  "attributes": {
    "created_at": "2025-01-01T00:00:00.000Z",
    "created_by_display_name": "Your Name",
    "created_by_email": "user@example.com",
    "development": false,
    "domains": [
      "example.com"
    ],
    "enabled": true,
    "name": "Your Web Property",
    "platform": "web",
    "rule_component_sequencing_enabled": true,
    "token": "<PROPERTY_TOKEN>",
    "undefined_vars_return_empty": false,
    "updated_at": "2025-01-01T00:00:00.000Z",
    "updated_by_display_name": "Your Name",
    "updated_by_email": "user@example.com"
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
        "value": "<PROPERTY_ID>"
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