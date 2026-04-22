# GraphQL API Guide

This guide explains how to use the GraphQL API for PR-Agent.

## Table of Contents

- [Overview](#overview)
- [Getting Started](#getting-started)
- [Schema](#schema)
- [Queries](#queries)
- [Mutations](#mutations)
- [Examples](#examples)
- [Best Practices](#best-practices)

## Overview

PR-Agent provides a GraphQL API alongside the REST API, offering:

- **Flexible queries**: Request exactly the data you need
- **Single endpoint**: All operations through `/graphql`
- **Type safety**: Strongly typed schema
- **Introspection**: Self-documenting API
- **Efficient**: Reduce over-fetching and under-fetching

### GraphQL vs REST

| Feature | GraphQL | REST |
|---------|---------|------|
| Endpoints | Single `/graphql` | Multiple endpoints |
| Data fetching | Request specific fields | Fixed response structure |
| Multiple resources | Single request | Multiple requests |
| Versioning | Schema evolution | URL versioning |

## Getting Started

### Accessing the API

The GraphQL API is available at:

```
POST http://localhost:8080/graphql
```

### GraphQL Playground

Access the interactive GraphQL playground at:

```
http://localhost:8080/graphql
```

The playground provides:
- Schema documentation
- Query autocomplete
- Query execution
- Response visualization

### Authentication

Include your JWT token in the Authorization header:

```bash
curl -X POST http://localhost:8080/graphql \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query": "{ repositories { id name } }"}'
```

## Schema

### Types

#### Repository

```graphql
type Repository {
  id: Int!
  url: String!
  name: String!
  enabled: Boolean!
  lastReview: DateTime
  totalReviews: Int!
}
```

#### Review

```graphql
type Review {
  id: Int!
  repositoryId: Int!
  prNumber: Int!
  status: String!
  createdAt: DateTime!
  completedAt: DateTime
  result: String
}
```

#### Prompt

```graphql
type Prompt {
  id: Int!
  name: String!
  content: String!
  createdAt: DateTime!
  updatedAt: DateTime
}
```

#### User

```graphql
type User {
  id: Int!
  username: String!
  email: String
  role: String!
  createdAt: DateTime!
}
```

#### Plugin

```graphql
type Plugin {
  name: String!
  version: String!
  description: String!
  author: String!
  enabled: Boolean!
}
```

#### AnalyticsMetrics

```graphql
type AnalyticsMetrics {
  totalReviews: Int!
  avgReviewTime: Float!
  reviewsByStatus: String!
  topRepositories: String!
}
```

### Input Types

#### RepositoryInput

```graphql
input RepositoryInput {
  url: String!
  name: String!
  enabled: Boolean = true
}
```

#### PromptInput

```graphql
input PromptInput {
  name: String!
  content: String!
}
```

#### ReviewFilter

```graphql
input ReviewFilter {
  repositoryId: Int
  status: String
  prNumber: Int
  startDate: DateTime
  endDate: DateTime
}
```

## Queries

### List Repositories

```graphql
query {
  repositories(limit: 10, offset: 0) {
    id
    name
    url
    enabled
    totalReviews
    lastReview
  }
}
```

### Get Repository by ID

```graphql
query {
  repository(id: 1) {
    id
    name
    url
    enabled
    totalReviews
  }
}
```

### List Reviews

```graphql
query {
  reviews(limit: 20, offset: 0) {
    id
    repositoryId
    prNumber
    status
    createdAt
    completedAt
    result
  }
}
```

### Filter Reviews

```graphql
query {
  reviews(
    filter: {
      repositoryId: 1
      status: "completed"
    }
    limit: 10
  ) {
    id
    prNumber
    status
    createdAt
  }
}
```

### Get Review by ID

```graphql
query {
  review(id: 1) {
    id
    repositoryId
    prNumber
    status
    result
  }
}
```

### List Prompts

```graphql
query {
  prompts(limit: 10) {
    id
    name
    content
    createdAt
    updatedAt
  }
}
```

### Get Prompt by ID

```graphql
query {
  prompt(id: 1) {
    id
    name
    content
  }
}
```

### List Users

```graphql
query {
  users(limit: 10) {
    id
    username
    email
    role
    createdAt
  }
}
```

### Get Audit Logs

```graphql
query {
  auditLogs(
    userId: "user123"
    eventType: "USER_LOGIN"
    limit: 50
  ) {
    id
    eventType
    userId
    severity
    timestamp
    details
  }
}
```

### Get Analytics

```graphql
query {
  analytics(
    startDate: "2024-01-01T00:00:00Z"
    endDate: "2024-12-31T23:59:59Z"
  ) {
    totalReviews
    avgReviewTime
    reviewsByStatus
    topRepositories
  }
}
```

### List Plugins

```graphql
query {
  plugins {
    name
    version
    description
    author
    enabled
  }
}
```

## Mutations

### Create Repository

```graphql
mutation {
  createRepository(
    input: {
      url: "https://github.com/user/repo"
      name: "my-repo"
      enabled: true
    }
  ) {
    id
    name
    url
    enabled
  }
}
```

### Update Repository

```graphql
mutation {
  updateRepository(
    id: 1
    input: {
      url: "https://github.com/user/repo"
      name: "updated-repo"
      enabled: false
    }
  ) {
    id
    name
    enabled
  }
}
```

### Delete Repository

```graphql
mutation {
  deleteRepository(id: 1)
}
```

### Create Prompt

```graphql
mutation {
  createPrompt(
    input: {
      name: "custom-review"
      content: "Review this PR carefully..."
    }
  ) {
    id
    name
    content
    createdAt
  }
}
```

### Update Prompt

```graphql
mutation {
  updatePrompt(
    id: 1
    input: {
      name: "updated-prompt"
      content: "Updated content..."
    }
  ) {
    id
    name
    content
    updatedAt
  }
}
```

### Delete Prompt

```graphql
mutation {
  deletePrompt(id: 1)
}
```

## Examples

### Complex Query with Nested Data

```graphql
query {
  repositories(limit: 5) {
    id
    name
    url
    enabled
    totalReviews
  }
  
  reviews(limit: 10, filter: { status: "completed" }) {
    id
    prNumber
    status
    createdAt
  }
  
  analytics {
    totalReviews
    avgReviewTime
  }
}
```

### Query with Variables

```graphql
query GetRepository($id: Int!) {
  repository(id: $id) {
    id
    name
    url
    enabled
    totalReviews
    lastReview
  }
}
```

Variables:
```json
{
  "id": 1
}
```

### Mutation with Variables

```graphql
mutation CreateRepo($input: RepositoryInput!) {
  createRepository(input: $input) {
    id
    name
    url
  }
}
```

Variables:
```json
{
  "input": {
    "url": "https://github.com/user/repo",
    "name": "my-repo",
    "enabled": true
  }
}
```

### Pagination Example

```graphql
query {
  page1: repositories(limit: 10, offset: 0) {
    id
    name
  }
  
  page2: repositories(limit: 10, offset: 10) {
    id
    name
  }
}
```

### Using Fragments

```graphql
fragment RepositoryFields on Repository {
  id
  name
  url
  enabled
  totalReviews
}

query {
  repository(id: 1) {
    ...RepositoryFields
  }
  
  repositories(limit: 5) {
    ...RepositoryFields
  }
}
```

## Best Practices

### 1. Request Only What You Need

❌ Bad:
```graphql
query {
  repositories {
    id
    name
    url
    enabled
    totalReviews
    lastReview
  }
}
```

✅ Good:
```graphql
query {
  repositories {
    id
    name
  }
}
```

### 2. Use Variables for Dynamic Values

❌ Bad:
```graphql
query {
  repository(id: 1) {
    name
  }
}
```

✅ Good:
```graphql
query GetRepo($id: Int!) {
  repository(id: $id) {
    name
  }
}
```

### 3. Use Fragments for Reusable Fields

❌ Bad:
```graphql
query {
  repo1: repository(id: 1) {
    id
    name
    url
  }
  repo2: repository(id: 2) {
    id
    name
    url
  }
}
```

✅ Good:
```graphql
fragment RepoInfo on Repository {
  id
  name
  url
}

query {
  repo1: repository(id: 1) {
    ...RepoInfo
  }
  repo2: repository(id: 2) {
    ...RepoInfo
  }
}
```

### 4. Handle Errors Properly

```javascript
const response = await fetch('/graphql', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${token}`
  },
  body: JSON.stringify({ query })
});

const result = await response.json();

if (result.errors) {
  console.error('GraphQL errors:', result.errors);
  // Handle errors
}

const data = result.data;
// Use data
```

### 5. Use Pagination

```graphql
query {
  repositories(limit: 20, offset: 0) {
    id
    name
  }
}
```

### 6. Optimize Query Depth

Avoid deeply nested queries that can impact performance:

❌ Bad:
```graphql
query {
  repositories {
    reviews {
      repository {
        reviews {
          # Too deep!
        }
      }
    }
  }
}
```

## Client Libraries

### JavaScript/TypeScript

```bash
npm install graphql-request
```

```typescript
import { GraphQLClient } from 'graphql-request';

const client = new GraphQLClient('http://localhost:8080/graphql', {
  headers: {
    Authorization: `Bearer ${token}`
  }
});

const query = `
  query {
    repositories {
      id
      name
    }
  }
`;

const data = await client.request(query);
```

### Python

```bash
pip install gql[all]
```

```python
from gql import gql, Client
from gql.transport.requests import RequestsHTTPTransport

transport = RequestsHTTPTransport(
    url='http://localhost:8080/graphql',
    headers={'Authorization': f'Bearer {token}'}
)

client = Client(transport=transport, fetch_schema_from_transport=True)

query = gql('''
    query {
        repositories {
            id
            name
        }
    }
''')

result = client.execute(query)
```

### cURL

```bash
curl -X POST http://localhost:8080/graphql \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "{ repositories { id name } }"
  }'
```

## Troubleshooting

### Common Issues

1. **Authentication Error**
   - Ensure JWT token is valid and included in Authorization header
   - Check token expiration

2. **Query Syntax Error**
   - Use GraphQL playground to validate syntax
   - Check field names match schema

3. **Field Not Found**
   - Verify field exists in schema
   - Check spelling and case sensitivity

4. **Performance Issues**
   - Reduce query depth
   - Use pagination
   - Request only needed fields

## Additional Resources

- [GraphQL Official Documentation](https://graphql.org/)
- [Strawberry GraphQL Documentation](https://strawberry.rocks/)
- [GraphQL Best Practices](https://graphql.org/learn/best-practices/)
