import asyncio

from langsmith import Client

from email_assistant.chains.criteria_grader import criteria_eval_structured_llm
from email_assistant.email_assistant_workflow import (
    EmailAssistantWorkflows,
    compiled_workflow,
)
from email_assistant.eval.email_dataset import email_inputs, response_criteria_list
from email_assistant.eval.prompts import RESPONSE_CRITERIA_SYSTEM_PROMPT
from email_assistant.utils import format_messages_string

workflow = EmailAssistantWorkflows(checkpointer=None)
email_assistant = workflow.build_graph(draw=True)
# Langsmith Client
langsmith_client = Client()


if __name__ == "__main__":
    email_input = email_inputs[0]
    print("Email Input:", email_input)
    success_criteria = response_criteria_list[0]
    print("Success Criteria:", success_criteria)

    response = asyncio.run(compiled_workflow.ainvoke({"email_input": email_input}))

    all_messages_str = format_messages_string(response["messages"])
    eval_result = criteria_eval_structured_llm.invoke(
        [
            {"role": "system", "content": RESPONSE_CRITERIA_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": f"""\n\n Response criteria: {success_criteria} \n\n Assistant's response: \n\n {all_messages_str} \n\n Evaluate whether the assistant's response meets the criteria and provide justification for your evaluation.""",  # noqa E501
            },
        ]
    )

    print(eval_result)
