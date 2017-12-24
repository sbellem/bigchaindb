#######################
BigchainDB Server Tests
#######################

## The tests/ Folder

The `tests/` folder is where all the tests for BigchainDB Server live. Most of them are unit tests. Integration tests are in the [`tests/integration/` folder](./integration/).

A few notes:

- [`tests/common/`](./common/) contains self-contained tests only testing
  [`bigchaindb/common/`](../bigchaindb/common/)
- [`tests/backend/`](./backend/) contains tests requiring
  the database backend (RethinkDB or MongoDB)


## Writing Tests

We write unit and integration tests for our Python code using the [pytest](http://pytest.org/latest/) framework. You can use the tests in the `tests/` folder as templates or examples.


## Running Tests

### Running Tests Directly

If you installed BigchainDB Server using `pip install bigchaindb`, then you
didn't install the tests. Before you can run all the tests, you must install
BigchainDB from source. The [`CONTRIBUTING.md` file](../CONTRIBUTING.md) has
instructions for how to do that.

Next, make sure you have RethinkDB or MongoDB running in the background. You
can run RethinkDB using `rethinkdb --daemon` or MongoDB using `mongod --replSet=bigchain-rs`.
If you wish to test with a TLS/SSL enabled MongoDB, use the command
```text
mongod --replSet=bigchain-rs --sslAllowInvalidHostnames --sslMode=requireSSL \
-sslCAFile=bigchaindb/tests/backend/mongodb-ssl/certs/ca.crt \
--sslCRLFile=bigchaindb/tests/backend/mongodb-ssl/certs/crl.pem \
--sslPEMKeyFile=bigchaindb/tests/backend/mongodb-ssl/certs/test_mdb_ssl_cert_and_key.pem
```

The `pytest` command has many options. If you want to learn about all the
things you can do with pytest, see [the pytest
documentation](http://pytest.org/latest/). We've also added a customization to
pytest:

`--database-backend`: Defines the backend to use for the tests. It defaults to
`rethinkdb`
It must be one of the backends available in the [server
configuration](https://docs.bigchaindb.com/projects/server/en/latest/server-reference/configuration.html).

Now you can run all tests using:
```text
py.test -v
```

or, if that doesn't work, try:
```text
python -m pytest -v
```

or:
```text
python setup.py test
```

**Note**: the above pytest commands default to use RethinkDB as the backend. If
you wish to run the tests against MongoDB add the `--database-backend=mongodb`
to the `pytest` command. If you wish to run tests against a TLS/SSL enabled
MongoDB instance (as mentioned above), use the command
```text
pytest -v --database-backend=mongodb-ssl -m bdb_ssl
```


How does `python setup.py test` work? The documentation for [pytest-runner](https://pypi.python.org/pypi/pytest-runner) explains.

The `pytest` command has many options. If you want to learn about all the things you can do with pytest, see [the pytest documentation](http://pytest.org/latest/). We've also added a customization to pytest:


### Running Tests with Docker Compose

You can also use [Docker Compose](https://docs.docker.com/compose/) to run all the tests.

#### With MongoDB as the backend

First, start `MongoDB` in the background:

```text
$ docker-compose up -d mdb
```

then run the tests using:

```text
$ docker-compose run --rm bdb py.test -v
```

If you've upgraded to a newer version of BigchainDB, you might have to rebuild
the images before being able to run the tests. Run:

```text
$ docker-compose build
```

#### With RethinkDB as the backend

First, start `RethinkDB` in the background:

```text
$ docker-compose -f docker-compose.rdb.yml up -d rdb
```

then run the tests using:

```text
$ docker-compose -f docker-compose.rdb.yml run --rm bdb-rdb py.test -v
```

to rebuild all the images (usually you only need to rebuild the `bdb` and
 `bdb-rdb` images). If that fails, then do `make clean-pyc` and try again.

## Automated Testing of All Pull Requests

We use [Travis CI](https://travis-ci.com/), so that whenever someone creates a new BigchainDB pull request on GitHub, Travis CI gets the new code and does *a bunch of stuff*. You can find out what we tell Travis CI to do in [the `.travis.yml` file](.travis.yml): it tells Travis CI how to install BigchainDB, how to run all the tests, and what to do "after success" (e.g. run `codecov`). (We use [Codecov](https://codecov.io/) to get a rough estimate of our test coverage.)


### Tox

We use [tox](https://tox.readthedocs.io/en/latest/) to run multiple suites of tests against multiple environments during automated testing. Generally you don't need to run this yourself, but it might be useful when troubleshooting a failing Travis CI build.

To run all the tox tests, use:
```text
tox
```

or:
```text
python -m tox
```

To run only a few environments, use the `-e` flag:
```text
tox -e {ENVLIST}
```

where `{ENVLIST}` is one or more of the environments specified in the [tox.ini file](../tox.ini).
