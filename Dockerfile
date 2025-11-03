FROM ghcr.io/camptocamp/qgis-server:3.44

LABEL maintainer="kartverket.no"

EXPOSE 8080

ENV QGIS_SERVER_LOG_PROFILE='true'
ENV QGIS_SERVER_LOG_LEVEL='0'
ENV QGIS_PROJECT_FILE=/data/project.qgs
ENV QGIS_SERVER_IGNORE_BAD_LAYERS='true'
ENV QGIS_SERVER_PARALLEL_RENDERING='false'
ENV QGIS_SERVER_MAX_THREADS='4'
ENV QGIS_SERVER_PROJECT_CACHE_CHECK_INTERVAL='0'

ENV FCGID_IO_TIMEOUT='3600'
ENV FCGID_BUSY_TIMEOUT='3600'
ENV FCGID_IDLE_TIMEOUT='3600'
# ENV FCGID_MAX_REQUESTS_PER_PROCESS='1000'
# ENV FCGID_MIN_PROCESSES=1
# ENV FCGID_MAX_PROCESSES=5

ENV CPL_VSIL_CURL_ALLOWED_EXTENSIONS='.tif,.tiff,.TIF,.fgb,.parquet'
# ENV CPL_CURL_TIMEOUT='60'
# ENV CPL_VSIL_CURL_USE_HEAD='NO'

# Set www-data UID and GID to 150 to match skiperator requirements
RUN usermod -u 150 www-data \
    && groupmod -g 150 www-data

USER www-data:root

COPY --chown=www-data:root --chmod=0755 ./runtime/init-server /usr/local/bin/init-server

CMD ["/usr/local/bin/init-server"]

COPY --chown=www-data:root ./fonts /etc/qgisserver/fonts

COPY --chown=www-data:root ./data/test.qgs /data/project.qgs
