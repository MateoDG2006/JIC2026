FROM debian:bookworm-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends wget ca-certificates python3 \
    && rm -rf /var/lib/apt/lists/*

COPY download_chembl.sh /usr/local/bin/download_chembl.sh
RUN chmod +x /usr/local/bin/download_chembl.sh

ENV CHEMBL_DIR=/data/chembl
VOLUME ["/data/chembl"]

ENTRYPOINT ["/usr/local/bin/download_chembl.sh"]
