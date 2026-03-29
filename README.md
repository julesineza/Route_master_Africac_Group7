# Route Master Africa - Cargo Logistics Platform

**Group 7 Project - ALU Foundations project**

## Overview

Route Master Africa is a digital cargo logistics platform designed to streamline the transportation and delivery of goods across Africa. The platform connects **traders** (shippers) with **carriers** (transport companies), providing a centralized system for managing shipments, tracking containers, and optimizing delivery routes.

### Live Deployment

**Visit the live application:** [http://routemasterafrica.julesineza.tech/](http://routemasterafrica.julesineza.tech/)

The application is fully hosted and operational. Local environment keys are not available for development setup—please use the live link above for access and testing.

## Group Members

- **Ineza Jules** - Lead Developer
- **Divine Mutesi** - Backend & Database
- **Esther Mahoro** - Frontend & UI
- **Kellen Mutoni** - Testing & QA
- **Nyiramanzi Igihozo** - Documentation & Integration

## Project Structure

```
├── main.py                          # Flask application entry point
├── carrier.py                       # Carrier module (shipment management)
├── trader.py                        # Trader module (cargo routing)
├── db_pool.py                       # MySQL connection pooling
├── mysql_setup.py                   # Database schema initialization
├── schema.sql                       # Database schema
├── requirements.txt                 # Python dependencies
├── pytest.ini                       # Test configuration
├── templates/                       # HTML templates
│   ├── index.html                   # Landing page
│   ├── login.html                   # User authentication
│   ├── register.html                # User registration
│   ├── trader.html                  # Trader dashboard
│   ├── trader_shipments.html        # Shipment management
│   ├── carrier.html                 # Carrier dashboard
│   ├── carrier_container_details.html
│   ├── pay.html                     # Payment interface
│   ├── forgot_password.html         # Password recovery
│   ├── reset_password.html          # Password reset
│   └── script.js / style.css        # Frontend assets
├── static/                          # Static resources
│   ├── style.css / example.css      # Stylesheets
│   ├── icons/                       # Icon assets
│   └── images/                      # Product & UI images
└── tests/                           # Automated test suite
    ├── test_authentication.py       # Auth workflows
    ├── test_trader.py               # Trader functionality
    ├── test_carrier.py              # Carrier functionality
    ├── test_db_pool.py              # Connection pooling
    ├── test_flask_app.py            # Flask routes & security
    ├── test_integration.py          # End-to-end workflows
    └── conftest.py                  # Test fixtures & configuration
```

## Key Features

### For Traders (Shippers)
- **Cargo Registration**: Upload goods with specifications (weight, dimensions, type)
- **Route Selection**: Browse available carriers and competitive rates
- **Real-time Tracking**: Monitor shipment location and status
- **Payment Integration**: Secure payment processing for shipments
- **Shipment History**: Archive of past bookings and deliveries

### For Carriers (Transport Companies)
- **Container Management**: Create and manage transport containers
- **Booking Management**: Accept/reject shipment requests
- **Route Optimization**: Track active and completed routes
- **Availability Updates**: Set container availability and pricing
- **Document Generation**: Generate invoices and delivery confirmations

### Security & Access Control
- User authentication with role-based access (Trader/Carrier)
- Password reset & recovery workflows
- Session management with secure cookies
- Input validation & SQL injection prevention

## Technology Stack

- **Backend**: Python 3.13.3, Flask web framework
- **Database**: MySQL with connection pooling
- **Frontend**: HTML5, CSS3, JavaScript
- **Testing**: pytest 9.0.2, unittest.mock for unit/integration/functional testing
- **Templating**: Jinja2 for dynamic HTML rendering

## Testing & Quality Assurance

The project includes a comprehensive test suite with **98 passing tests** across four stages:

- **Unit Tests**: 46 tests (authentication, core logic)
- **Validation Tests**: 13 tests (input validation & business rules)
- **Integration Tests**: 13 tests (end-to-end workflows)
- **Functional Tests**: 26 tests (Flask routes & security)

Test execution and detailed test documentation available in [tests/README.md](tests/README.md).

## Environment Configuration

The application requires the following environment variables (configured in `.env`):
- `server_ip`: MySQL server address
- `server_password`: MySQL authentication credential

**Note**: Environment credentials are not provided in this repository for security purposes. The live deployment handles all environment configuration securely.

## Database Schema

The application uses a relational database with the following core entities:
- **Users**: Authentication & role management (Trader/Carrier)
- **Containers**: Transport containers with capacity and pricing
- **Bookings**: Shipment records linking traders and carriers
- **Items**: Cargo items within shipments
- **Routes**: Delivery paths with origin/destination

See [schema.sql](schema.sql) for the complete database schema.

## Deployment

The application is deployed and accessible at:
**[http://routemasterafrica.julesineza.tech/](http://routemasterafrica.julesineza.tech/)**

No local setup is required—simply visit the link to access the live platform.

## For Academic Review

This project submission includes:
- **Chapter 4 Test Evidence**: Comprehensive test reports in `test_results/` directory
  - JUnit XML reports for CI/CD integration
  - Acceptance testing report with sign-off documentation
  - Detailed test execution logs
- **Code Quality**: All tests passing, no security vulnerabilities
- **Documentation**: Complete test README with security hygiene guidelines

## Contact & Support

For questions about this project, contact:
- **Project Lead**: Ineza Jules

---


