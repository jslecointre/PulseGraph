import os
from datetime import datetime

import matplotlib.pyplot as plt
import pandas as pd


def plot_classification_score(df: pd.DataFrame, agent_name: str, feedback_key: str, save_dir: str):
    """
    Plot classification score for an agent.

    Args:
        df (pd.DataFrame): DataFrame with evaluation results.
        agent_name (str): Display name for the agent.
        feedback_key (str): Key used to extract evaluator feedback.
        save_dir (str): Directory where the plot image will be saved.

    Returns:
        str: Path to the saved plot image.
    """
    # Compute mean score
    score_col = f"feedback.{feedback_key}_evaluator"
    avg_score = df[score_col].mean() if score_col in df.columns else 0.0

    # Plot
    plt.figure(figsize=(10, 6))
    plt.bar([agent_name], [avg_score], color="#5DA5DA", width=0.5)
    plt.xlabel("Agent Type")
    plt.ylabel("Average Score")
    plt.title(f"Email Triage Performance - {feedback_key.capitalize()} Score")
    plt.text(0, avg_score + 0.02, f"{avg_score:.2f}", ha="center", fontweight="bold")
    plt.ylim(0, 1.1)
    plt.grid(axis="y", linestyle="--", alpha=0.7)

    os.makedirs(save_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    plot_path = os.path.join(save_dir, f"triage_comparison_{timestamp}.png")
    plt.savefig(plot_path)
    plt.close()
    print(f"\nEvaluation visualization saved to: {plot_path}")
    return plot_path
