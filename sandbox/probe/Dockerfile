# Pass a reviewed Python 3.13 base image pinned by digest; no mutable default.
ARG BASE_IMAGE
FROM ${BASE_IMAGE}
COPY probe.py /opt/dtd-probe.py
RUN touch /opt/dtd-readonly-check && chmod 666 /opt/dtd-readonly-check
USER 65532:65532
ENTRYPOINT ["python", "-I", "-B", "/opt/dtd-probe.py"]
