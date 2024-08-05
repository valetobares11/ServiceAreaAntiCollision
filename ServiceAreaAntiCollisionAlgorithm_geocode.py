# -*- coding: utf-8 -*-

"""
***************************************************************************
*                                                                         *
*   This program is free software; you can redistribute it and/or modify  *
*   it under the terms of the GNU General Public License as published by  *
*   the Free Software Foundation; either version 2 of the License, or     *
*   (at your option) any later version.                                   *
*                                                                         *
***************************************************************************
"""

from PyQt5.QtCore import (QCoreApplication, QUrl, QVariant)
from PyQt5.QtNetwork import (QNetworkReply,
                             QNetworkAccessManager,
                             QNetworkRequest)
from qgis.core import (QgsProcessing,
                       QgsFeatureSink,
                       QgsProcessingParameterField,
                       QgsProcessingException,
                       QgsProcessingAlgorithm,
                       QgsProcessingParameterFeatureSource,
                       QgsProcessingParameterField,
                       QgsProcessingParameterFeatureSink,
                       QgsNetworkAccessManager,
                       QgsField,
                       QgsFields,
                       QgsWkbTypes,
                       QgsCoordinateReferenceSystem,
                       QgsFeature,
                       QgsGeometry,
                       QgsPointXY,
                       QgsSettings)
from functools import partial
import processing
from . import serviceAreaAntiCollision
import os
import requests
import json
import time
import urllib


class geocodeList(QgsProcessingAlgorithm):
    def __init__(self):
        super().__init__()

    """
    This is an example algorithm that takes a vector layer and
    creates a new identical one.

    It is meant to be used as an example of how to create your own
    algorithms and explain methods and variables used to do it. An
    algorithm like this will be available in all elements, and there
    is not need for additional work.

    All Processing algorithms should extend the QgsProcessingAlgorithm
    class.
    """

    # Constants used to refer to parameters and outputs. They will be
    # used when calling the algorithm from another algorithm, or when
    # calling from the QGIS console.

    INPUT = 'INPUT'
    OUTPUT = 'OUTPUT'
    AddressField = 'Address Field'

    def tr(self, string):
        """
        Returns a translatable string with the self.tr() function.
        """
        return QCoreApplication.translate('Processing', string)

    def createInstance(self):
        return type(self)()

    def name(self):
        """
        Returns the algorithm name, used for identifying the algorithm. This
        string should be fixed for the algorithm, and must not be localised.
        The name should be unique within each provider. Names should contain
        lowercase alphanumeric characters only and no spaces or other
        formatting characters.
        """
        return 'geocodeFieldAddress'

    def displayName(self):
        """
        Returns the translated algorithm name, which should be used for any
        user-visible display of the algorithm name.
        """
        return self.tr('Geocode List')

    def group(self):
        """
        Returns the name of the group this algorithm belongs to. This string
        should be localised.
        """
        return self.tr('geocode')

    def groupId(self):
        """
        Returns the unique ID of the group this algorithm belongs to. This
        string should be fixed for the algorithm, and must not be localised.
        The group id should be unique within each provider. Group id should
        contain lowercase alphanumeric characters only and no spaces or other
        formatting characters.
        """
        return 'geocode'

    def shortHelpString(self):
        """
        Returns a localised short helper string for the algorithm. This string
        should provide a basic description about what the algorithm does and the
        parameters and outputs associated with it.
        """
        return self.tr(
            "This processing algorithm supports geocoding of a list of addresses in a single field originating from a txt/csv/table.<br> Make sure your HERE credentials are stored in the QGIS global settings using the plugin itself. Please read the referenced <a href='https://github.com/riccardoklinger/Hqgis#tos--usage'>Terms of Usage</a> prior usage")

    def loadCredFunctionAlg(self):
        import json
        import os
        #fileLocation = QFileDialog.getOpenFileName(self.dlg, "JSON with credentials",os.path.dirname(os.path.realpath(__file__))+ os.sep + "creds", "JSON(*.JSON)")
        # print(fileLocation)
        scriptDirectory = os.path.dirname(os.path.realpath(__file__))
        # self.dlg.credentialInteraction.setText("")
        creds = {}
        try:
            s = QgsSettings()
            creds["id"] = s.value("HQGIS/api_key", None)
            #self.dlg.credentialInteraction.setText("credits used from " + scriptDirectory + os.sep + 'creds' + os.sep + 'credentials.json')
        except BaseException:
            print("cred load failed, check QGIS global settings")
            #self.dlg.credentialInteraction.setText("no credits found in. Check for file" + scriptDirectory + os.sep + 'creds' + os.sep + 'credentials.json')
            # self.dlg.geocodeButton.setEnabled(False)
        # if not id in creds:
        #    self.feedback.reportError("no id / appcode found! Check file " + scriptDirectory + os.sep + 'creds' + os.sep + 'credentials.json')
        return creds

    def initAlgorithm(self, config=None):
        """
        Here we define the inputs and output of the algorithm, along
        with some other properties.
        """

        # We add the input vector features source. It can have any kind of
        # geometry.
        self.addParameter(
            QgsProcessingParameterFeatureSource(
                self.INPUT,
                self.tr('Input table'),
                [QgsProcessing.TypeVector]
            )
        )
        self.addParameter(
            QgsProcessingParameterField(
                self.AddressField,
                self.tr('Address Field'),
                parentLayerParameterName=self.INPUT,
                type=QgsProcessingParameterField.String

            )
        )

        # We add a feature sink in which to store our processed features (this
        # usually takes the form of a newly created vector layer when the
        # algorithm is run in QGIS).
        self.addParameter(
            QgsProcessingParameterFeatureSink(
                self.OUTPUT,
                self.tr('Geocoded Addresses')
            )
        )

    def convertGeocodeResponse(self, responseAddress):
        geocodeResponse = {}
        try:
            geocodeResponse["Label"] = responseAddress["address"]["label"]
        except BaseException:
            geocodeResponse["Label"] = ""
        try:
            geocodeResponse["Country"] = responseAddress["address"]["country"]
        except BaseException:
            geocodeResponse["Country"] = ""
        try:
            geocodeResponse["State"] = responseAddress["address"]["state"]
        except BaseException:
            geocodeResponse["State"] = ""
        try:
            geocodeResponse["County"] = responseAddress["address"]["county"]
        except BaseException:
            geocodeResponse["County"] = ""
        try:
            geocodeResponse["City"] = responseAddress["address"]["city"]
        except BaseException:
            geocodeResponse["City"] = ""
        try:
            geocodeResponse["District"] = responseAddress["address"][
                "district"
            ]
        except BaseException:
            geocodeResponse["District"] = ""
        try:
            geocodeResponse["Street"] = responseAddress["address"]["street"]
        except BaseException:
            geocodeResponse["Street"] = ""
        try:
            geocodeResponse["HouseNumber"] = responseAddress["address"][
                "houseNumber"
            ]
        except BaseException:
            geocodeResponse["HouseNumber"] = ""
        try:
            geocodeResponse["PostalCode"] = responseAddress["address"][
                "postalCode"
            ]
        except BaseException:
            geocodeResponse["PostalCode"] = ""
        try:
            geocodeResponse["Relevance"] = responseAddress["scoring"]["queryScore"]
        except BaseException:
            geocodeResponse["Relevance"] = None
        try:
            geocodeResponse["CountryQuality"] = responseAddress["scoring"]["fieldscore"][
                "country"
            ]
        except BaseException:
            geocodeResponse["CountryQuality"] = None
        try:
            geocodeResponse["CityQuality"] = responseAddress["scoring"]["fieldscore"]["city"]
        except BaseException:
            geocodeResponse["CityQuality"] = None
        try:
            geocodeResponse["StreetQuality"] = responseAddress["scoring"]["fieldscore"][
                "street"
            ][0]
        except BaseException:
            geocodeResponse["StreetQuality"] = None
        try:
            geocodeResponse["NumberQuality"] = responseAddress["scoring"]["fieldscore"][
                "houseNumber"
            ]
        except BaseException:
            geocodeResponse["NumberQuality"] = None
        try:
            geocodeResponse["MatchType"] = responseAddress["resultType"]
        except BaseException:
            geocodeResponse["MatchType"] = ""
        return geocodeResponse

    def processAlgorithm(self, parameters, context, feedback):
        """
        Here is where the processing itself takes place.
        """

        # Retrieve the feature source and sink. The 'dest_id' variable is used
        # to uniquely identify the feature sink, and must be included in the
        # dictionary returned by the processAlgorithm function.
        source = self.parameterAsSource(
            parameters,
            self.INPUT,
            context
        )
        addressField = self.parameterAsString(
            parameters,
            self.AddressField,
            context
        )
        feedback.pushInfo(addressField)

        # If source was not found, throw an exception to indicate that the algorithm
        # encountered a fatal error. The exception text can be any string, but in this
        # case we use the pre-built invalidSourceError method to return a standard
        # helper text for when a source cannot be evaluated
        if source is None:
            raise QgsProcessingException(
                self.invalidSourceError(
                    parameters, self.INPUT))

        fields = QgsFields()
        fields.append(QgsField("id", QVariant.Int))
        fields.append(QgsField("oldAddress", QVariant.String))
        fields.append(QgsField("lat", QVariant.Double))
        fields.append(QgsField("lng", QVariant.Double))
        fields.append(QgsField("address", QVariant.String))
        fields.append(QgsField("country", QVariant.String))
        fields.append(QgsField("state", QVariant.String))
        fields.append(QgsField("county", QVariant.String))
        fields.append(QgsField("city", QVariant.String))
        fields.append(QgsField("district", QVariant.String))
        fields.append(QgsField("street", QVariant.String))
        fields.append(QgsField("number", QVariant.String))
        fields.append(QgsField("zip", QVariant.String))
        fields.append(QgsField("relevance", QVariant.Double))
        fields.append(QgsField("qu_country", QVariant.Double))
        fields.append(QgsField("qu_city", QVariant.Double))
        fields.append(QgsField("qu_street", QVariant.Double))
        fields.append(QgsField("qu_number", QVariant.Double))
        fields.append(QgsField("matchtype", QVariant.String))
        (sink, dest_id) = self.parameterAsSink(
            parameters,
            self.OUTPUT,
            context,
            fields,
            QgsWkbTypes.Point,
            QgsCoordinateReferenceSystem(4326)
        )

        # Send some information to the user
        feedback.pushInfo(
            '{} addresses to geocode'.format(
                source.featureCount()))

        # If sink was not created, throw an exception to indicate that the algorithm
        # encountered a fatal error. The exception text can be any string, but in this
        # case we use the pre-built invalidSinkError method to return a standard
        # helper text for when a sink cannot be evaluated
        if sink is None:
            raise QgsProcessingException(
                self.invalidSinkError(
                    parameters, self.OUTPUT))

        # Compute the number of steps to display within the progress bar and
        # get features from source
        total = 100.0 / source.featureCount() if source.featureCount() else 0
        features = source.getFeatures()
        # get the keys:
        creds = self.loadCredFunctionAlg()
        for current, feature in enumerate(features):
            # Stop the algorithm if cancel button has been clicked
            if feedback.isCanceled():
                break

            # get the location from the API:
            ApiUrl = "https://geocode.search.hereapi.com/v1/geocode?apiKey=" + \
                creds["id"] + "&q=" + feature[addressField]
            r = requests.get(ApiUrl)
            responseAddress = json.loads(r.text)["items"][0]
            geocodeResponse = self.convertGeocodeResponse(responseAddress)
            lat = responseAddress["position"]["lat"]
            lng = responseAddress["position"]["lng"]
            # Add a feature in the sink
            # feedback.pushInfo(str(lat))
            fet = QgsFeature()
            fet.setGeometry(QgsGeometry.fromPointXY(QgsPointXY(lng, lat)))
            fet.setAttributes([
                feature.id(),
                feature[addressField],
                lat,
                lng,
                geocodeResponse["Label"],
                geocodeResponse["Country"],
                geocodeResponse["State"],
                geocodeResponse["County"],
                geocodeResponse["City"],
                geocodeResponse["District"],
                geocodeResponse["Street"],
                geocodeResponse["HouseNumber"],
                geocodeResponse["PostalCode"],
                geocodeResponse["Relevance"],
                geocodeResponse["CountryQuality"],
                geocodeResponse["CityQuality"],
                geocodeResponse["StreetQuality"],
                geocodeResponse["NumberQuality"],
                geocodeResponse["MatchType"]
            ])
            sink.addFeature(fet, QgsFeatureSink.FastInsert)

            # Update the progress bar
            feedback.setProgress(int(current * total))

        # To run another Processing algorithm as part of this algorithm, you can use
        # processing.run(...). Make sure you pass the current context and feedback
        # to processing.run to ensure that all temporary layer outputs are available
        # to the executed algorithm, and that the executed algorithm can send feedback
        # reports to the user (and correctly handle cancelation and progress
        # reports!)
        if False:
            buffered_layer = processing.run("native:buffer", {
                'INPUT': dest_id,
                'DISTANCE': 1.5,
                'SEGMENTS': 5,
                'END_CAP_STYLE': 0,
                'JOIN_STYLE': 0,
                'MITER_LIMIT': 2,
                'DISSOLVE': False,
                'OUTPUT': 'memory:'
            }, context=context, feedback=feedback)['OUTPUT']

        # Return the results of the algorithm. In this case our only result is
        # the feature sink which contains the processed features, but some
        # algorithms may return multiple feature sinks, calculated numeric
        # statistics, etc. These should all be included in the returned
        # dictionary, with keys matching the feature corresponding parameter
        # or output names.
        return {self.OUTPUT: dest_id}
