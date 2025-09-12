# Lag en referanse til aktivt QGIS-prosjekt
project = QgsProject.instance()

# Lag variabel med koordinatsystem
crs = QgsCoordinateReferenceSystem("EPSG:4258")

# Sett koordinatsystem for hele prosjektet
project.setCrs(crs)

# Opprett en LayerOptions med innstillinger for laget
options = QgsVectorLayer.LayerOptions()

# Fortell QGIS på forhånd hva lagets koordinatsystem er
options.fallbackCrs = crs

# Fortell QGIS på forhånd hva lagets geometritype er
options.fallbackWkbType = QgsWkbTypes.LineString

# Fortell QGIS at dette laget ikke kan skrives til
options.forceReadOnly = True

# Usikker på denne: https://qgis.org/pyqgis/master/core/QgsVectorLayer.html#qgis.core.QgsVectorLayer.LayerOptions.loadAllStoredStyles
options.loadAllStoredStyles = True

# Les utstrekning fra prosjektfil istedenfor å hente fra kilden
options.readExtentFromXml = True

# Opprett laget
layer = QgsVectorLayer(
    path="/vsicurl/https://s3-rin.statkart.no/topotest/grenser/n1000.fgb|subset=\"type\" != 'Kommunegrense'",
    baseName="n1000_grenser",
    providerLib="ogr",
    options=options,
)

# Sett WMS-relatert informasjon
layer.setShortName("n1000_grenser")
layer.setTitle("Grenser (N1000)")

# Last inn style fra qml-fil
layer.loadNamedStyle("styles/grenser.qml")

# Legg til i kartet
project.addMapLayer(layer)
