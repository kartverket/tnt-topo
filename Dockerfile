FROM ghcr.io/camptocamp/qgis-server:3.44

LABEL maintainer="kartverket.no"

EXPOSE 8080

ENV QGIS_PROJECT_FILE=/etc/qgisserver/project.qgs

# Set www-data UID and GID to 150 to match skiperator requirements
RUN usermod -u 150 www-data \
    && groupmod -g 150 www-data

USER www-data:root

COPY --chown=www-data:root ./runtime/init-server /usr/local/bin/init-server

CMD ["/usr/local/bin/init-server"]

COPY --chown=www-data:root ./fonts /etc/qgisserver/fonts

COPY --chown=www-data:root ./data/test.qgs /data/project.qgs
