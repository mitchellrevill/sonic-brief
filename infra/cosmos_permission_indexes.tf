# Optimized Cosmos DB Indexing Policy for Permissions
# Add this to your Terraform configuration or apply via Azure Portal/SDK

# Enhanced indexing policy for voice_auth_container (users)
resource "azurerm_cosmosdb_sql_container" "voice_auth_container_optimized" {
  name                = "voice_auth"
  resource_group_name = azurerm_resource_group.rg.name
  account_name        = azurerm_cosmosdb_account.voice_account.name
  database_name       = azurerm_cosmosdb_sql_database.voice_db.name

  partition_key_paths   = ["/id"]
  partition_key_version = 2

  # Unique key block: enforce uniqueness on the email field.
  unique_key {
    paths = ["/email"]
  }

  conflict_resolution_policy {
    mode                     = "LastWriterWins"
    conflict_resolution_path = "/_ts"
  }

  indexing_policy {
    indexing_mode = "consistent"

    # PERMISSION-SPECIFIC INDEXES
    # Index the permission property for efficient permission-based queries
    included_path {
      path = "/permission/?"
    }

    # Index email for user lookups
    included_path {
      path = "/email/?"
    }

    # Index created_at for sorting users by registration date
    included_path {
      path = "/created_at/?"
    }

    # Index last_login for user activity tracking
    included_path {
      path = "/last_login/?"
    }

    # Index permission_changed_at for audit queries
    included_path {
      path = "/permission_changed_at/?"
    }

    # Index permission_changed_by for audit trail
    included_path {
      path = "/permission_changed_by/?"
    }

    # Index is_active for filtering active/inactive users
    included_path {
      path = "/is_active/?"
    }

    # COMPOSITE INDEXES for complex queries
    # Composite index for permission + created_at (for sorted permission queries)
    composite_index {
      index {
        path  = "/permission"
        order = "ascending"
      }
      index {
        path  = "/created_at"
        order = "descending"
      }
    }

    # Composite index for permission + is_active (for active users by permission)
    composite_index {
      index {
        path  = "/permission"
        order = "ascending"
      }
      index {
        path  = "/is_active"
        order = "ascending"
      }
    }

    # Composite index for permission + last_login (for recent active users by permission)
    composite_index {
      index {
        path  = "/permission"
        order = "ascending"
      }
      index {
        path  = "/last_login"
        order = "descending"
      }
    }

    # Exclude unnecessary system properties to reduce index size
    excluded_path {
      path = "/_etag/?"
    }

    excluded_path {
      path = "/_attachments/?"
    }

    excluded_path {
      path = "/_rid/?"
    }

    excluded_path {
      path = "/_self/?"
    }
  }
}

# If you have a separate resources container, optimize it too
resource "azurerm_cosmosdb_sql_container" "resources_container" {
  name                = "resources"
  resource_group_name = azurerm_resource_group.rg.name
  account_name        = azurerm_cosmosdb_account.voice_account.name
  database_name       = azurerm_cosmosdb_sql_database.voice_db.name

  partition_key_paths   = ["/id"]
  partition_key_version = 2

  indexing_policy {
    indexing_mode = "consistent"

    # Index for resource type
    included_path {
      path = "/type/?"
    }

    # Index for minimum permission required
    included_path {
      path = "/min_permission_required/?"
    }

    # Index for owner/creator
    included_path {
      path = "/created_by/?"
    }

    # Index for creation date
    included_path {
      path = "/created_at/?"
    }

    # Index for resource status
    included_path {
      path = "/status/?"
    }

    # Composite indexes for resource access queries
    composite_index {
      index {
        path  = "/min_permission_required"
        order = "ascending"
      }
      index {
        path  = "/type"
        order = "ascending"
      }
    }

    composite_index {
      index {
        path  = "/min_permission_required"
        order = "ascending"
      }
      index {
        path  = "/created_at"
        order = "descending"
      }
    }

    # Exclude system properties
    excluded_path {
      path = "/_etag/?"
    }
  }
}

/*
MANUAL INDEX CREATION (If using SDK instead of Terraform):

For Users Container:
{
  "indexingMode": "consistent",
  "automatic": true,
  "includedPaths": [
    {
      "path": "/permission/?"
    },
    {
      "path": "/email/?"
    },
    {
      "path": "/created_at/?"
    },
    {
      "path": "/is_active/?"
    },
    {
      "path": "/last_login/?"
    },
    {
      "path": "/permission_changed_at/?"
    }
  ],
  "excludedPaths": [
    {
      "path": "/_etag/?"
    },
    {
      "path": "/_attachments/?"
    }
  ],
  "compositeIndexes": [
    [
      {
        "path": "/permission",
        "order": "ascending"
      },
      {
        "path": "/created_at",
        "order": "descending"
      }
    ],
    [
      {
        "path": "/permission",
        "order": "ascending"
      },
      {
        "path": "/is_active",
        "order": "ascending"
      }
    ]
  ]
}

PERFORMANCE BENEFITS:
1. Permission queries will be very fast (indexed lookups)
2. Composite indexes enable efficient sorting and filtering
3. Excluded paths reduce index size and improve write performance
4. Supports complex permission-based queries with optimal performance

QUERY EXAMPLES THAT WILL BE OPTIMIZED:
- SELECT * FROM users u WHERE u.permission = 'Admin'
- SELECT * FROM users u WHERE u.permission = 'User' ORDER BY u.created_at DESC
- SELECT * FROM users u WHERE u.permission = 'Admin' AND u.is_active = true
- SELECT * FROM resources r WHERE r.min_permission_required = 'User' AND r.type = 'document'
*/
