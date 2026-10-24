import json
import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel, Field


# Настройки приложения
APP_VERSION = os.getenv("APP_VERSION", "1.0.0")

BASE_DIR = Path(__file__).resolve().parent

EXPENSES_FILE = Path(
    os.getenv(
        "EXPENSES_FILE",
        str(BASE_DIR / "data" / "expenses.json"),
    )
)

BUDGET_FILE = BASE_DIR / "data" / "budget.json"

DEFAULT_MONTHLY_BUDGET = 30000.0
monthly_budget = DEFAULT_MONTHLY_BUDGET


# Настройка журналирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)

logger = logging.getLogger("expense_tracker")


# Список расходов и следующий номер
expenses = []
next_expense_id = 1


# Данные, которые пользователь отправляет при добавлении расхода
class BudgetUpdate(BaseModel):
    monthly_budget: float = Field(gt=0)

class ExpenseCreate(BaseModel):
    title: str = Field(min_length=1, max_length=100)
    amount: float = Field(gt=0)
    category: str = Field(min_length=1, max_length=50)


# Расход с уникальным номером
class Expense(ExpenseCreate):
    id: int


# Загрузка расходов из файла
def load_expenses():
    global next_expense_id

    if not EXPENSES_FILE.exists():
        logger.info("Data file does not exist yet")
        return

    try:
        with EXPENSES_FILE.open("r", encoding="utf-8") as file:
            saved_data = json.load(file)

        if not isinstance(saved_data, list):
            raise ValueError("JSON must contain a list of expenses")

        loaded_expenses = [
            Expense(**item) for item in saved_data
        ]

    except (OSError, json.JSONDecodeError, ValueError, TypeError) as error:
        logger.error("Could not load expenses: %s", error)
        raise RuntimeError("Could not load expenses from JSON file") from error

    expenses.clear()
    expenses.extend(loaded_expenses)

    if expenses:
        next_expense_id = max(item.id for item in expenses) + 1
    else:
        next_expense_id = 1

    logger.info("Loaded %s expenses", len(expenses))


# Сохранение расходов в файл
def save_expenses():
    EXPENSES_FILE.parent.mkdir(parents=True, exist_ok=True)

    data = [expense.model_dump() for expense in expenses]

    with EXPENSES_FILE.open("w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=4)

    logger.info("Saved %s expenses", len(expenses))


def load_budget():
    global monthly_budget

    if not BUDGET_FILE.exists():
        return

    try:
        with BUDGET_FILE.open("r", encoding="utf-8") as file:
            data = json.load(file)

        monthly_budget = float(data["monthly_budget"])

    except (OSError, json.JSONDecodeError, KeyError, TypeError, ValueError):
        logger.exception("Could not load budget")


def save_budget():
    BUDGET_FILE.parent.mkdir(parents=True, exist_ok=True)

    with BUDGET_FILE.open("w", encoding="utf-8") as file:
        json.dump(
            {"monthly_budget": monthly_budget},
            file,
            ensure_ascii=False,
            indent=4,
        )


# Действия при запуске и остановке приложения
@asynccontextmanager
async def lifespan(app: FastAPI):
    load_expenses()
    load_budget()

    logger.info("Expense Tracker started, version=%s", APP_VERSION)

    yield

    logger.info("Expense Tracker stopped")


# Создание приложения
app = FastAPI(
    title="Expense Tracker API",
    description="A simple personal expense tracking service",
    version=APP_VERSION,
    lifespan=lifespan,
)


# Запись информации о запросах в журнал
@app.middleware("http")
async def log_requests(request: Request, call_next):
    logger.info(
        "Request started: %s %s",
        request.method,
        request.url.path,
    )

    response = await call_next(request)

    logger.info("Request finished: status=%s", response.status_code)

    return response


# Главная страница
@app.get("/")
def home():
    return {"message": "Welcome to Expense Tracker API"}


# Проверка состояния приложения
@app.get("/health")
def health():
    return {"status": "ok"}


# Версия приложения
@app.get("/version")
def version():
    return {"version": APP_VERSION}


# Получение всех расходов с необязательной фильтрацией по категории
@app.get("/expenses", response_model=list[Expense])
def get_expenses(category: str | None = None):
    if category is None:
        return expenses

    return [
        expense
        for expense in expenses
        if expense.category.casefold() == category.casefold()
    ]


# Добавление расхода
@app.post("/expenses", response_model=Expense, status_code=201)
def add_expense(expense: ExpenseCreate):
    global next_expense_id

    new_expense = Expense(
        id=next_expense_id,
        title=expense.title,
        amount=expense.amount,
        category=expense.category,
    )

    expenses.append(new_expense)

    try:
        save_expenses()
    except (OSError, TypeError, ValueError):
        expenses.pop()
        logger.exception("Could not save expense")
        raise HTTPException(
            status_code=500,
            detail="Could not save expense",
        )

    next_expense_id += 1

    logger.info("Expense created: id=%s", new_expense.id)

    return new_expense


# Подсчёт расходов
@app.get("/expenses/summary")
def expenses_summary():
    total = sum(expense.amount for expense in expenses)

    return {
        "count": len(expenses),
        "total": round(total, 2),
    }


@app.get("/expenses/stats")
def expenses_stats():
    total = sum(expense.amount for expense in expenses)

    categories = {}

    for expense in expenses:
        if expense.category not in categories:
            categories[expense.category] = 0

        categories[expense.category] += expense.amount

    categories = {
        category: round(amount, 2)
        for category, amount in categories.items()
    }

    most_expensive_category = None

    if categories:
        most_expensive_category = max(
            categories,
            key=categories.get,
        )

    return {
        "count": len(expenses),
        "total": round(total, 2),
        "categories": categories,
        "most_expensive_category": most_expensive_category,
    }


# Получение расхода по номеру
@app.get("/expenses/{expense_id}", response_model=Expense)
def get_expense(expense_id: int):
    for expense in expenses:
        if expense.id == expense_id:
            return expense

    raise HTTPException(
        status_code=404,
        detail="Expense not found",
    )
@app.put("/expenses/{expense_id}", response_model=Expense)
def update_expense(expense_id: int, updated_data: ExpenseCreate):
    for index, expense in enumerate(expenses):
        if expense.id == expense_id:
            updated_expense = Expense(
                id=expense_id,
                title=updated_data.title,
                amount=updated_data.amount,
                category=updated_data.category,
            )

            old_expense = expenses[index]
            expenses[index] = updated_expense

            try:
                save_expenses()
            except (OSError, TypeError, ValueError):
                expenses[index] = old_expense
                logger.exception("Could not update expense")
                raise HTTPException(
                    status_code=500,
                    detail="Could not save expense",
                )

            logger.info("Expense updated: id=%s", expense_id)
            return updated_expense

    raise HTTPException(
        status_code=404,
        detail="Expense not found",
    )


@app.delete("/expenses/{expense_id}")
def delete_expense(expense_id: int):
    for index, expense in enumerate(expenses):
        if expense.id == expense_id:
            deleted_expense = expenses.pop(index)

            try:
                save_expenses()
            except (OSError, TypeError, ValueError):
                expenses.insert(index, deleted_expense)
                logger.exception("Could not delete expense")
                raise HTTPException(
                    status_code=500,
                    detail="Could not save expenses",
                )

            logger.info("Expense deleted: id=%s", expense_id)
            return {
                "message": "Expense deleted successfully",
                "id": expense_id,
            }

    raise HTTPException(
        status_code=404,
        detail="Expense not found",
    )


@app.get("/budget")
def get_budget():
    total = sum(expense.amount for expense in expenses)
    remaining = monthly_budget - total

    if monthly_budget > 0:
        percent_used = round(total / monthly_budget * 100, 2)
    else:
        percent_used = 0

    return {
        "monthly_budget": round(monthly_budget, 2),
        "total_spent": round(total, 2),
        "remaining": round(remaining, 2),
        "percent_used": percent_used,
        "over_budget": total > monthly_budget,
    }


@app.put("/budget")
def update_budget(budget_data: BudgetUpdate):
    global monthly_budget

    old_budget = monthly_budget
    monthly_budget = budget_data.monthly_budget

    try:
        save_budget()
    except (OSError, TypeError, ValueError):
        monthly_budget = old_budget
        logger.exception("Could not save budget")
        raise HTTPException(
            status_code=500,
            detail="Could not save budget",
        )

    logger.info("Monthly budget updated: %s", monthly_budget)

    return {
        "message": "Budget updated successfully",
        "monthly_budget": round(monthly_budget, 2),
    }
