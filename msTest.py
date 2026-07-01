# Code snippets are only available for the latest version. Current version is 1.x
from azure.identity import DeviceCodeCredential
from msgraph.graph_service_client import GraphServiceClient
# To initialize your graph_client, see https://learn.microsoft.com/en-us/graph/sdks/create-client?from=snippets&tabs=python
scopes = ['User.Read']

# Multi-tenant apps can use "common",
# single-tenant apps must use the tenant ID from the Azure portal
tenant_id = 'common'

# Values from app registration
client_id = '90a811b2-292a-49f3-811a-3fe458b65677'

# azure.identity
credential = DeviceCodeCredential(
    tenant_id=tenant_id,
    client_id=client_id)

graph_client = GraphServiceClient(credential, scopes)
result = graph_client.users.by_user_id('90a811b2-292a-49f3-811a-3fe458b65677').get()