import pytest  # noqa E402
from dotenv import load_dotenv  # noqa E402
from langsmith import testing as t  # noqa E402

from email_assistant.email_assistant_workflow import compiled_workflow  # noqa E402
from email_assistant.eval.email_dataset import (  # noqa E402
    email_inputs,
    expected_tool_calls,
)
from email_assistant.utils import (  # noqa E402
    extract_tool_calls,
    format_messages_string,
)


@pytest.mark.asyncio
@pytest.mark.langsmith
@pytest.mark.parametrize(
    "email_input, expected_calls",
    [  # Pick some examples with e-mail reply expected
        (email_inputs[0], expected_tool_calls[0]),
        (email_inputs[3], expected_tool_calls[3]),
    ],
)
async def test_email_dataset_tool_calls(email_input, expected_calls):
    """Test if email processing contains expected tool calls."""
    try:
        # Run the email assistant
        result = await compiled_workflow.ainvoke({"email_input": email_input})

        # Extract tool calls from messages list
        extracted_tool_calls = extract_tool_calls(result["messages"])

        missing_calls = [call for call in expected_calls if call.lower() not in extracted_tool_calls]
        # https://docs.smith.langchain.com/reference/python/testing/langsmith.testing._internal.log_outputs
        t.log_outputs(
            {
                "missing_calls": missing_calls,
                "extracted_tool_calls": extracted_tool_calls,
                "response": format_messages_string(result["messages"]),
            }
        )

        assert len(missing_calls) == 0
    except Exception as e:
        print(f"Test failed with error: {e}")
        raise


def foo(x, y):
    return x + y


@pytest.mark.langsmith
def test_foo() -> None:
    x = 0
    y = 1
    expected = 1
    result = foo(x, y)
    t.log_reference_outputs({"foo": expected})
    t.log_inputs({"x": x, "y": y})
    t.log_outputs({"foo": result})
    assert result == expected
