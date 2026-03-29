# Route Master Africa - Test Suite Documentation

## Overview

This directory contains comprehensive unit, integration, and functional tests for the Route Master Africa logistics platform. The test suite uses **pytest** as the testing framework with mocking for external dependencies.

## Test Structure

```
tests/
├── __init__.py                 # Test package initialization
├── conftest.py                 # Pytest fixtures and configuration
├── test_authentication.py       # Authentication and decorator tests
├── test_trader.py              # Trader module tests
├── test_carrier.py             # Carrier module tests
├── test_db_pool.py             # Database pool and connection tests
├── test_integration.py          # End-to-end workflow tests
└── test_flask_app.py           # Flask app and route tests
```

## Test Coverage

### 1. Authentication Tests (`test_authentication.py`)

- **Token Hashing**: Validates password reset token generation and consistency
- **Email Sending**: Tests password reset email notifications
- **Login Decorator**: Validates `@login_required` access control
- **Carrier Decorator**: Validates `@carrier_required` authorization
- **Email Validation**: Tests email format validation
- **Password Strength**: Tests password strength requirements

**Test Count**: 10 tests

### 2. Trader Module Tests (`test_trader.py`)

- **getRoutes()**: Tests route retrieval with database error handling
- **getCarriers()**: Tests carrier listing with filters and limits
- **getContainerById()**: Tests individual container detail retrieval
- **book_container()**: Tests shipment creation and booking validation
  - Validates empty items rejection
  - Validates item array length matching
  - Validates weight/CBM numeric validation
  - Validates negative weight rejection

**Test Count**: 13 tests

### 3. Carrier Module Tests (`test_carrier.py`)

- **create_container()**: Tests container creation workflow
  - Success path with database persistence
  - Error handling when carrier profile not found
  - Database error recovery
- **show_carrier_containers()**: Tests carrier's container listing
- **get_shipment_items()**: Tests shipment item retrieval
- **Status Constants**: Tests allowed status values validation
- **get_carrier_container_details_payload()**: Tests detailed container retrieval

**Test Count**: 14 tests

### 4. Database Pool Tests (`test_db_pool.py`)

- **Pool Initialization**: Validates connection pool configuration
- **Connection Retrieval**: Tests successful connection acquisition
- **Retry Logic**: Tests automatic retry with exponential backoff
- **Retry Exhaustion**: Tests error when retries exhausted
- **Pool Size Configuration**: Tests environment variable configuration
- **Minimum Pool Size**: Validates minimum pool size enforcement

**Test Count**: 9 tests

### 5. Integration Tests (`test_integration.py`)

- **Trader Onboarding**: End-to-end trader registration to booking
- **Carrier Onboarding**: End-to-end carrier registration to container publication
- **Payment Workflow**: Shipment creation to payment completion
- **Notification Workflow**: Booking event notification system
- **Concurrent Bookings**: Multiple traders booking same container
- **Error Recovery**: Rollback and retry scenarios
- **Data Validation**: Cross-module validation scenarios
  - Weight summation
  - Container capacity checking
  - Distance validation
  - Pricing calculation

**Test Count**: 13 tests

### 6. Flask App Tests (`test_flask_app.py`)

- **App Initialization**: Tests Flask setup and configuration
- **Home Route**: Tests index page rendering
- **Login Route**: Tests login GET/POST handlers
- **Flash Messages**: Tests centralized alert handling
- **Decorators**: Tests decorator effectiveness with routes
- **Session Management**: Tests session creation/cleanup
- **Error Handling**: Tests error response handling
- **Response Formats**: Tests HTML/JSON/redirect responses
- **Security**: Tests CSRF and cookie security
- **Rate Limiting**: Tests rate limits on sensitive endpoints

**Test Count**: 26 tests

## Current Verified Results (2026-03-29)

Latest executed test runs produced the following results:

- **Unit suite** (`test_authentication.py`, `test_trader.py`, `test_carrier.py`, `test_db_pool.py`): **46 passed**
- **Validation-focused subset**: **13 passed**, **72 deselected**
- **Integration suite** (`test_integration.py`): **13 passed**
- **Functional/System test file** (`test_flask_app.py`): **26 passed**

Generated artifacts are available in `test_results/`:

- `unit.txt`, `unit.xml`
- `validation.txt`, `validation.xml`
- `integration.txt`, `integration.xml`
- `functional.txt`, `functional.xml`
- `acceptance_report.md`

## Running the Tests

### Installation

```bash
# Install test dependencies
pip install -r test-requirements.txt
```

### Run All Tests

```bash
# Run entire test suite with verbose output
pytest

# Run with coverage report
pytest --cov=. --cov-report=html
```

### Run Specific Test Categories

```bash
# Run only unit tests
pytest tests/test_authentication.py tests/test_trader.py tests/test_carrier.py tests/test_db_pool.py

# Run only integration tests
pytest tests/test_integration.py

# Run only Flask app tests
pytest tests/test_flask_app.py

# Run tests for specific module
pytest tests/test_trader.py -v

# Run specific test class
pytest tests/test_trader.py::TestGetCarriers -v

# Run specific test function
pytest tests/test_trader.py::TestGetCarriers::test_get_carriers_success -v
```

### Run with Markers

```bash
# Run only unit tests
pytest -m unit

# Run only integration tests
pytest -m integration

# Run only database tests
pytest -m database

# Run only authentication tests
pytest -m auth

# Run only trader tests
pytest -m trader

# Run only carrier tests
pytest -m carrier
```

### Run with Coverage

```bash
# Generate coverage report
pytest --cov=. --cov-report=html --cov-report=term-missing

# View HTML coverage report
open htmlcov/index.html
```

### Run with Specific Options

```bash
# Stop on first failure
pytest -x

# Show print statements
pytest -s

# Run last failed tests
pytest --lf

# Run failed tests first, then others
pytest --ff

# Full traceback
pytest -vv --tb=long

# Quiet output
pytest -q
```

## Test Fixtures

The test suite provides reusable fixtures in `conftest.py`:

### Database Fixtures

- `mock_db_connection`: Mocked database connection
- `mock_db_cursor`: Mocked database cursor
- `patched_get_connection`: Global patch for database connections

### Sample Data Fixtures

- `sample_user_trader`: Trader user object
- `sample_user_carrier`: Carrier user object
- `sample_carrier_profile`: Carrier company profile
- `sample_route`: Sample shipping route
- `sample_container`: Sample shipping container
- `sample_shipment`: Sample shipment order
- `sample_booking`: Sample booking record
- `sample_payment`: Sample payment transaction

### Flask Fixtures

- `flask_app`: Configured Flask test app
- `flask_client`: Flask test client for requests
- `flask_request_context`: Flask request context manager
- `session_with_trader`: Authenticated trader session
- `session_with_carrier`: Authenticated carrier session

### Validation Fixtures

- `assert_valid_email_format`: Email validation function
- `assert_password_strength`: Password strength validator
- `reset_token`: Generate test password reset token
- `valid_container_status`: Valid container status list
- `valid_shipment_status`: Valid shipment status list

## Mocking Strategy

All tests use `unittest.mock` to isolate units under test:

- **Database Connections**: Mocked to avoid real database calls
- **External APIs**: Mocked payment gateway and email services
- **File I/O**: Mocked template rendering and file operations
- **Environment Variables**: Patched for test configuration

Additionally, the test harness stubs MySQL pool creation during tests so importing application modules does not open live DB connections.

## Security and Credential Hygiene

- Tests and test fixtures should never contain real secrets (passwords, API keys, tokens).
- Keep `.env` out of version control and never paste its values into test files or reports.
- Generated XML artifacts may contain host metadata (for example, local machine hostname). This is not a credential, but avoid publishing artifacts publicly without review.
- Before sharing reports externally, search outputs for sensitive patterns:

```bash
grep -RinE "password|secret|api[_-]?key|token" test_results tests
```

## Test Data Validation

Key validation tested across modules:

| Validation         | Test                                   | Expected                                         |
| ------------------ | -------------------------------------- | ------------------------------------------------ |
| Email format       | `test_validate_email_format`           | `user@example.com` valid, `@example.com` invalid |
| Weight bounds      | `test_book_container_negative_weight`  | Rejects weight <= 0                              |
| Item arrays        | `test_book_container_mismatched_items` | All arrays same length                           |
| Shipment items     | `test_book_container_invalid_items`    | Rejects empty items                              |
| Container capacity | `test_container_capacity_validation`   | Checks weight & CBM limits                       |
| Status values      | `test_status_validation`               | Only allows defined statuses                     |

## Database Transaction Testing

Tests verify transaction integrity:

- **Commit on Success**: `test_create_container_success`
- **Rollback on Failure**: `test_rollback_on_booking_failure`
- **Connection Cleanup**: All tests verify cursor/connection closure

## Continuous Integration

To integrate with CI/CD pipeline:

```bash
# In your CI configuration (GitHub Actions, GitLab CI, etc.)
pytest --cov=. --cov-report=xml --junit-xml=test-results.xml
```

## Coverage Goals

Target test coverage by module:

| Module              | Target Coverage | Current |
| ------------------- | --------------- | ------- |
| `authentication.py` | 95%             | -       |
| `trader.py`         | 90%             | -       |
| `carrier.py`        | 90%             | -       |
| `db_pool.py`        | 95%             | -       |
| `main.py` (routes)  | 85%             | -       |

## Common Test Patterns

### Testing Database Operations

```python
@patch('trader.get_connection_with_retry')
def test_function(mock_get_connection):
    mock_cursor = Mock()
    mock_connection = Mock()
    mock_connection.cursor.return_value = mock_cursor
    mock_get_connection.return_value = mock_connection

    # Set up mock responses
    mock_cursor.fetchall.return_value = [expected_data]

    # Call function
    result = function_under_test()

    # Assert results
    assert result == [expected_data]
```

### Testing Error Handling

```python
@patch('module.get_connection_with_retry')
def test_error_handling(mock_get_connection):
    mock_cursor = Mock()
    mock_connection = Mock()
    mock_cursor.execute.side_effect = mysql.connector.Error("DB Error")

    result = function_under_test()

    assert result[0] is False
    assert "Error" in result[1]
```

### Testing Validation

```python
def test_validation():
    result = invalid_input_function()
    assert result[0] is False
    assert result[2] == 400  # HTTP status code
```

## Troubleshooting

### Import Errors

```bash
# Ensure project root is in Python path
export PYTHONPATH="${PYTHONPATH}:/path/to/project"
pytest
```

### Database Connection Mocking Issues

- Ensure `get_connection_with_retry` is properly patched
- Verify cursor creation and method mocking

### Flask Test Context Issues

```python
# Use provided fixture
def test_route(flask_client):
    response = flask_client.get('/')
    assert response.status_code == 200
```

## Adding New Tests

1. **Identify module**: Which module to test?
2. **Create test class**: Group related tests in classes
3. **Use fixtures**: Leverage existing fixtures from `conftest.py`
4. **Mock externals**: Mock database, APIs, files
5. **Test both paths**: Success and error scenarios
6. **Update docs**: Add test description to this README

## Best Practices

**DO:**

- Use descriptive test names: `test_function_with_condition_returns_expected`
- Test one thing per test
- Use fixtures for setup
- Mock external dependencies
- Test error paths
- Clean up resources (automatic with mocks)

**DON'T:**

- Use test database for unit tests
- Make network calls in tests
- Test third-party libraries
- Create test interdependencies
- Ignore error cases
- Skip assertions with `pass`

## Contributing

When adding new tests:

1. Follow existing naming conventions
2. Use appropriate markers (`@pytest.mark.unit`, `@pytest.mark.integration`)
3. Document complex test scenarios
4. Maintain test isolation
5. Run full suite before submitting: `pytest`

---

**Last Updated**: 2026-03-29
**Verified On**: Python 3.13.3, pytest 9.0.2
