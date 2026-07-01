"""Math and utility tool endpoints."""

from fastapi import APIRouter
from pydantic import BaseModel, Field

router = APIRouter(prefix="/math", tags=["math"])


class AddRequest(BaseModel):
    a: float = Field(..., description="First number")
    b: float = Field(..., description="Second number")


class AddResponse(BaseModel):
    result: float
    expression: str


class PercentageRequest(BaseModel):
    value: float
    percent: float


@router.post("/add", response_model=AddResponse)
def add_numbers(body: AddRequest) -> AddResponse:
    """Add two numbers together."""
    result = body.a + body.b
    return AddResponse(result=result, expression=f"{body.a} + {body.b} = {result}")


@router.post("/percentage")
def calculate_percentage(body: PercentageRequest) -> dict:
    """Calculate what percentage of a value equals."""
    amount = (body.value * body.percent) / 100
    return {
        "value": body.value,
        "percent": body.percent,
        "result": amount,
        "expression": f"{body.percent}% of {body.value} = {amount}",
    }


@router.get("/fibonacci/{n}")
def fibonacci(n: int) -> dict:
    """Return the first n Fibonacci numbers (max 50)."""
    n = max(1, min(n, 50))
    sequence = [0, 1]
    for _ in range(2, n):
        sequence.append(sequence[-1] + sequence[-2])
    return {"count": n, "sequence": sequence[:n]}
