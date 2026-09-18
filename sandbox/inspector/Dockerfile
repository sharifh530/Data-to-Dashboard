ARG BASE_IMAGE
FROM ${BASE_IMAGE}
COPY inspect_data.py /opt/inspect_data.py
USER 65532:65532
ENTRYPOINT ["python", "-I", "-B", "/opt/inspect_data.py"]
