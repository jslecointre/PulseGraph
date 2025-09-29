import asyncio

from langsmith import Client

from email_assistant import SRC_ROOT
from email_assistant.email_assistant_workflow import EmailAssistantWorkflows
from email_assistant.eval.email_dataset import examples_triage
from email_assistant.eval.plot import plot_classification_score

workflow = EmailAssistantWorkflows(checkpointer=None)
email_assistant = workflow.build_graph(draw=True)
# Langsmith Client
langsmith_client = Client()


async def target_email_assistant(inputs: dict) -> dict:
    """Process an email through the workflow-based email assistant.

    Args:
        inputs: A dictionary containing the email_input field from the dataset

    Returns:
        A formatted dictionary with the assistant's response messages
    """
    try:
        response = await email_assistant.ainvoke({"email_input": inputs["email_input"]})
        if "classification_decision" in response:
            return {"classification_decision": response["classification_decision"]}
        else:
            print("No classification_decision in response from workflow agent")
            return {"classification_decision": "unknown"}
    except Exception as e:
        print(f"Error in workflow agent: {e}")
        return {"classification_decision": "unknown"}


def classification_evaluator(outputs: dict, reference_outputs: dict) -> bool:
    """Check if the answer exactly matches the expected answer."""
    return outputs["classification_decision"].lower() == reference_outputs["classification"].lower()


if __name__ == "__main__":
    dataset_name = "E-mail Triage Dataset"
    # https://docs.smith.langchain.com/evaluation/how_to_guides/manage_datasets_programmatically
    if not langsmith_client.has_dataset(dataset_name=dataset_name):
        dataset = langsmith_client.create_dataset(
            dataset_name=dataset_name, description="A dataset of e-mails and their triage decisions."
        )
        langsmith_client.create_examples(dataset_id=dataset.id, examples=examples_triage)

    # Evaluator
    feedback_key = "classification"  # Key saved to langsmith

    experiment_results_workflow = asyncio.run(
        langsmith_client.aevaluate(
            target_email_assistant,
            data=dataset_name,
            evaluators=[classification_evaluator],
            experiment_prefix="E-mail assistant workflow",
            max_concurrency=2,
        )
    )

    df_workflow = experiment_results_workflow.to_pandas()

    workflow_score = (
        df_workflow["feedback.classification_evaluator"].mean()
        if "feedback.classification_evaluator" in df_workflow.columns
        else 0.0
    )

    plot_path = plot_classification_score(
        df_workflow,
        agent_name="Agentic Workflow",
        feedback_key="classification",
        save_dir=f"{SRC_ROOT}/email_assistant/eval/results",
    )

    print(f"Agent With Router Score: {workflow_score:.2f}")
