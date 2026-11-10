FROM python:3.12-slim

WORKDIR /app
COPY pyproject.toml README.md LICENSE ./
COPY src ./src
COPY agent ./agent
COPY fixtures ./fixtures
COPY docs ./docs
COPY failure_scenarios ./failure_scenarios
COPY security ./security
COPY workflows ./workflows
COPY services ./services
RUN pip install --no-cache-dir .
EXPOSE 8000
CMD ["fde-lab", "serve", "--host", "0.0.0.0", "--port", "8000"]
