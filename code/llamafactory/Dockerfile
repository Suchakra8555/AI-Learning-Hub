# A CPU image with LLaMA-Factory v0.9.5, MLflow, KFP and our scripts. Build from code/:
#   docker build -f llamafactory/Dockerfile --build-arg GIT_COMMIT=$(git rev-parse --short HEAD) -t nori-lf:0.9.5 .
FROM python:3.12-slim

# CPU wheels: the default Linux torch wheel brings CUDA libraries a laptop without NVIDIA cannot use
RUN pip install --no-cache-dir torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu

WORKDIR /app
COPY llamafactory/vendor/LlamaFactory /app/vendor/LlamaFactory
RUN pip install --no-cache-dir -e vendor/LlamaFactory "mlflow==3.18.0" "kfp==2.18.0"

COPY llmops/training_data.py /llmops/training_data.py
COPY llamafactory/make_dataset.py llamafactory/train_tracked.py llamafactory/evaluate.py llamafactory/register.py \
     llamafactory/pipeline.py /app/
COPY llamafactory/configs /app/configs
RUN python make_dataset.py

ARG GIT_COMMIT=unknown
ENV GIT_COMMIT=$GIT_COMMIT
