# Expense Tracker API

A REST API for managing personal expenses and tracking a budget, built with FastAPI and Pydantic.

## Features

* Create, list, retrieve, update, and delete expenses
* Filter expenses by category
* Calculate expense summaries and statistics
* Group expenses by category
* Set and retrieve a budget
* Calculate remaining budget and percentage spent
* Validate incoming data using Pydantic
* Store expenses and budget in JSON files
* Load saved data when the application starts
* Log HTTP requests and application events
* Health check and application version endpoints
* Automated tests with pytest

## Requirements

* Python 3.10 or newer
* pip

## Installation

Clone the repository and navigate to the project directory.

Create and activate a virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Install the dependencies:

```bash
python -m pip install -r requirements-dev.txt
```

## Run the application

Start the API server:

```bash
python -m uvicorn app_final:app
```

Open the interactive API documentation:

http://127.0.0.1:8000/docs

## API Endpoints

| Method | Endpoint                 | Description               |
| ------ | ------------------------ | ------------------------- |
| GET    | `/`                      | Welcome message           |
| GET    | `/health`                | Check application status  |
| GET    | `/version`               | Get application version   |
| GET    | `/expenses`              | List expenses             |
| POST   | `/expenses`              | Create an expense         |
| GET    | `/expenses/summary`      | Get expense summary       |
| GET    | `/expenses/stats`        | Get expense statistics    |
| GET    | `/expenses/{expense_id}` | Retrieve an expense by ID |
| PUT    | `/expenses/{expense_id}` | Update an expense         |
| DELETE | `/expenses/{expense_id}` | Delete an expense         |
| GET    | `/budget`                | Get budget information    |
| PUT    | `/budget`                | Update the budget         |

## Example: Create an Expense

Send a POST request to `/expenses` with the following JSON body:

```json
{
  "title": "Groceries",
  "amount": 450.5,
  "category": "Food"
}
```

The API validates the input and returns the created expense with its assigned ID.

## Example: Update the Budget

Send a PUT request to `/budget` with the following JSON body:

```json
{
  "monthly_budget": 40000
}
```

The budget must be greater than zero.

The `GET /budget` endpoint returns the configured budget, total recorded expenses, remaining budget, percentage used, and whether the recorded expenses exceed the budget.

**Note:** The current implementation calculates spending from all expenses stored in the application. It does not yet filter expenses by calendar month.

## Data Storage

The application stores data in JSON files:

* `data/expenses.json` — expense records
* `data/budget.json` — configured budget

The application loads saved data at startup and saves changes to the corresponding files.

The data directory and files are created automatically when needed.

These data files are excluded from Git through `.gitignore` to help prevent personal financial information from being committed accidentally.

## Configuration

* `APP_VERSION` sets the application version. Default: `1.0.0`.
* `EXPENSES_FILE` sets the path to the expense JSON file.

The default expense file is `data/expenses.json`. The budget file is `data/budget.json`.

Environment variables must be set in the environment before starting the application.

## Health Check, Version, and Logs

After starting the application, open these URLs in your browser:

* `http://127.0.0.1:8000/health` — check whether the service is running.
* `http://127.0.0.1:8000/version` — check the application version.
* `http://127.0.0.1:8000/docs` — explore and test API endpoints interactively.

The application logs are written to the terminal where Uvicorn is running. They include application startup and shutdown, HTTP requests, expense and budget operations, and errors.

## Troubleshooting

* **The server does not start:** make sure the virtual environment is activated and dependencies are installed with `python -m pip install -r requirements-dev.txt`.
* **Port 8000 is already in use:** stop the other process using that port or start the application on another port, for example `python -m uvicorn app_final:app --port 8001`.
* **The API returns a validation error:** check the request body and the required fields in `/docs`.
* **Saved data is missing:** check the configured `EXPENSES_FILE` path and the JSON files in the `data` directory.
* **Tests fail:** run `python -m pytest -v` and inspect the error output.

## Run Tests

Run all automated tests:

```bash
python -m pytest -v
```

The tests use temporary files to avoid modifying the application's real expense and budget data.

## License

This project was created for educational purposes.
