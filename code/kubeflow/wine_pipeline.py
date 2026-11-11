"""The wine pipeline: make data, fit a forest, score it. Three KFP components.

Other files import `wine`. Nothing runs here.
"""
from kfp import dsl
from kfp.dsl import Dataset, Input, Metrics, Model, Output

BASE = "python:3.12"  # set it yourself: the SDK default moves from 3.11 to 3.12 on 2027-10-01


@dsl.component(base_image=BASE, packages_to_install=["scikit-learn", "pandas"])
def make_data(test_size: float, train: Output[Dataset], test: Output[Dataset]):
    from sklearn.datasets import load_wine
    from sklearn.model_selection import train_test_split
    X, y = load_wine(return_X_y=True, as_frame=True)
    X["target"] = y
    a, b = train_test_split(X, test_size=test_size, random_state=0)
    a.to_csv(train.path, index=False)
    b.to_csv(test.path, index=False)


@dsl.component(base_image=BASE)
def fit(train: Input[Dataset], trees: int, model: Output[Model]):
    import pickle
    import pandas as pd
    from sklearn.ensemble import RandomForestClassifier
    df = pd.read_csv(train.path)
    clf = RandomForestClassifier(n_estimators=trees, random_state=0).fit(df.drop(columns="target"), df["target"])
    with open(model.path, "wb") as f:
        pickle.dump(clf, f)
    model.metadata["trees"] = trees


@dsl.component(base_image=BASE)
def score(test: Input[Dataset], model: Input[Model], metrics: Output[Metrics]) -> float:
    import pickle
    import pandas as pd
    df = pd.read_csv(test.path)
    with open(model.path, "rb") as f:
        clf = pickle.load(f)
    acc = float((clf.predict(df.drop(columns="target")) == df["target"]).mean())
    metrics.log_metric("accuracy", acc)
    return acc


@dsl.pipeline(name="wine-pipeline")
def wine(trees: int = 50, test_size: float = 0.3) -> float:
    data = make_data(test_size=test_size)
    trained = fit(train=data.outputs["train"], trees=trees)
    result = score(test=data.outputs["test"], model=trained.outputs["model"])
    return result.outputs["Output"]  # a task with an extra Output[...] has several outputs, so use the name
