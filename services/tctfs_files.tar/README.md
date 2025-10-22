# TCTFS - Tropical Cyclone Threat and Forecast Service

A secure, real-time tropical cyclone tracking and forecasting web application with automated watch/warning zone generation.

## Overview

TCTFS ingests live tropical cyclone data from the University of Wisconsin CIMSS ADT page, processes forecast data from UCAR A-Decks (AP1-AP30 ensemble mean), and generates automated Cyclone Watch/Warning zones. The system features:

- **Real-time tracking** of all active tropical cyclones worldwide
- **Automated forecast** generation using AP1-AP30 ensemble mean
- **Watch/Warning zones** algorithmically derived from intensity, forward speed, and wind radii
- **Interactive maps** with beautiful visualizations (past/present/future tracks at 50% opacity for forecasts)
- **User alerts** via email for storm updates and zone changes
- **Complete archive** of historical systems with replay capability

## Key Features

### For Users
- Live dashboard with all active systems
- Per-storm interactive maps with time controls
- Automated watch/warning zones
- Email subscription & alerts (immediate or digest mode)
- Archive browsing and data export

### For Administrators
- Storm re-ingestion and forecast rebuild tools
- Zone generation parameter tuning
- User management with RBAC
- System health monitoring
- Audit logging

## Tech Stack

- **Backend**: Python 3.12, Flask, SQLAlchemy
- **Database**: PostgreSQL 15+ with PostGIS
- **Task Queue**: Celery + Redis
- **Frontend**: Jinja2 templates + MapLibre GL JS
- **Real-time**: Flask-SocketIO (WebSockets)
- **Security**: bcrypt, TOTP 2FA, CSRF protection, secure headers

## Quick Start

### Prerequisites
- Python 3.12+
- PostgreSQL 15+ with PostGIS extension
- Redis 7+
- Node.js 18+ (for frontend tooling, optional)

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/tctfs.git
   cd tctfs
   ```

2. **Create virtual environment**
   ```bash
   python3.12 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment**
   ```bash
   cp .env.example .env
   # Edit .env with your database credentials, email settings, etc.
   ```

5. **Initialize database**
   ```bash
   # Create PostgreSQL database with PostGIS
   createdb tctfs_db
   psql tctfs_db -c "CREATE EXTENSION postgis;"
   
   # Run migrations
   flask db upgrade
   ```

6. **Create admin user**
   ```bash
   python manage.py create-admin --email admin@example.com --password yourpassword
   ```

7. **Run the application**
   
   Terminal 1 - Web server:
   ```bash
   python wsgi.py
   ```
   
   Terminal 2 - Celery worker:
   ```bash
   celery -A tctfs_app.workers.queue worker --loglevel=info
   ```
   
   Terminal 3 - Celery beat (scheduler):
   ```bash
   celery -A tctfs_app.workers.queue beat --loglevel=info
   ```

8. **Access the application**
   - Open browser to `http://localhost:5001`
   - Login with admin credentials

## Docker Deployment

```bash
docker-compose up -d
```

See `docker-compose.yml` for configuration options.

## Project Structure

```
tctfs/
├── tctfs_app/              # Main application package
│   ├── models/             # SQLAlchemy models (Storm, Advisory, User, etc.)
│   ├── blueprints/         # Flask blueprints (web + API routes)
│   ├── services/           # Business logic (ingest, forecast, zones, alerts)
│   ├── workers/            # Celery tasks for background processing
│   ├── templates/          # Jinja2 HTML templates
│   └── static/             # CSS, JS, images
├── alembic/                # Database migrations
├── tests/                  # Unit, integration, and UI tests
├── docs/                   # Documentation
├── scripts/                # Utility scripts
└── ops/                    # Operations runbooks
```

## Data Sources

### Primary Sources
1. **CIMSS ADT** (https://tropic.ssec.wisc.edu/real-time/adt/adt.html)
   - Real-time storm discovery
   - Historical observations from *-list.txt files

2. **UCAR A-Decks** (http://hurricanes.ral.ucar.edu/repository/data/adecks_open/)
   - Ensemble forecast data (AP1-AP30 members)
   - Reduced to single mean forecast for display

### Data Processing
- **History Files**: Parsed with basin-specific adapters, robust error handling
- **Forecasts**: AP1-AP30 members temporally aligned, position/intensity averaged
- **Future Path**: Always rendered at 50% opacity per spec

## Configuration

Key environment variables in `.env`:

```bash
# Flask
SECRET_KEY=your-secret-key-here
FLASK_ENV=production

# Database
SQLALCHEMY_DATABASE_URI=postgresql://user:pass@localhost:5432/tctfs_db

# Redis
REDIS_URL=redis://localhost:6379/0

# Email
MAIL_SERVER=smtp.office365.com
MAIL_USERNAME=your-email@example.com
MAIL_PASSWORD=your-password

# Polling intervals (minutes)
CIMSS_POLL_INTERVAL=10
ADECK_POLL_INTERVAL=15
```

## API Endpoints

### Public API
- `GET /api/storms` - List all storms (with filters)
- `GET /api/storms/{id}` - Storm details
- `GET /api/storms/{id}/track` - Historical track
- `GET /api/storms/{id}/forecast` - AP-mean forecast (future path)
- `GET /api/storms/{id}/zones` - Watch/warning polygons

### Authentication
- `POST /api/auth/login` - Login
- `POST /api/auth/logout` - Logout
- `POST /api/auth/totp/verify` - 2FA verification

### WebSocket
- `ws://localhost:5001/ws/live` - Real-time updates (new advisories, forecasts, zones)

## Testing

```bash
# Run all tests
pytest

# With coverage
pytest --cov=tctfs_app --cov-report=html

# Specific test suite
pytest tests/unit/
pytest tests/integration/
```

## Security Features

- HTTPS enforced (production)
- HSTS, CSP, and security headers
- CSRF protection on all forms
- bcrypt password hashing
- TOTP 2FA for admin accounts
- Rate limiting on login and API
- Session timeout and IP pinning
- Audit logging for admin actions

## Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open Pull Request

## License

MIT License - see LICENSE file for details

## Support

- Documentation: https://docs.tctfs.example.com
- Issues: https://github.com/yourusername/tctfs/issues
- Email: support@tctfs.example.com

## Acknowledgments

- University of Wisconsin CIMSS for ADT data
- UCAR for A-Deck ensemble forecasts
- MapLibre GL JS for mapping library
- Flask and the Python community

---

**Status**: Phase 1 Complete (Ingest & Live Map)  
**Next**: Phase 2 - Forecast Integration & Zone Refinement
