"""Utils to initialize and drop the database."""

import logging

from pymongo import ASCENDING, TEXT

from bigchaindb import backend
from bigchaindb.common import exceptions
from bigchaindb.backend.utils import module_dispatch_registrar
from bigchaindb.backend.localmongodb.connection import LocalMongoDBConnection


logger = logging.getLogger(__name__)
register_schema = module_dispatch_registrar(backend.schema)


@register_schema(LocalMongoDBConnection)
def create_database(conn, dbname):
    if dbname in conn.conn.database_names():
        raise exceptions.DatabaseAlreadyExists('Database `{}` already exists'
                                               .format(dbname))

    logger.info('Create database `%s`.', dbname)
    # TODO: read and write concerns can be declared here
    conn.conn.get_database(dbname)


@register_schema(LocalMongoDBConnection)
def create_tables(conn, dbname):
    for table_name in ['transactions', 'assets']:
        logger.info('Create `%s` table.', table_name)
        # create the table
        # TODO: read and write concerns can be declared here
        conn.conn[dbname].create_collection(table_name)


@register_schema(LocalMongoDBConnection)
def create_indexes(conn, dbname):
    create_transactions_secondary_index(conn, dbname)
    create_assets_secondary_index(conn, dbname)


@register_schema(LocalMongoDBConnection)
def drop_database(conn, dbname):
    conn.conn.drop_database(dbname)


def create_transactions_secondary_index(conn, dbname):
    logger.info('Create `transactions` secondary index.')

    # to query the transactions for a transaction id, this field is unique
    conn.conn[dbname]['transactions'].create_index('transactions.id',
                                                   name='transaction_id')

    # secondary index for asset uuid, this field is unique
    conn.conn[dbname]['transactions']\
        .create_index('asset.id', name='asset_id')

    # secondary index on the public keys of outputs
    conn.conn[dbname]['transactions']\
        .create_index('outputs.public_keys',
                      name='outputs')

    # secondary index on inputs/transaction links (transaction_id, output)
    conn.conn[dbname]['transactions']\
        .create_index([
            ('inputs.fulfills.transaction_id', ASCENDING),
            ('inputs.fulfills.output_index', ASCENDING),
        ], name='inputs')


def create_assets_secondary_index(conn, dbname):
    logger.info('Create `assets` secondary index.')

    # unique index on the id of the asset.
    # the id is the txid of the transaction that created the asset
    conn.conn[dbname]['assets'].create_index('id',
                                             name='asset_id',
                                             unique=True)

    # full text search index
    conn.conn[dbname]['assets'].create_index([('$**', TEXT)], name='text')
