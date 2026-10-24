import pytest
from fastapi.testclient import TestClient

import app_final


@pytest.fixture
def client(tmp_path, monkeypatch):
    test_file = tmp_path / "expenses.json"

    monkeypatch.setattr(app_final, "EXPENSES_FILE", test_file)
    monkeypatch.setattr(app_final, "BUDGET_FILE", tmp_path / "budget.json")
    monkeypatch.setattr(app_final, "monthly_budget", 30000.0)

    app_final.expenses.clear()
    app_final.next_expense_id = 1

    with TestClient(app_final.app) as test_client:
        yield test_client

    app_final.expenses.clear()
    app_final.next_expense_id = 1


def test_home(client):
    response = client.get("/")

    assert response.status_code == 200
    assert response.json()["message"] == "Welcome to Expense Tracker API"


def test_health(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_version(client):
    response = client.get("/version")

    assert response.status_code == 200
    assert response.json()["version"] == app_final.APP_VERSION


def test_add_expense(client):
    response = client.post(
        "/expenses",
        json={
            "title": "Продукты",
            "amount": 450.5,
            "category": "Еда",
        },
    )

    assert response.status_code == 201
    assert response.json()["id"] == 1
    assert response.json()["title"] == "Продукты"


def test_get_expenses(client):
    client.post(
        "/expenses",
        json={
            "title": "Продукты",
            "amount": 450.5,
            "category": "Еда",
        },
    )

    response = client.get("/expenses")

    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["amount"] == 450.5

def test_filter_expenses_by_category(client):
    client.post(
        "/expenses",
        json={
            "title": "Продукты",
            "amount": 450.5,
            "category": "Еда",
        },
    )
    client.post(
        "/expenses",
        json={
            "title": "Автобус",
            "amount": 50,
            "category": "Транспорт",
        },
    )

    response = client.get("/expenses?category=еда")

    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["title"] == "Продукты"

def test_expenses_summary(client):
    client.post(
        "/expenses",
        json={
            "title": "Продукты",
            "amount": 450.5,
            "category": "Еда",
        },
    )

    response = client.get("/expenses/summary")

    assert response.status_code == 200
    assert response.json() == {"count": 1, "total": 450.5}


def test_expenses_stats(client):
    client.post(
        "/expenses",
        json={
            "title": "Продукты",
            "amount": 450,
            "category": "Еда",
        },
    )

    client.post(
        "/expenses",
        json={
            "title": "Обед",
            "amount": 250,
            "category": "Еда",
        },
    )

    client.post(
        "/expenses",
        json={
            "title": "Автобус",
            "amount": 100,
            "category": "Транспорт",
        },
    )

    response = client.get("/expenses/stats")

    assert response.status_code == 200

    data = response.json()

    assert data["count"] == 3
    assert data["total"] == 800
    assert data["categories"]["Еда"] == 700
    assert data["categories"]["Транспорт"] == 100
    assert data["most_expensive_category"] == "Еда"


def test_get_expense_by_id(client):
    client.post(
        "/expenses",
        json={
            "title": "Продукты",
            "amount": 450.5,
            "category": "Еда",
        },
    )

    response = client.get("/expenses/1")

    assert response.status_code == 200
    assert response.json()["id"] == 1


def test_update_expense(client):
    client.post(
        "/expenses",
        json={
            "title": "Продукты",
            "amount": 450.5,
            "category": "Еда",
        },
    )

    response = client.put(
        "/expenses/1",
        json={
            "title": "Продукты",
            "amount": 500,
            "category": "Еда",
        },
    )

    assert response.status_code == 200
    assert response.json()["title"] == "Продукты"
    assert response.json()["amount"] == 500
    assert response.json()["category"] == "Еда"
    assert response.json()["id"] == 1


def test_delete_expense(client):
    client.post(
        "/expenses",
        json={
            "title": "Продукты",
            "amount": 450.5,
            "category": "Еда",
        },
    )

    response = client.delete("/expenses/1")

    assert response.status_code == 200
    assert response.json()["id"] == 1

    response_after_delete = client.get("/expenses/1")
    assert response_after_delete.status_code == 404


def test_expense_not_found(client):
    response = client.get("/expenses/999")

    assert response.status_code == 404
    assert response.json() == {"detail": "Expense not found"}


def test_invalid_expense(client):
    response = client.post(
        "/expenses",
        json={
            "title": "Продукты",
            "amount": -10,
            "category": "Еда",
        },
    )

    assert response.status_code == 422


def test_get_budget(client):
    response = client.get("/budget")

    assert response.status_code == 200

    data = response.json()

    assert data["monthly_budget"] == 30000
    assert data["total_spent"] == 0
    assert data["remaining"] == 30000
    assert data["percent_used"] == 0
    assert data["over_budget"] is False


def test_update_budget(client):
    response = client.put(
        "/budget",
        json={"monthly_budget": 40000},
    )

    assert response.status_code == 200
    assert response.json()["monthly_budget"] == 40000

    response = client.get("/budget")

    assert response.json()["monthly_budget"] == 40000


def test_update_budget_invalid(client):
    response = client.put(
        "/budget",
        json={"monthly_budget": 0},
    )

    assert response.status_code == 422
