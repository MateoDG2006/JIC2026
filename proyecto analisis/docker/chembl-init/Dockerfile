FROM debian:bookworm-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends wget ca-certificates python3 python3-yaml \
    && rm -rf /var/lib/apt/lists/*

COPY download_chembl.sh /usr/local/bin/download_chembl.sh
RUN chmod +x /usr/local/bin/download_chembl.sh

ENV CONFIG_PATH=/config/config.yaml
ENV CHEMBL_DB_PATH=/data/chembl/chembl_37.db

ENTRYPOINT ["/usr/local/bin/download_chembl.sh"]
