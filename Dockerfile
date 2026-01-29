FROM ghcr.io/camptocamp/qgis-server:3.44

LABEL maintainer="kartverket.no"

EXPOSE 8080

ENV QGIS_SERVER_LOG_PROFILE='true'
ENV QGIS_SERVER_LOG_LEVEL='0'
ENV QGIS_PROJECT_FILE=/etc/qgisserver/project.qgs
ENV QGIS_SERVER_IGNORE_BAD_LAYERS='true'
ENV QGIS_SERVER_PARALLEL_RENDERING='false'
ENV QGIS_SERVER_PROJECT_CACHE_STRATEGY='filesystem'
# ENV QGIS_SERVER_CACHE_DIRECTORY='/tmp'
ENV QGIS_SERVER_CACHE_SIZE='256'
ENV MAX_CACHE_LAYERS='5000'
ENV QGIS_SERVER_TRUST_LAYER_METADATA='1'
ENV QGIS_SERVER_FORCE_READONLY_LAYERS='true'

ENV FCGID_IO_TIMEOUT='3600'
ENV FCGID_BUSY_TIMEOUT='3600'
ENV FCGID_IDLE_TIMEOUT='3600'
ENV FCGID_MAX_REQUESTS_PER_PROCESS='1000'
ENV FCGID_MIN_PROCESSES='4'
ENV FCGID_MAX_PROCESSES='8'

ENV CPL_VSIL_CURL_ALLOWED_EXTENSIONS='.tif,.tiff,.TIF,.fgb,.parquet'
ENV VSI_CACHE='TRUE'
ENV VSI_CACHE_SIZE='50000000'

# GDAL/OGR performance and logging configuration
ENV CPL_LOG_ERRORS='OFF'
ENV CPL_DEBUG='OFF'
ENV GDAL_DISABLE_READDIR_ON_OPEN='EMPTY_DIR'
ENV GDAL_CACHEMAX='1024'
ENV GDAL_PAM_ENABLED='NO'
ENV GDAL_HTTP_TIMEOUT='120'
ENV GDAL_HTTP_CONNECTTIMEOUT='60'
ENV GDAL_HTTP_MAX_RETRY='3'
ENV GDAL_HTTP_RETRY_DELAY='1'

# Qt cache configuration
ENV QT_NETWORK_CACHE_SIZE='104857600'
ENV QT_NETWORK_CACHE_DIR='/tmp/qt-cache'
ENV QT_CACHE_DISABLE_COMPRESSION='0'
# ENV XDG_CACHE_HOME='/tmp'

# Python optimization
ENV PYTHONOPTIMIZE='2'

# Memory allocation optimization
ENV MALLOC_TRIM_THRESHOLD_='65536'
ENV MALLOC_MMAP_THRESHOLD_='131072'

ENV PROJ_NETWORK='ON'

# Install htop for system monitoring inside the container, useful for finding performance settings
RUN apt-get update && apt-get install -y htop && rm -rf /var/lib/apt/lists/*

# Set www-data UID and GID to 150 to match skiperator requirements
RUN usermod -u 150 www-data \
    && groupmod -g 150 www-data

# Ensure Apache runtime dir exists in the image 
RUN mkdir -p /run/apache2 \
    && chown www-data:root /run/apache2 \
    && chmod 0775 /run/apache2

USER www-data:root

# Copy PROJ grid file for Norwegian coordinate transformations
COPY proj/no_kv_HREF2018B_NN2000_EUREF89.tif /usr/share/proj/

COPY --chown=www-data:root --chmod=0755 ./runtime/init-server /usr/local/bin/init-server

CMD ["/usr/local/bin/init-server"]

COPY --chown=www-data:root ./fonts /etc/qgisserver/fonts

COPY --chown=www-data:root ./data/topo_2026.qgs /data/project.qgs
