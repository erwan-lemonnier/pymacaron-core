import pprint
import logging
from klue.swagger.api import API
from klue.exceptions import MergeApisException
from bravado_core.spec import Spec


log = logging.getLogger(__name__)


apis = {}


class ApiPool():
    """Store a pool of API objects, each describing one Swagger API.

    USAGE:

    To load an API:
      api = ApiPool.add('klue', 'klue-api.yaml')

    This will generate model classes for all definitions in the YAML spec.

    To get this api from the pool, as an API object (see swagger.api):
      api = ApiPool.klue

    To instantiate one of the model object:
      api.model.Credentials(user='foo', password='bar')

    To spawn all routes associated with the server side of that API:
      api.spawn_api(flask_app)

    To call a remote server endpoint from within the client:
      param = api.model.Param(..)
      result = api.client.server_method(param)

    Where result is an instance of the model returned by the endpoint
    bound to 'server_method' according to the 'x-bind-client' key in
    the YAML file.
    """

    @classmethod
    def add(self, name, **kwargs):
        api = API(name, **kwargs)
        global apis
        apis[name] = api
        setattr(ApiPool, name, api)
        return api

    @property
    def current_server_name(self):
        for name, api in apis.iteritems():
            if api.is_server:
                return name
        return ''

    @property
    def current_server_api(self):
        for name, api in apis.iteritems():
            if api.is_server:
                return api
        return None

    @classmethod
    def merge(self):
        """Try merging all the bravado_core models across all loaded APIs. If
        duplicates occur, use the same bravado-core model to represent each, so
        bravado-core won't treat them as different models when passing them
        from one Klue client stub to an other or when returning them via the
        Klue server stub.
        """

        # The sole purpose of this method is to trick isinstance to return true
        # on model_values of the same kind but different apis/specs at:
        # https://github.com/Yelp/bravado-core/blob/4840a6e374611bb917226157b5948ee263913abc/bravado_core/marshal.py#L160

        log.info("Merging models of apis " + ", ".join(apis.keys()))

        # model_name => (api_name, model_json_def, bravado_core.model.MODELNAME)
        models = {}

        # First pass: find duplicate and keep only one model of each (fail if
        # duplicates have same name but different definitions)
        for api_name, api in apis.iteritems():
            for model_name, model_def in api.api_spec.swagger_dict['definitions'].iteritems():
                if model_name in models:
                    other_api_name, other_model_def, _ = models.get(model_name)
                    log.info("Model %s in %s is a duplicate of one in %s" % (model_name, api_name, other_api_name))
                    if cmp(model_def, other_model_def) != 0:
                        raise MergeApisException("Cannot merge apis! Model %s exists in apis %s and %s but have different definitions:\n[%s]\n[%s]"
                                                 % (model_name, api_name, other_api_name, pprint.pformat(model_def), pprint.pformat(other_model_def)))
                else:
                    models[model_name] = (api_name, model_def, api.api_spec.definitions[model_name])

        # Second pass: patch every models and replace with the one we decided
        # to keep
        log.info("Patching api definitions to remove all duplicates")
        for api_name, api in apis.iteritems():
            for model_name in api.api_spec.definitions.keys():
                _, _, model_class = models.get(model_name)
                api.api_spec.definitions[model_name] = model_class
