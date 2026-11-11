"""Version a prompt, point an alias at one version, and load it by alias.

Run:  python prompt_registry.py
"""
import mlflow

mlflow.set_experiment("support-bot")
NAME = "support-answer"

v1 = mlflow.genai.register_prompt(
    name=NAME,
    template="Answer {{question}} using only these notes:\n{{notes}}",
    commit_message="first version",
)
v2 = mlflow.genai.register_prompt(
    name=NAME,
    template="Answer {{question}} using only these notes. If they do not say, reply: I don't know.\n{{notes}}",
    commit_message="add the refusal line",
)
print("versions:", v1.version, v2.version)

mlflow.genai.set_prompt_alias(NAME, alias="production", version=1)
print("production ->", mlflow.genai.load_prompt(f"prompts:/{NAME}@production").version)
mlflow.genai.set_prompt_alias(NAME, alias="production", version=2)  # promote
p = mlflow.genai.load_prompt(f"prompts:/{NAME}@production")
print("production ->", p.version, "|", p.commit_message)
print(p.format(question="Do you sell stoves?", notes="(none)"))
