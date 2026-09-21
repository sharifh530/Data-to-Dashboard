ARG BASE_IMAGE
FROM ${BASE_IMAGE}
RUN pip install --no-cache-dir pandas==2.2.3
COPY transform_data.py /opt/transform_data.py
USER 65532:65532
ENTRYPOINT ["python", "-I", "-B", "/opt/transform_data.py"]

