# Generate a random complex password
resource "random_password" "db_password" {
  length           = 16
  special          = true
  override_special = "!#$%&*()-_=+[]{}<>:?"
}

resource "azurerm_cosmosdb_account" "voice_account" {
  name                = "${local.name_prefix}-voice-${random_string.unique.result}"
  location            = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name
  offer_type          = "Standard"
  kind                = "GlobalDocumentDB"

  identity {
    type = "SystemAssigned"
  }
  consistency_policy {
    consistency_level       = "BoundedStaleness"
    max_interval_in_seconds = 5
    max_staleness_prefix    = 100
  }

  geo_location {
    location          = azurerm_resource_group.rg.location
    failover_priority = 0
    zone_redundant    = false
  }



  is_virtual_network_filter_enabled = false
  public_network_access_enabled     = true
  analytical_storage_enabled        = false
  minimal_tls_version               = "Tls12"

  multiple_write_locations_enabled   = false
  automatic_failover_enabled         = false
  free_tier_enabled                  = false
  access_key_metadata_writes_enabled = false



  backup {
    type                = "Periodic"
    storage_redundancy  = "Geo"
    interval_in_minutes = 240
    retention_in_hours  = 8
  }
  capabilities {
    name = "EnableServerless"
  }

  capacity {
    total_throughput_limit = 4000
  }
  tags = local.default_tags

}

resource "azurerm_cosmosdb_sql_database" "voice_db" {
  name                = "VoiceDB"
  resource_group_name = azurerm_resource_group.rg.name
  account_name        = azurerm_cosmosdb_account.voice_account.name
}

resource "azurerm_cosmosdb_sql_container" "voice_auth_container" {
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

    # CRITICAL: Add missing type index (used in every query)
    included_path {
      path = "/type/?"
    }

    # CRITICAL: Add missing permission index (your most frequent query)
    included_path {
      path = "/permission/?"
    }

    # Index the email property.
    included_path {
      path = "/email/?"
    }

    # Add created_at for sorting
    included_path {
      path = "/created_at/?"
    }

    # Add is_active for user filtering
    included_path {
      path = "/is_active/?"
    }

    # CRITICAL: Composite index for type + permission (90% of your queries)
    composite_index {
      index {
        path  = "/type"
        order = "ascending"
      }
      index {
        path  = "/permission"
        order = "ascending"
      }
    }

    # Composite index for type + id (exact user lookups)
    composite_index {
      index {
        path  = "/type"
        order = "ascending"
      }
      index {
        path  = "/id"
        order = "ascending"
      }
    }

    # Composite index for type + email (login queries)
    composite_index {
      index {
        path  = "/type"
        order = "ascending"
      }
      index {
        path  = "/email"
        order = "ascending"
      }
    }

    # Catch-all path to index any other properties.
    included_path {
      path = "/*"
    }

    # Exclude the _etag system property.
    excluded_path {
      path = "/_etag/?"
    }
  }
}

resource "azurerm_cosmosdb_sql_container" "voice_jobs_container" {
  name                = "voice_jobs"
  resource_group_name = azurerm_resource_group.rg.name
  account_name        = azurerm_cosmosdb_account.voice_account.name
  database_name       = azurerm_cosmosdb_sql_database.voice_db.name

  partition_key_paths   = ["/id"]
  partition_key_version = 2

  # Unique key block: enforce uniqueness on the combination of user_id and created_at.
  unique_key {
    paths = ["/user_id", "/created_at"]
  }

  conflict_resolution_policy {
    mode                     = "LastWriterWins"
    conflict_resolution_path = "/_ts"
  }

  indexing_policy {
    indexing_mode = "consistent"

    # CRITICAL: Add missing type index (every query includes this)
    included_path {
      path = "/type/?"
    }

    # Index the user_id property.
    included_path {
      path = "/user_id/?"
    }

    # Index status for job filtering
    included_path {
      path = "/status/?"
    }

    # Index created_at for sorting
    included_path {
      path = "/created_at/?"
    }

    # Index the prompt_category_id property.
    included_path {
      path = "/prompt_category_id/?"
    }

    # Index the prompt_subcategory_id property.
    included_path {
      path = "/prompt_subcategory_id/?"
    }

    # CRITICAL: Composite index for type + user_id (user's jobs listing)
    composite_index {
      index {
        path  = "/type"
        order = "ascending"
      }
      index {
        path  = "/user_id"
        order = "ascending"
      }
    }

    # Composite index for type + status (job filtering)
    composite_index {
      index {
        path  = "/type"
        order = "ascending"
      }
      index {
        path  = "/status"
        order = "ascending"
      }
    }

    # Composite index for user_id + status + created_at (filtered job listing)
    composite_index {
      index {
        path  = "/user_id"
        order = "ascending"
      }
      index {
        path  = "/status"
        order = "ascending"
      }
      index {
        path  = "/created_at"
        order = "descending"
      }
    }

    # Catch-all path to index any other properties.
    included_path {
      path = "/*"
    }

    # Exclude the _etag system property.
    excluded_path {
      path = "/_etag/?"
    }
  }
}

resource "azurerm_cosmosdb_sql_container" "voice_prompts_container" {
  name                = "voice_prompts"
  resource_group_name = azurerm_resource_group.rg.name
  account_name        = azurerm_cosmosdb_account.voice_account.name
  database_name       = azurerm_cosmosdb_sql_database.voice_db.name

  partition_key_paths   = ["/id"]
  partition_key_version = 2

  # Unique key block: enforce uniqueness on the name field.
  unique_key {
    paths = ["/name"]
  }

  conflict_resolution_policy {
    mode                     = "LastWriterWins"
    conflict_resolution_path = "/_ts"
  }

  indexing_policy {
    indexing_mode = "consistent"

    # Index the type property (to differentiate between categories and subcategories).
    included_path {
      path = "/type/?"
    }

    # Index the category_id property (used in subcategories).
    included_path {
      path = "/category_id/?"
    }

    # Index the name property.
    included_path {
      path = "/name/?"
    }

    # Add ordering support
    included_path {
      path = "/order/?"
    }

    # Add active status support
    included_path {
      path = "/is_active/?"
    }

    # CRITICAL: Composite index for type + category_id (subcategory queries)
    composite_index {
      index {
        path  = "/type"
        order = "ascending"
      }
      index {
        path  = "/category_id"
        order = "ascending"
      }
    }

    # Composite index for type + is_active (active prompts only)
    composite_index {
      index {
        path  = "/type"
        order = "ascending"
      }
      index {
        path  = "/is_active"
        order = "ascending"
      }
    }

    # Catch-all path to index any other properties.
    included_path {
      path = "/*"
    }

    # Exclude the _etag system property.
    excluded_path {
      path = "/_etag/?"
    }
  }
}

resource "azurerm_cosmosdb_sql_container" "voice_user_sessions_container" {
  name                = "voice_user_sessions"
  resource_group_name = azurerm_resource_group.rg.name
  account_name        = azurerm_cosmosdb_account.voice_account.name
  database_name       = azurerm_cosmosdb_sql_database.voice_db.name

  partition_key_paths   = ["/user_id"]
  partition_key_version = 1

  conflict_resolution_policy {
    mode                     = "LastWriterWins"
    conflict_resolution_path = "/_ts"
  }

  indexing_policy {
    indexing_mode = "consistent"

    # Index the user_id property for session queries
    included_path {
      path = "/user_id/?"
    }

    # Index session_id for direct session lookups
    included_path {
      path = "/session_id/?"
    }

    # Index created_at for session cleanup and expiry
    included_path {
      path = "/created_at/?"
    }

    # Index expires_at for automatic session expiry
    included_path {
      path = "/expires_at/?"
    }

    # Index is_active for active session filtering
    included_path {
      path = "/is_active/?"
    }

    # Composite index for user_id + is_active (active sessions per user)
    composite_index {
      index {
        path  = "/user_id"
        order = "ascending"
      }
      index {
        path  = "/is_active"
        order = "ascending"
      }
    }

    # Composite index for expires_at + is_active (session cleanup)
    composite_index {
      index {
        path  = "/expires_at"
        order = "ascending"
      }
      index {
        path  = "/is_active"
        order = "ascending"
      }
    }

    # Catch-all path to index any other properties.
    included_path {
      path = "/*"
    }

    # Exclude the _etag system property.
    excluded_path {
      path = "/_etag/?"
    }
  }
}

resource "azurerm_cosmosdb_sql_container" "voice_audit_logs_container" {
  name                = "voice_audit_logs"
  resource_group_name = azurerm_resource_group.rg.name
  account_name        = azurerm_cosmosdb_account.voice_account.name
  database_name       = azurerm_cosmosdb_sql_database.voice_db.name

  partition_key_paths   = ["/user_id"]
  partition_key_version = 1

  conflict_resolution_policy {
    mode                     = "LastWriterWins"
    conflict_resolution_path = "/_ts"
  }

  indexing_policy {
    indexing_mode = "consistent"

    # Index the user_id property for user-specific audit queries
    included_path {
      path = "/user_id/?"
    }

    # Index action for filtering by audit action type
    included_path {
      path = "/action/?"
    }

    # Index timestamp for chronological queries
    included_path {
      path = "/timestamp/?"
    }

    # Index resource_type for filtering by resource
    included_path {
      path = "/resource_type/?"
    }

    # Index resource_id for specific resource audit trails
    included_path {
      path = "/resource_id/?"
    }

    # Index severity for filtering by log severity
    included_path {
      path = "/severity/?"
    }

    # Composite index for user_id + timestamp (user audit timeline)
    composite_index {
      index {
        path  = "/user_id"
        order = "ascending"
      }
      index {
        path  = "/timestamp"
        order = "descending"
      }
    }

    # Composite index for action + timestamp (action timeline)
    composite_index {
      index {
        path  = "/action"
        order = "ascending"
      }
      index {
        path  = "/timestamp"
        order = "descending"
      }
    }

    # Composite index for resource_type + resource_id + timestamp (resource audit trail)
    composite_index {
      index {
        path  = "/resource_type"
        order = "ascending"
      }
      index {
        path  = "/resource_id"
        order = "ascending"
      }
      index {
        path  = "/timestamp"
        order = "descending"
      }
    }

    # Catch-all path to index any other properties.
    included_path {
      path = "/*"
    }

    # Exclude the _etag system property.
    excluded_path {
      path = "/_etag/?"
    }
  }
}



resource "azurerm_cosmosdb_sql_role_definition" "data_reader" {
  resource_group_name = azurerm_resource_group.rg.name
  account_name        = azurerm_cosmosdb_account.voice_account.name
  name                = "${local.name_prefix}-voice-reader-role"
  type                = "BuiltInRole"
  assignable_scopes   = [azurerm_cosmosdb_account.voice_account.id]



  permissions {
    data_actions = ["Microsoft.DocumentDB/databaseAccounts/sqlDatabases/containers/items/read",
      "Microsoft.DocumentDB/databaseAccounts/readMetadata",
      "Microsoft.DocumentDB/databaseAccounts/sqlDatabases/containers/executeQuery",
      "Microsoft.DocumentDB/databaseAccounts/sqlDatabases/containers/readChangeFeed",
      "Microsoft.DocumentDB/databaseAccounts/sqlDatabases/containers/items/read"
    ]
  }
}

resource "azurerm_cosmosdb_sql_role_definition" "data_contributor" {
  resource_group_name = azurerm_resource_group.rg.name
  account_name        = azurerm_cosmosdb_account.voice_account.name
  name                = "${local.name_prefix}-voice-contributer-role"
  type                = "BuiltInRole"
  assignable_scopes   = [azurerm_cosmosdb_account.voice_account.id]


  permissions {
    data_actions = [
      "Microsoft.DocumentDB/databaseAccounts/readMetadata",
      "Microsoft.DocumentDB/databaseAccounts/sqlDatabases/containers/*",
      "Microsoft.DocumentDB/databaseAccounts/sqlDatabases/containers/items/*"
    ]
  }
}
