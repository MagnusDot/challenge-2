# Reply Challenge API

Strictly typed REST API with Pydantic validation for dataset analysis.

## Features

✅ **Strict Type Validation** - All data validated with Pydantic  
✅ **5 Complete Datasets** - Users, Transactions, Locations, SMS, Emails  
✅ **Docker Ready** - Full Docker Compose setup  
✅ **Auto Documentation** - Swagger UI & ReDoc included  
✅ **Pagination** - All list endpoints support pagination  
✅ **Filtering** - Advanced filters on transactions & locations  
✅ **Statistics** - Summary endpoints for analytics  
✅ **Health Checks** - Built-in monitoring  

## Quick Start

### Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Run API
uvicorn api.main:app --reload

# Or with just
just api-dev
```

### Docker

```bash
# Build and start
docker-compose up -d

# View logs
docker-compose logs -f

# Stop
docker-compose down
```

## API Endpoints

### Users
- `GET /users/` - List all users
- `GET /users/by-iban/{iban}` - Get by IBAN
- `GET /users/by-city/{city}` - Filter by city
- `GET /users/stats` - User statistics

### Transactions
- `GET /transactions/` - List with filters (type, fraud)
- `GET /transactions/{id}` - Get by ID
- `GET /transactions/sender/{id}` - By sender
- `GET /transactions/stats/summary` - Statistics

### Locations
- `GET /locations/` - List all locations
- `GET /locations/biotag/{biotag}` - By biotag
- `GET /locations/stats/summary` - Statistics

### SMS & Emails
- `GET /sms/` - List SMS
- `GET /sms/user/{user_id}` - By user
- `GET /emails/` - List emails

### Global
- `GET /health` - Health check
- `GET /stats` - Global stats
- `GET /docs` - Swagger UI
- `GET /redoc` - ReDoc

## Documentation

📚 **Full documentation**: `docs/API_DOCUMENTATION.md`

🌐 **Interactive docs**: http://localhost:8000/docs (when running)

## Data Models

All models use Pydantic for validation:

- **User**: First/last name, birth year, salary, job, IBAN, residence
- **Transaction**: UUID, sender/recipient, type, amount, location, IBAN, fraud flag
- **Location**: Biotag, datetime, lat/lng coordinates
- **SMS**: User ID, message content
- **Email**: Full RFC 822 email content

## Examples

```bash
# Get users
curl http://localhost:8000/users/

# Get fraud transactions
curl "http://localhost:8000/transactions/?is_fraud=true&limit=50"

# Get user by IBAN
curl http://localhost:8000/users/by-iban/FR7630006...

# Get statistics
curl http://localhost:8000/stats
```

## Tech Stack

- **FastAPI** - Modern Python web framework
- **Pydantic** - Data validation
- **Uvicorn** - ASGI server
- **Docker** - Containerization

## License

MIT



