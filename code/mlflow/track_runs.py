"""Three training runs, logged and compared with MLflow Tracking.

Run:  python track_runs.py
Then: mlflow ui   (open http://127.0.0.1:5000)
Needs: pip install -r requirements.txt
"""
import mlflow
from sklearn.datasets import load_wine
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, f1_score
from sklearn.model_selection import train_test_split

X, y = load_wine(return_X_y=True)
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.3, random_state=0)

mlflow.set_experiment("wine-forest")  # created on first use

for trees, depth in [(5, 2), (50, 4), (200, None)]:
    with mlflow.start_run(run_name=f"trees={trees} depth={depth}"):
        mlflow.log_params({"n_estimators": trees, "max_depth": depth})
        mlflow.set_tag("dataset", "sklearn wine, 30% test, seed 0")
        model = RandomForestClassifier(n_estimators=trees, max_depth=depth, random_state=0)
        model.fit(X_train, y_train)
        pred = model.predict(X_test)
        mlflow.log_metrics({
            "accuracy": accuracy_score(y_test, pred),
            "f1_macro": f1_score(y_test, pred, average="macro"),
        })
        for step, tree in enumerate(model.estimators_[:5]):  # a metric with steps draws a line chart
            mlflow.log_metric("single_tree_accuracy", accuracy_score(y_test, tree.predict(X_test)), step=step)
        with open("notes.txt", "w") as f:
            f.write(f"feature importances: {model.feature_importances_.round(3).tolist()}\n")
        mlflow.log_artifact("notes.txt")

print("tracking URI:", mlflow.get_tracking_uri())
runs = mlflow.search_runs(
    experiment_names=["wine-forest"],
    filter_string="metrics.accuracy > 0.9",
    order_by=["metrics.f1_macro DESC"],
)
print(runs[["tags.mlflow.runName", "params.n_estimators", "metrics.accuracy", "metrics.f1_macro"]].to_string(index=False))
