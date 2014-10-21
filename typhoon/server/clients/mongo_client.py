"""
This file is part of typhoon, a request-counting web server.
Copyright (C) 2014 Ryan Brown <sb@ryansb.com>

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as
published by the Free Software Foundation, either version 3 of the
License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

import datetime, time
from json import JSONEncoder
import json
import json.encoder
import logging

from bson.objectid import ObjectId
from bson.timestamp import Timestamp
import jsonschema
from pymongo import GEO2D
from tornado.gen import Return, coroutine


class BaseMongoClient(object):
    """Concrete abstract class for a mongo collection and document interface

    This class simplifies the use of the motor library, encoding/decoding special types, etc
    """

    def __init__(self, collection_name, settings, schema=None):

        """
        Constructor

        :param str collection_name: The name of the collection you want to operate on
        :param dict settings: The application settings
        :param dict schema: A JSON Schema definition for this object type, used for validation
        :param bool scheduleable: Whether or not this document is scheduleable

        """
        self.logger = logging.getLogger(self.__class__.__name__)
        self.settings = settings
        self.client = self.settings.get("db")

        assert self.client is not None
        self.collection_name = collection_name
        self.revisions_collection = self.client["revisions"]
        self.collection = self.client[collection_name]
        self.schema = schema

    @coroutine
    def insert(self, dct):
        """Create a document

        :param dict dct:
        :param toa toa: Optional time of action, triggers this to be handled as a future insert action for a new document
        :param str comment: A comment
        :rtype str:
        :returns string bson id:
        """
        if self.schema:
            jsonschema.validate(dct, self.schema)

        bson_obj = yield self.collection.insert(dct)

        raise Return(bson_obj.__str__())

    @coroutine
    def upsert(self, _id, dct, attribute="_id"):
        """Update or Insert a new document

        :param str _id: The document id
        :param dict dct: The dictionary to set on the document
        :param str attribute: The attribute to query for to find the object to set this data on
        :returns: JSON Mongo client response including the "n" key to show number of objects effected
        """

        mongo_response = yield self.update(_id, dct, upsert=True, attribute=attribute)

        raise Return(mongo_response)

    @coroutine
    def update(self, predicate_value, dct, upsert=False, attribute="_id"):
        """Update an existing document

        :param predicate_value: The value of the predicate
        :param dict dct: The dictionary to update with
        :param bool upsert: Whether this is an upsert action
        :param str attribute: The attribute to query for to find the object to set this data ond
        :returns: JSON Mongo client response including the "n" key to show number of objects effected
        """
        if self.schema:
            jsonschema.validate(dct, self.schema)

        if attribute=="_id" and not isinstance(predicate_value, ObjectId):
            predicate_value = ObjectId(predicate_value)

        predicate = {attribute: predicate_value}


        dct = self._dictionary_to_cursor(dct)

        mongo_response = yield self.collection.update(predicate, dct, upsert)

        raise Return(self._obj_cursor_to_dictionary(mongo_response))


    @coroutine
    def patch(self, predicate_value, attrs, predicate_attribute="_id"):
        """Update an existing document via a $set query, this will apply only these attributes.

        :param predicate_value: The value of the predicate
        :param dict attrs: The dictionary to apply to this object
        :param str predicate_attribute: The attribute to query for to find the object to set this data ond
        :returns: JSON Mongo client response including the "n" key to show number of objects effected
        t"""

        if predicate_attribute=="_id" and not isinstance(predicate_value, ObjectId):
            predicate_value = ObjectId(predicate_value)

        predicate = {predicate_attribute: predicate_value}

        dct = self._dictionary_to_cursor(attrs)

        if dct.get("_id"):
            del dct["_id"]

        set = { "$set": dct }

        mongo_response = yield self.collection.update(predicate, set, False)

        raise Return(self._obj_cursor_to_dictionary(mongo_response))

    @coroutine
    def delete(self, _id):
        """Delete a document or create a DELETE revision

        :param str _id: The ID of the document to be deleted
        :returns: JSON Mongo client response including the "n" key to show number of objects effected
        """
        mongo_response = yield self.collection.remove({"_id": ObjectId(_id)})

        raise Return(mongo_response)

    @coroutine
    def delete_by_query(self, dct):
        """
        Allows for removing documents by custom query

        :param dct:
        :return:
        """
        mongo_response = yield self.collection.remove(dct)

        raise Return(mongo_response)

    @coroutine
    def find_one(self, query):
        """Find one wrapper with conversion to dictionary

        :param dict query: A Mongo query
        """
        mongo_response = yield self.collection.find_one(query)
        raise Return(self._obj_cursor_to_dictionary(mongo_response))

    @coroutine
    def find(self, query, orderby=None, order_by_direction=1, page=0, limit=0):
        """Find a document by any criteria

        :param dict query: The query to perform
        :param str orderby: The attribute to order results by
        :param int order_by_direction: 1 or -1
        :param int page: The page to return
        :param int limit: Number of results per page
        :returns: A list of results
        :rtype: list

        """

        cursor = self.collection.find(query)

        if orderby:
            cursor.sort(orderby, order_by_direction)

        cursor.skip(page*limit).limit(limit)

        results = []
        while (yield cursor.fetch_next):
            results.append(self._obj_cursor_to_dictionary(cursor.next_object()))

        raise Return(results)

    @coroutine
    def find_one_by_id(self, _id):
        """
        Find a single document by id

        :param str _id: BSON string repreentation of the Id
        :return: a signle object
        :rtype: dict

        """
        document = (yield self.collection.find_one({"_id": ObjectId(_id)}))
        raise Return(self._obj_cursor_to_dictionary(document))

    @coroutine
    def find_one_and_modify(self, _id, sort=None, remove=False, update=None, **kwargs):
        """
        Find a single document by id and modify it

        :param str _id: BSON string repreentation of the Id
        :return: a single object
        :rtype: dict

        """
        document = (yield self.collection.find_and_modify(query={"_id": ObjectId(_id)}, sort=sort, remove=remove, update=update, kwargs=kwargs))
        raise Return(self._obj_cursor_to_dictionary(document))

    @coroutine
    def create_index(self, index, index_type=GEO2D):
        """Create an index on a given attribute

        :param str index: Attribute to set index on
        :param str index_type: See PyMongo index types for further information, defaults to GEO2D index.
        """
        self.logger.info("Adding %s index to stores on attribute: %s" % (index_type, index))
        yield self.collection.create_index([(index, index_type)])

    @coroutine
    def find_and_group_by(self, key, condition, initial, reduce, finalize={}):
        """
        Group results where necessary
        :param key:
        :param condition:
        :param initial:
        :param reduce:
        :param finalize:
        :return:
        """
        results = yield self.collection.group(key=key, condition=condition, initial=initial, reduce=reduce)
        raise Return(self._list_cursor_to_json(results))

    @coroutine
    def location_based_search(self, lng, lat, distance, unit="miles", attribute_map=None, page=0, limit=50):
        """Search based on location and other attribute filters

        :param float lng: Longitude parameter
        :param float lat: Latitude parameter
        :param int distance: The radius of the query
        :param str unit: The unit of measure for the query, defaults to miles
        :param dict attribute_map: Additional attributes to apply to the location bases query
        :param int page: The page to return
        :param int limit: Number of results per page
        :returns: List of objects
        :rtype: list
        """

        #Determine what type of radian conversion you want base on a unit of measure
        if unit == "miles":
            distance = float(distance/69)
        else:
            distance = float(distance/111.045)

        #Start with geospatial query
        query = {
            "loc" : {
                "$within": {
                    "$center" : [[lng, lat], distance]}
                }
        }

        #Allow querying additional attributes
        if attribute_map:
            query = dict(query.items() + attribute_map.items())

        results = yield self.find(query, page=page, limit=limit)

        raise Return(self._list_cursor_to_json(results))

    @coroutine
    def aggregate(self, pipeline, **kwargs):
        """Run an aggregate query on this collection, proxies all pymongo/motor arguments and returns a dictionary of primatives"""

        results = yield self.collection.aggregate(pipeline, **kwargs)
        raise Return(self._obj_cursor_to_dictionary(results))

    def _dictionary_to_cursor(self, obj):
        """
        Take a raw dictionary representation and adapt it back to a proper mongo document dictionary
        :param dict obj: The object to adapt
        :return: a mongo document with complex types for storage in mongo
        :rtype: dict
        """
        if obj.get("id"):
            obj["_id"] = ObjectId(obj.get("id"))
            del obj["id"]

        if isinstance(obj.get("_id"), str):
            obj["_id"] = ObjectId(obj.get("_id"))

        return obj

    def _obj_cursor_to_dictionary(self, cursor):
        """Handle conversion of pymongo cursor into a JSON object formatted for UI consumption

        :param dict cursor: a mongo document that should be converted to primitive types for the client code
        :returns: a primitive dictionary
        :rtype: dict
        """
        if not cursor:
            return cursor

        cursor = json.loads(json.dumps(cursor, cls=BSONEncoder))

        if cursor.get("_id"):
            cursor["id"] = cursor.get("_id")
            del cursor["_id"]

        return cursor

    def _list_cursor_to_json(self, cursor):
        """Convenience method for converting a mongokit or pymongo list cursor into a JSON object for return"""
        return [self._obj_cursor_to_dictionary(obj) for obj in cursor]

class BSONEncoder(JSONEncoder):
    """BSONEncorder is used to transform certain value types to a more desirable format"""

    def default(self, obj, **kwargs):
        """Handles the adapting of special types from mongo"""
        if isinstance(obj, datetime.datetime):
            return time.mktime(obj.timetuple())

        if isinstance(obj, Timestamp):
            return obj.time

        if isinstance(obj, ObjectId):
            return obj.__str__()

        return JSONEncoder.default(self, obj)

