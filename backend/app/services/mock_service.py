from __future__ import annotations

try:
    from backend.app.schemas import GenerateRequest
except ModuleNotFoundError:
    from app.schemas import GenerateRequest


class MockCodeService:
    """Mock service used for UI and API testing before a real model is connected."""

    def generate(self, request: GenerateRequest) -> dict:
        code = request.code.strip()
        docstring = (
            '"""Calculate the total of all items in a list.\n\n'
            '    Args:\n'
            '        items (list[float]): A list of numeric values to sum.\n\n'
            '    Returns:\n'
            '        float: The total value of all items.\n'
            '    """'
        )
        explanation = (
            'This function iterates through each value in the list, accumulates a running total, and returns the final sum. '
            'It is useful when you want to aggregate several numbers into one total.'
        )

        if request.output_mode == "docstring":
            return {"docstring": docstring, "explanation": None}
        if request.output_mode == "explain":
            return {"docstring": None, "explanation": explanation}
        return {"docstring": docstring, "explanation": explanation}


mock_service = MockCodeService()
