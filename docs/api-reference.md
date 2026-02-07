# API Reference

Complete API documentation for Intelligent Support Router.

## Base URL

```
http://localhost:8000/api/v1
```

## Authentication

Currently, the API does not require authentication. For production, implement your own authentication layer.

---

## Tickets

### Create Ticket

Create and process a new support ticket.

```http
POST /tickets
```

**Request Body:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| content | string | Yes | Ticket content/message |
| subject | string | No | Ticket subject |
| customer_email | string | No | Customer email |
| customer_name | string | No | Customer name |
| customer_tier | string | No | Customer tier (free, standard, premium, vip) |
| source | string | No | Ticket source (api, email, zendesk) |
| language | string | No | Language code (tr, en) |
| tags | array | No | Custom tags |
| process_async | boolean | No | Process asynchronously (default: true) |

**Example:**

```bash
curl -X POST http://localhost:8000/api/v1/tickets \
  -H "Content-Type: application/json" \
  -d '{
    "content": "Uygulamanız çalışmıyor",
    "customer_email": "customer@example.com",
    "process_async": false
  }'
```

**Response (201 Created):**

```json
{
  "ticket_id": "uuid",
  "status": "processed",
  "classification": {
    "primary_category": "technical_issue",
    "confidence": 0.92
  },
  "sentiment": {
    "sentiment": "negative",
    "score": -0.6
  },
  "priority": {
    "score": 4,
    "level": "high"
  },
  "routing": {
    "agent_id": "uuid",
    "agent_name": "Mehmet Yılmaz",
    "reason": "skill_match"
  }
}
```

### Get Ticket

```http
GET /tickets/{ticket_id}
```

### List Tickets

```http
GET /tickets
```

**Query Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| page | integer | Page number (default: 1) |
| page_size | integer | Items per page (default: 20, max: 100) |
| status | string | Filter by status |
| category | string | Filter by category |
| priority | integer | Filter by priority (1-5) |
| sentiment | string | Filter by sentiment |
| search | string | Search in content |

### Update Ticket

```http
PATCH /tickets/{ticket_id}
```

### Reassign Ticket

```http
POST /tickets/{ticket_id}/reassign
```

### Escalate Ticket

```http
POST /tickets/{ticket_id}/escalate?reason=VIP%20customer
```

### Resolve Ticket

```http
POST /tickets/{ticket_id}/resolve
```

---

## Agents

### Create Agent

```http
POST /agents
```

### Get Agent

```http
GET /agents/{agent_id}
```

### List Agents

```http
GET /agents
```

### Update Agent

```http
PATCH /agents/{agent_id}
```

### Update Agent Status

```http
PUT /agents/{agent_id}/status
```

**Request Body:**

```json
{
  "status": "online"
}
```

### Get Available Agents

```http
GET /agents/available?category=technical_issue&language=tr
```

---

## Analytics

### Overview

```http
GET /analytics/overview?period_days=30
```

### Category Analytics

```http
GET /analytics/categories?period_days=30
```

### Agent Performance

```http
GET /analytics/performance?period_days=30
```

### Trends

```http
GET /analytics/trends?period_days=30&granularity=day
```

---

## Configuration

### List Categories

```http
GET /config/categories
```

### Create Category

```http
POST /config/categories
```

### Seed Default Categories

```http
POST /config/categories/seed
```

### List Routing Rules

```http
GET /config/routing-rules
```

### Create Routing Rule

```http
POST /config/routing-rules
```

---

## Webhooks

### Zendesk Webhook

```http
POST /webhooks/zendesk
```

### Freshdesk Webhook

```http
POST /webhooks/freshdesk
```

### Generic Webhook

```http
POST /webhooks/generic
```

### Email Webhook

```http
POST /webhooks/email
```

---

## Health

### Basic Health Check

```http
GET /health
```

### Detailed Health Check

```http
GET /health/detailed
```

### Readiness Probe

```http
GET /ready
```

### Liveness Probe

```http
GET /live
```

---

## Error Responses

All errors follow this format:

```json
{
  "detail": "Error message",
  "code": "ERROR_CODE"
}
```

**Common Status Codes:**

| Code | Description |
|------|-------------|
| 400 | Bad Request |
| 404 | Not Found |
| 409 | Conflict |
| 422 | Validation Error |
| 500 | Internal Server Error |
