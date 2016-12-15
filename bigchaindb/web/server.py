"""This module contains basic functions to instantiate the BigchainDB API.

The application is implemented in Flask and runs using Gunicorn.
"""

import copy
import multiprocessing

from flask import Flask
import gunicorn.app.base

from bigchaindb import util
from bigchaindb import Bigchain
from bigchaindb.web.views.info import info_views
from bigchaindb.web.views.transactions import transaction_views
from bigchaindb.web.views.unspents import unspent_views

from bigchaindb.monitor import Monitor


# TODO: Figure out if we do we need all this boilerplate.
class StandaloneApplication(gunicorn.app.base.BaseApplication):
    """Run a **wsgi** app wrapping it in a Gunicorn Base Application.

    Adapted from:
     - http://docs.gunicorn.org/en/latest/custom.html
    """

    def __init__(self, app, options=None):
        '''Initialize a new standalone application.

        Args:
            app: A wsgi Python application.
            options (dict): the configuration.

        '''
        self.options = options or {}
        self.application = app
        super(StandaloneApplication, self).__init__()

    def load_config(self):
        config = dict((key, value) for key, value in self.options.items()
                      if key in self.cfg.settings and value is not None)

        for key, value in config.items():
            # not sure if we need the `key.lower` here, will just keep
            # keep it for now.
            self.cfg.set(key.lower(), value)

    def load(self):
        return self.application


def create_app(*, debug=False, threads=4):
    """Return an instance of the Flask application.

    Args:
        debug (bool): a flag to activate the debug mode for the app
            (default: False).
        threads (int): number of threads to use
    Return:
        an instance of the Flask application.
    """

    app = Flask(__name__)

    app.debug = debug

    app.config['bigchain_pool'] = util.pool(Bigchain, size=threads)
    app.config['monitor'] = Monitor()

    app.register_blueprint(info_views, url_prefix='/')
    app.register_blueprint(transaction_views, url_prefix='/api/v1')
    app.register_blueprint(unspent_views, url_prefix='/api/v1')
    return app


def create_server(settings):
    """Wrap and return an application ready to be run.

    Args:
        settings (dict): a dictionary containing the settings, more info
            here http://docs.gunicorn.org/en/latest/settings.html

    Return:
        an initialized instance of the application.
    """

    settings = copy.deepcopy(settings)

    if not settings.get('workers'):
        settings['workers'] = (multiprocessing.cpu_count() * 2) + 1

    if not settings.get('threads'):
        settings['threads'] = (multiprocessing.cpu_count() * 2) + 1

    app = create_app(debug=settings.get('debug', False),
                     threads=settings['threads'])
    standalone = StandaloneApplication(app, settings)
    return standalone
