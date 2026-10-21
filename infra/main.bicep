@description('Azure region for every resource. Defaults to the resource group region.')
param location string = resourceGroup().location

@description('Prefix for resource names.')
param name string = 'small-clinic'

@description('Container image of the API, for example kreezy09/small-clinic:<git-sha>.')
param image string

@description('Docker Hub account that pulls the image.')
param dockerHubUsername string

@secure()
@description('Docker Hub access token used to pull the image.')
param dockerHubToken string

@secure()
@description('Django SECRET_KEY.')
param djangoSecretKey string

@secure()
@description('Administrator password of the PostgreSQL server.')
param postgresAdminPassword string

@description('IANA time zone of the clinic.')
param clinicTimezone string = 'Africa/Nairobi'

@description('Minimum minutes between now and an appointment start for it to be bookable.')
param bookingMinLeadMinutes int = 60

@description('Minimum number of API replicas. 0 lets the API scale to zero when idle.')
param minReplicas int = 0

@description('Maximum number of API replicas.')
param maxReplicas int = 2

var postgresAdminLogin = 'clinicadmin'
var postgresDatabase = 'small_clinic'
var suffix = uniqueString(resourceGroup().id)

resource postgres 'Microsoft.DBforPostgreSQL/flexibleServers@2025-08-01' = {
  name: '${name}-db-${suffix}'
  location: location
  sku: {
    name: 'Standard_B1ms'
    tier: 'Burstable'
  }
  properties: {
    version: '18'
    administratorLogin: postgresAdminLogin
    administratorLoginPassword: postgresAdminPassword
    storage: {
      storageSizeGB: 32
      autoGrow: 'Disabled'
    }
    backup: {
      backupRetentionDays: 7
      geoRedundantBackup: 'Disabled'
    }
    highAvailability: {
      mode: 'Disabled'
    }
    network: {
      publicNetworkAccess: 'Enabled'
    }
  }
}

resource postgresExtensions 'Microsoft.DBforPostgreSQL/flexibleServers/configurations@2025-08-01' = {
  parent: postgres
  name: 'azure.extensions'
  properties: {
    value: 'BTREE_GIST'
    source: 'user-override'
  }
}

resource postgresDatabaseResource 'Microsoft.DBforPostgreSQL/flexibleServers/databases@2025-08-01' = {
  parent: postgres
  name: postgresDatabase
  properties: {
    charset: 'UTF8'
    collation: 'en_US.utf8'
  }
  dependsOn: [
    postgresExtensions
  ]
}

resource postgresAllowAzure 'Microsoft.DBforPostgreSQL/flexibleServers/firewallRules@2025-08-01' = {
  parent: postgres
  name: 'AllowAllAzureServicesAndResourcesWithinAzureIps'
  properties: {
    startIpAddress: '0.0.0.0'
    endIpAddress: '0.0.0.0'
  }
  dependsOn: [
    postgresDatabaseResource
  ]
}

resource environment 'Microsoft.App/managedEnvironments@2025-07-01' = {
  name: '${name}-env'
  location: location
  properties: {}
}

resource api 'Microsoft.App/containerApps@2025-07-01' = {
  name: '${name}-api'
  location: location
  properties: {
    managedEnvironmentId: environment.id
    configuration: {
      activeRevisionsMode: 'Single'
      ingress: {
        external: true
        targetPort: 8000
        transport: 'auto'
        allowInsecure: false
      }
      registries: [
        {
          server: 'docker.io'
          username: dockerHubUsername
          passwordSecretRef: 'dockerhub-token'
        }
      ]
      secrets: [
        {
          name: 'dockerhub-token'
          value: dockerHubToken
        }
        {
          name: 'django-secret-key'
          value: djangoSecretKey
        }
        {
          name: 'postgres-password'
          value: postgresAdminPassword
        }
      ]
    }
    template: {
      containers: [
        {
          name: 'api'
          image: image
          resources: {
            cpu: json('0.5')
            memory: '1Gi'
          }
          env: [
            {
              name: 'DJANGO_SECRET_KEY'
              secretRef: 'django-secret-key'
            }
            {
              name: 'DJANGO_ALLOWED_HOSTS'
              value: '${name}-api.${environment.properties.defaultDomain}'
            }
            {
              name: 'POSTGRES_DB'
              value: postgresDatabase
            }
            {
              name: 'POSTGRES_USER'
              value: postgresAdminLogin
            }
            {
              name: 'POSTGRES_PASSWORD'
              secretRef: 'postgres-password'
            }
            {
              name: 'POSTGRES_HOST'
              value: postgres.properties.fullyQualifiedDomainName
            }
            {
              name: 'POSTGRES_PORT'
              value: '5432'
            }
            {
              name: 'POSTGRES_SSLMODE'
              value: 'require'
            }
            {
              name: 'CLINIC_TIMEZONE'
              value: clinicTimezone
            }
            {
              name: 'BOOKING_MIN_LEAD_MINUTES'
              value: string(bookingMinLeadMinutes)
            }
          ]
        }
      ]
      scale: {
        minReplicas: minReplicas
        maxReplicas: maxReplicas
      }
    }
  }
  dependsOn: [
    postgresAllowAzure
  ]
}

output apiUrl string = 'https://${api.properties.configuration.ingress.fqdn}'
