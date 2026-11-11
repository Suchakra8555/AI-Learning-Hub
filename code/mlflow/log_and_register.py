"""Log a model with a signature, read its MLmodel file, register two versions,
and move a `champion` alias between them.

Run:  python log_and_register.py
"""
import mlflow
from mlflow import MlflowClient
from mlflow.models import infer_signature
from sklearn.datasets import load_wine
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split

X, y = load_wine(return_X_y=True, as_frame=True)
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.3, random_state=0)
mlflow.set_experiment("wine-registry")
client = MlflowClient()
NAME = "wine-classifier"

versions = []
for c in [0.01, 1.0]:  # two candidates: a weak one and a good one
    with mlflow.start_run(run_name=f"C={c}"):
        model = LogisticRegression(C=c, max_iter=5000).fit(X_train, y_train)
        acc = model.score(X_test, y_test)
        mlflow.log_param("C", c)
        mlflow.log_metric("accuracy", acc)
        info = mlflow.sklearn.log_model(
            model,
            name="model",
            signature=infer_signature(X_train, model.predict(X_train)),
            input_example=X_train.head(2),
            registered_model_name=NAME,  # creates the next version
        )
        versions.append((info.registered_model_version, acc))
        print(f"C={c}: accuracy {acc:.3f}, model_id {info.model_id}, version {info.registered_model_version}")

print("\nmodel URI:", info.model_uri)  # MLflow 3: models:/<model_id>, a LoggedModel
local = mlflow.artifacts.download_artifacts(info.model_uri)
print("--- MLmodel file of the last model ---")
print(open(f"{local}/MLmodel").read())

best = max(versions, key=lambda v: v[1])[0]
client.set_registered_model_alias(NAME, "champion", best)
client.set_model_version_tag(NAME, best, "validated", "true")
champ = mlflow.pyfunc.load_model(f"models:/{NAME}@champion")
print("champion is version", client.get_model_version_by_alias(NAME, "champion").version)
print("prediction for 2 rows:", champ.predict(X_test.head(2)).tolist())

# Roll back: point the alias at the other version. Serving code that loads @champion needs no change.
other = [v for v, _ in versions if v != best][0]
client.set_registered_model_alias(NAME, "champion", other)
print("after rollback, champion is version", client.get_model_version_by_alias(NAME, "champion").version)
client.set_registered_model_alias(NAME, "champion", best)  # and back again

print("\n--- a schema check: send a column the model never saw ---")
try:
    champ.predict(X_test.head(1).rename(columns={"alcohol": "alcohol_pct"}))
except Exception as e:
    print(type(e).__name__, "...", str(e).split("Error: ")[-1])
