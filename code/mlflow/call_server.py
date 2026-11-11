"""Call a model served by `mlflow models serve`. Standard library only.

Start the server first (in another terminal):
  mlflow models serve -m "models:/wine-classifier@champion" --env-manager local -p 5001
Run:  python call_server.py
"""
import json
import urllib.error
import urllib.request

BASE = "http://127.0.0.1:5001"
ROW = [13.74, 1.67, 2.25, 16.4, 118, 2.6, 2.9, 0.21, 1.62, 5.85, 0.92, 3.2, 1060]
COLS = ["alcohol", "malic_acid", "ash", "alcalinity_of_ash", "magnesium", "total_phenols",
        "flavanoids", "nonflavanoid_phenols", "proanthocyanins", "color_intensity", "hue",
        "od280/od315_of_diluted_wines", "proline"]


def call(path, body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(BASE + path, data=data, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req) as r:
            return r.status, r.read().decode()
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()


print("GET /ping   ", call("/ping"))
print("GET /version", call("/version"))
# The same row in the three input shapes /invocations accepts for a table model.
print("dataframe_split  ", call("/invocations", {"dataframe_split": {"columns": COLS, "data": [ROW]}}))
print("dataframe_records", call("/invocations", {"dataframe_records": [dict(zip(COLS, ROW))]}))
print("inputs (columns)  ", call("/invocations", {"inputs": {c: [v] for c, v in zip(COLS, ROW)}}))
print("bad: missing key  ", call("/invocations", {"rows": [ROW]}))
