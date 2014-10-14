"""
A base handlers module
"""

import json
import tornado.web
from bson.objectid import ObjectId
import logging
from bson import json_util
from tornado.web import authenticated

class BaseHandler(tornado.web.RequestHandler):
    """A class to collect common handler methods that can be useful in your individual implementation,
    this includes functions for working with query strings and Motor/Mongo type documents
    """

    def initialize(self):
        self.logger = logging.getLogger(self.__class__.__name__)

    def load_json(self):
        """Load JSON from the request body and store them in
        self.request.arguments, like Tornado does by default for POSTed form
        parameters.

        If JSON cannot be decoded

        :raises ValueError: JSON Could not be decoded
        """
        try:
            self.request.arguments = json.loads(self.request.body)
        except ValueError:
            msg = "Could not decode JSON: %s" % self.request.body
            self.logger.debug(msg)
            self.raise_error(400, msg)

    def get_json_argument(self, name, default=None):
        """Find and return the argument with key 'name'
        from JSON request data. Similar to Tornado's get_argument() method.

        :param str name: The name of the json key you want to get the value for
        :param bool default: The default value if nothing is found
        :returns: value of the argument name request
        """

        if default is None:
            default = self._ARG_DEFAULT
        if not self.request.arguments:
            self.load_json()
        if name not in self.request.arguments:
            if default is self._ARG_DEFAULT:
                msg = "Missing argument '%s'" % name
                self.logger.debug(msg)
                self.raise_error(400, msg)
            self.logger.debug("Returning default argument %s, as we couldn't find "
                    "'%s' in %s" % (default, name, self.request.arguments))
            return default
        arg = self.request.arguments[name]
        return arg

    def get_dict_of_all_args(self):
        """Generates a dictionary from a handler paths query string and returns it

        :returns: Dictionary of all key/values in arguments list
        :rtype: dict
        """
        dictionary = {}
        for arg in [arg for arg in self.request.arguments if arg not in self.settings.get("reserved_query_string_params", [])]:
            val =  self.get_argument(arg, default=None)
            if val:
                dictionary[arg] = val
        return dictionary

    def get_arg_value_as_type(self, key, default=None, convert_int=False):
        """Allow users to pass through truthy type values like true, yes, no and get to a typed variable in your code

        :param str val: The string reprensentation of the value you want to convert
        :returns: adapted value
        :rtype: dynamic
        """

        val = self.get_query_argument(key, default)

        if isinstance(val, int):
            return val

        if val.lower() in ['true', 'yes']:
            return True

        if val.lower() in ['false', 'no']:
            return False

        return val

    def get_mongo_query_from_arguments(self, reserved_attributes=[]):
        """Generate a mongo query from the given URL query parameters, handles OR query via multiples

        :param list reserved_attributes: A list of attributes you want to exclude from this particular query
        :return: dict
        """

        query = {}
        for arg in self.request.arguments:
            if arg not in reserved_attributes:
                if len(self.request.arguments.get(arg)) > 1:
                    query["$or"] = []
                    for val in self.request.arguments.get(arg):
                        query["$or"].append({arg: self.get_arg_value_as_type(val)})
                else:
                    query[arg] = self.get_arg_value_as_type(self.request.arguments.get(arg)[0])

        return query

    def arg_as_array(self, arg, split_char="|"):
        """Turns an argument into an array, split by the splitChar

        :param str arg: The name of the query param you want to turn into an array based on the value
        :param str split_char: The character the value should be split on.
        :returns: A list of values
        :rtype: list
        """
        valuesString = self.get_argument(arg, default=None)
        if valuesString:
            valuesArray = valuesString.split(split_char)
            return valuesArray

        return None

    def raise_error(self, status=500, message="Generic server error.  Out of luck..."):
        """
        Sets an error status and returns a message to the user in JSON format

        :param int status: The status code to use
        :param str message: The message to return in the JSON response
        """
        self.set_status(status)
        self.write({"message" : message,
                    "status" : status})

    def unauthorized(self, message="Unauthorized request, please login first"):
        """Standard Unauthorized response

        :param str message: The Message to use in the error response
        """
        self.raise_error(401, message)

    def return_resource(self, resource, status=200, statusMessage="OK"):
        """Return a resource response

        :param str resource: The JSON String representation of a resource response
        :param int status: Status code to use
        :param str statusMessage: The message to use in the error response
        """
        self.set_status(status, statusMessage)
        self.write(json.loads(json_util.dumps(resource)))


    def group_objects_by(self, list, attr, valueLabel="value", childrenLabel="children"):
        """
        Generates a group object based on the attribute value on of the given attr value that is passed in.

        :param list list: A list of dictionary objects
        :param str attr: The attribute that the dictionaries should be sorted upon
        :param str valueLabel: What to call the key of the field we're sorting upon
        :param str childrenLabel: What to call the list of child objects on the group object
        :returns: list of grouped objects by a given attribute
        :rtype: list
        """

        groups = []
        for obj in list:
            val = obj.get(attr)
            if not val:
                pass

            newGroup = {"attribute": attr, valueLabel: val, childrenLabel: [obj]}

            found = False
            for i in range(0,len(groups)):
                if val == groups[i].get(valueLabel):
                    found = True
                    groups[i][childrenLabel].append(obj)
                    pass

            if not found:
                groups.append(newGroup)

        return groups

    def get_current_user(self):
        """Gets the current user from the secure cookie store

        :returns: user name for logged in user
        :rtype: str
        """
        return self.get_secure_cookie(self.settings.get("session_cookie", "user"))

    def write_hyper_response(self, links=[], meta={}, entity_name=None, entity=None, notifications=[], actions=[]):
        """Writes a hyper media response object

        :param list links: A list of links to the resources
        :param dict meta: The meta data for this response
        :param str entity_name: The entity name
        :param object entity: The Entity itself
        :param list notifications: List of notifications
        :param list actions: List of actions
        """
        assert entity_name is not None
        assert entity is not None

        meta.update({
            "status": self.get_status()
        })

        self.write({
            "links": links,
            "meta": meta,
            entity_name: entity,
            "notifications": notifications,
            "actions": actions
        })
