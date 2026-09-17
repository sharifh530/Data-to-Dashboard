ARG BASE_IMAGE
FROM ${BASE_IMAGE}
COPY exercise.py /opt/exercise.py
USER 65532:65532
ENTRYPOINT ["python", "-I", "-B", "/opt/exercise.py"]
