from time import time

from pymongo import ReturnDocument

from bigchaindb.backend import query
from bigchaindb.common.exceptions import CyclicBlockchainError
from bigchaindb.backend.mongodb.connection import MongoDBConnection


@query.write_transaction.register(MongoDBConnection)
def write_transaction(conn, signed_transaction):
    return conn.db['backlog'].insert_one(signed_transaction)


@query.update_transaction.register(MongoDBConnection)
def update_transaction(conn, transaction_id, doc):
    return conn.db['backlog']\
            .find_one_and_update({'id': transaction_id},
                                 doc,
                                 return_document=ReturnDocument.AFTER)


@query.delete_transaction.register(MongoDBConnection)
def delete_transaction(conn, *transaction_id):
    return conn.db['backlog'].delete_many({'id': {'$in': transaction_id}})


@query.get_stale_transactions.register(MongoDBConnection)
def get_stale_transactions(conn, reassign_delay):
    return conn.db['backlog']\
            .find({'assignment_timestamp': {'$lt': time() - reassign_delay}})


@query.get_transaction_from_block.register(MongoDBConnection)
def get_transaction_from_block(conn, block_id, tx_id):
    # this is definitely wrong, but it's something like this
    return conn.db['bigchain'].find_one({'id': block_id,
                                         'block.transactions.id': tx_id})


@query.get_transaction_from_backlog.register(MongoDBConnection)
def get_transaction_from_backlog(conn, transaction_id):
    return conn.db['backlog'].find_one({'id': transaction_id})


@query.get_blocks_status_from_transaction.register(MongoDBConnection)
def get_blocks_status_from_transaction(conn, transaction_id):
    return conn.db['bigchain']\
            .find({'block.transactions.id': transaction_id},
                  projection=['id', 'block.voters'])


@query.get_txids_by_asset_id.register(MongoDBConnection)
def get_txids_by_asset_id(conn, asset_id):
    return conn.db['bigchain']\
            .find({'block.transactions.asset.id': asset_id},
                  projection=['id'])


@query.get_asset_by_id.register(MongoDBConnection)
def get_asset_by_id(conn, asset_id):
    return conn.db['bigchain']\
            .find_one({'block.transactions.asset.id': asset_id,
                       'block.transactions.asset.operation': 'CREATE'},
                      projection=['block.transactions.asset'])


@query.get_spent.register(MongoDBConnection)
def get_spent(conn, transaction_id, condition_id):
    return conn.db['bigchain']\
            .find_one({'block.transactions.fulfillments.input.txid':
                       transaction_id,
                       'block.transactions.fulfillments.input.cid':
                       condition_id})


@query.get_owned_ids.register(MongoDBConnection)
def get_owned_ids(conn, owner):
    return conn.db['bigchain']\
            .find({'block.transactions.transaction.conditions.owners_after':
                   owner})


@query.get_votes_by_block_id.register(MongoDBConnection)
def get_votes_by_block_id(conn, block_id):
    return conn.db['votes']\
            .find({'vote.voting_for_block': block_id})


@query.get_votes_by_block_id_and_voter.register(MongoDBConnection)
def get_votes_block_id_and_voter(conn, block_id, node_pubkey):
    return conn.db['votes']\
            .find({'vote.voting_for_block': block_id,
                   'node_pubkey': node_pubkey})


@query.write_block.register(MongoDBConnection)
def write_block(conn, block):
    return conn.db['bigchain'].insert_one(block.to_dict())


@query.get_block.register(MongoDBConnection)
def get_block(conn, block_id):
    return conn.db['bigchain'].find_one({'id': block_id})


@query.has_transaction.register(MongoDBConnection)
def has_transaction(conn, transaction_id):
    return bool(conn.db['bigchain']
                .find_one({'block.transactions.id': transaction_id}))


@query.count_blocks.register(MongoDBConnection)
def count_blocks(conn):
    return conn.db['bigchain'].count()


@query.count_backlog(MongoDBConnection)
def count_backlog(conn):
    return conn.db['backlog'].count()


@query.write_vote.register(MongoDBConnection)
def write_vote(conn, vote):
    return conn.db['votes'].insert_one(vote)


@query.get_genesis_block.register(MongoDBConnection)
def get_genesis_block(conn):
    return conn.db['bigchain'].find_one({'block.transactions.0.operation' ==
                                         'GENESIS'})


@query.get_last_voted_block.register(MongoDBConnection)
def get_last_voted_block(conn, node_pubkey):
    last_voted = conn.db['votes']\
                  .find({'node_pubkey': node_pubkey},
                        sort=[('vote.timestamp', -1)])
    if not last_voted:
        return get_genesis_block(conn)

    mapping = {v['vote']['previous_block']: v['vote']['voting_for_block']
               for v in last_voted}

    last_block_id = list(mapping.values())[0]

    explored = set()

    while True:
        try:
            if last_block_id in explored:
                raise CyclicBlockchainError()
            explored.add(last_block_id)
            last_block_id = mapping[last_block_id]
        except KeyError:
            break

    return get_block(conn, last_block_id)


@query.get_unvoted_blocks.register(MongoDBConnection)
def get_unvoted_blocks(conn, node_pubkey):
    pass
