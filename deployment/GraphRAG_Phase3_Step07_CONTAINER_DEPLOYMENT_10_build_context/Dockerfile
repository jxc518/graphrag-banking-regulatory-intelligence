FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

ENV GRAPHRAG_PHASE2_ROOT=/opt/phase2
ENV GRAPHRAG_PHASE2_RUNTIME_CONFIG=/opt/graphrag/runtime
ENV GRAPHRAG_PHASE3_INDEX_OUTPUT=/opt/graphrag/index

WORKDIR /app/phase3

COPY requirements.txt /tmp/requirements.txt

RUN pip install --no-cache-dir -r /tmp/requirements.txt

COPY phase3/app /app/phase3/app
COPY phase2_frozen /opt/phase2

# V1.3 regulatory deployment compatibility
# Production Python expects the frozen Phase 2 deployment path below.
# Keep one physical copy at /opt/phase2 and expose the legacy path via symlink.
RUN mkdir -p /app/phase3/deployment/GraphRAG_Phase3_Step07_CONTAINER_DEPLOYMENT_10_build_context \
    && ln -s /opt/phase2 \
       /app/phase3/deployment/GraphRAG_Phase3_Step07_CONTAINER_DEPLOYMENT_10_build_context/phase2_frozen
COPY graphrag_runtime /opt/graphrag/runtime
COPY graphrag_index /opt/graphrag/index

ENV PYTHONPATH=/app/phase3/app:/opt/phase2

EXPOSE 8000

CMD ["uvicorn", "GraphRAG_Phase3_Step06_API_SERVICE_03_fastapi_app:app", "--app-dir", "/app/phase3/app", "--host", "0.0.0.0", "--port", "8000"]

