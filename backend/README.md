# VerificAI Backend

Backend API for the VerificAI Code Quality System - an AI-powered code analysis platform for QA teams.

## 🚀 Features

- **User Management**: Complete user authentication, authorization, and profile management
- **Prompt System**: Create, manage, and test AI prompts for code analysis
- **Code Analysis**: Submit code for AI-powered quality analysis
- **Security**: JWT-based authentication, rate limiting, and input validation
- **Scalability**: PostgreSQL + Redis with connection pooling
- **Monitoring**: Comprehensive logging and health checks
- **Testing**: 85%+ test coverage with pytest
- **Deployment**: Docker and Kubernetes ready

## 📋 Prerequisites

- Python 3.11+
- PostgreSQL 15.0+
- Redis 7.0+
- Docker (optional)
- Kubernetes (optional)

## 🛠️ Installation

### Local Development

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd verificAI-code/backend
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   pip install -r requirements-dev.txt  # For development
   ```

4. **Set up environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

5. **Initialize database**
   ```bash
   # Create database and run migrations
   alembic upgrade head
   ```

6. **Start the application**
   ```bash
   uvicorn app.main:app --reload
   ```

### Docker Development

1. **Start services**
   ```bash
   docker-compose up -d
   ```

2. **Run migrations**
   ```bash
   docker-compose exec api alembic upgrade head
   ```

3. **Access the API**
   - API: http://localhost:8000
   - Documentation: http://localhost:8000/docs
   - Health: http://localhost:8000/health

## 🔧 Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection string | `postgresql://verificai:verificai123@localhost:5432/verificai` |
| `REDIS_URL` | Redis connection string | `redis://localhost:6379` |
| `SECRET_KEY` | Application secret key | `your-secret-key-here` |
| `JWT_SECRET_KEY` | JWT secret key | `your-jwt-secret-key` |
| `DEBUG` | Debug mode | `false` |
| `ENVIRONMENT` | Environment | `development` |
| `LOG_LEVEL` | Logging level | `INFO` |
| `HOST` | Bind host | `0.0.0.0` |
| `PORT` | Bind port | `8000` |

### Database Configuration

```python
DATABASE_POOL_SIZE = 20
DATABASE_MAX_OVERFLOW = 10
DATABASE_POOL_TIMEOUT = 30
DATABASE_POOL_RECYCLE = 3600
```

### Security Configuration

```python
# Rate limiting
RATE_LIMIT_REQUESTS_PER_MINUTE = 60
RATE_LIMIT_BURST = 10

# CORS settings
BACKEND_CORS_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:5173"
]
```

## 🧪 Testing

### Run Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test categories
pytest -m unit
pytest -m integration
pytest -m api

# Run tests with verbose output
pytest -v
```

### Test Coverage

- Unit tests: 85%+ coverage required
- Integration tests: API endpoint testing
- E2E tests: Full workflow testing

## 📊 API Documentation

### Interactive Documentation

- **Swagger UI**: http://localhost:8000/api/v1/docs
- **ReDoc**: http://localhost:8000/api/v1/redoc
- **OpenAPI Schema**: http://localhost:8000/api/v1/openapi.json

### Authentication

All API endpoints (except `/auth/*`) require authentication:

```bash
# Get token
curl -X POST "http://localhost:8000/api/v1/auth/login" \
     -H "Content-Type: application/x-www-form-urlencoded" \
     -d "username=your_username&password=your_password"

# Use token
curl -X GET "http://localhost:8000/api/v1/users/me" \
     -H "Authorization: Bearer YOUR_TOKEN"
```

## 🚀 Deployment

### Docker Deployment

1. **Build and push image**
   ```bash
   ./deploy.sh build
   ./deploy.sh push
   ```

2. **Deploy to production**
   ```bash
   ./deploy.sh deploy
   ```

3. **Rollback deployment**
   ```bash
   ./deploy.sh rollback v1.0.0
   ```

### Kubernetes Deployment

1. **Apply manifests**
   ```bash
   kubectl apply -f k8s/namespace.yaml
   kubectl apply -f k8s/configmap.yaml
   kubectl apply -f k8s/secret.yaml
   kubectl apply -f k8s/
   ```

2. **Check deployment status**
   ```bash
   kubectl get pods -n verificai
   kubectl get services -n verificai
   kubectl get ingress -n verificai
   ```

### Monitoring Setup

The application includes comprehensive monitoring:

- **Prometheus**: Metrics collection
- **Grafana**: Dashboards and visualization
- **AlertManager**: Alert management
- **Health Checks**: `/health` and `/ready` endpoints

## 🔒 Security Features

### Authentication & Authorization

- JWT-based authentication
- Role-based access control (RBAC)
- Password hashing with bcrypt
- API key support
- Rate limiting

### Input Validation

- Pydantic schema validation
- SQL injection prevention
- XSS protection
- File upload validation

### Security Headers

- Content Security Policy (CSP)
- XSS Protection
- HSTS
- CORS configuration

## 📈 Monitoring & Logging

### Structured Logging

```json
{
  "timestamp": "2024-01-01T00:00:00Z",
  "level": "INFO",
  "logger": "verificai",
  "message": "User login successful",
  "user_id": 123,
  "ip_address": "192.168.1.1"
}
```

### Metrics

- HTTP request rates and response times
- Database connection metrics
- Redis performance metrics
- Error rates and status codes
- Custom business metrics

### Health Checks

- `/health` - Basic health check
- `/ready` - Readiness probe with dependencies

## 🏗️ Architecture

### Layered Architecture

```
┌─────────────────┐
│   API Layer     │ FastAPI + Pydantic
├─────────────────┤
│ Business Logic │ Services + Use Cases
├─────────────────┤
│  Data Access   │ SQLAlchemy + ORM
├─────────────────┤
│ Infrastructure │ PostgreSQL + Redis
└─────────────────┘
```

### Key Components

- **FastAPI**: Modern, fast web framework
- **SQLAlchemy**: Python SQL toolkit and ORM
- **Alembic**: Database migration tool
- **Pydantic**: Data validation using Python type annotations
- **Redis**: Caching and session management
- **PostgreSQL**: Primary database

## 🤝 Contributing

### Development Workflow

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Ensure all tests pass (85%+ coverage)
6. Submit a pull request

### Code Style

- Follow PEP 8 guidelines
- Use type hints
- Write comprehensive docstrings
- Keep functions small and focused
- Use meaningful variable names

### Commit Messages

```
type(scope): description

# Examples
feat(auth): add JWT token refresh
fix(api): handle database connection errors
docs(readme): update installation instructions
test(auth): add unit tests for user service
```

## 📝 API Endpoints

### Authentication

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/auth/register` | Register new user |
| POST | `/api/v1/auth/login` | User login |
| GET | `/api/v1/auth/me` | Get current user |
| POST | `/api/v1/auth/refresh` | Refresh JWT token |

### Users

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/users/me` | Get user profile |
| PUT | `/api/v1/users/me` | Update user profile |
| GET | `/api/v1/users/` | List users (admin) |
| GET | `/api/v1/users/{id}` | Get user by ID (admin) |

### Prompts

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/prompts/` | Create prompt |
| GET | `/api/v1/prompts/` | List prompts |
| GET | `/api/v1/prompts/{id}` | Get prompt by ID |
| PUT | `/api/v1/prompts/{id}` | Update prompt |
| DELETE | `/api/v1/prompts/{id}` | Delete prompt |

### Analysis

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/analysis/` | Create analysis |
| GET | `/api/v1/analysis/` | List analyses |
| GET | `/api/v1/analysis/{id}` | Get analysis by ID |
| GET | `/api/v1/analysis/{id}/result` | Get analysis result |

## 🔧 Troubleshooting

### Common Issues

**Database Connection Issues**
```bash
# Check PostgreSQL status
sudo systemctl status postgresql

# Test connection
psql -h localhost -U verificai -d verificai
```

**Redis Connection Issues**
```bash
# Check Redis status
sudo systemctl status redis

# Test connection
redis-cli ping
```

**Migration Issues**
```bash
# Check migration status
alembic current
alembic history

# Rollback migration
alembic downgrade -1
```

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- FastAPI team for the excellent framework
- SQLAlchemy developers
- OpenAI and Anthropic for AI models
- The Python community

## 📞 Support

For support and questions:

- Create an issue on GitHub
- Check the documentation
- Review existing issues and discussions

---

**Note**: This is the backend component of the VerificAI Code Quality System. Please refer to the main repository for full system documentation.