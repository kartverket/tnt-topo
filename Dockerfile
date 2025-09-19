FROM ghcr.io/camptocamp/qgis-server:3.44

LABEL maintainer="kartverket.no"

EXPOSE 8080

ENV QGIS_PROJECT_FILE=/etc/qgisserver/test.qgs

USER www-data:root

COPY --chown=www-data:root ./fonts /etc/qgisserver/fonts

COPY --chown=www-data:root ./data/test.qgs /etc/qgisserver/test.qgs
