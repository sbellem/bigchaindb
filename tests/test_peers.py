from collections import defaultdict
from os import environ
from threading import Thread
from time import sleep, time

from pymongo import MongoClient
from pytest import mark


@mark.skipif(environ.get('CI') == 'true',
             reason='Experimental test not ready for CI.')
def test_peers(alice, bob):
    from bigchaindb.models import Transaction
    from bigchaindb.common.crypto import generate_key_pair
    alice, bob = generate_key_pair(), generate_key_pair()

    TX_COUNT = 50
    mdb1 = MongoClient('mdb-1')
    mdb2 = MongoClient('mdb-2')
    mdb3 = MongoClient('mdb-3')

    def gen_tx():
        while True:
            tx_obj = Transaction.create(
                [alice.public_key],
                [([bob.public_key], 1)],
                asset=dict(time=time()),
            )
            tx = tx_obj.sign([alice.private_key]).to_dict()
            yield tx

    mdb2_tx_generator = gen_tx()
    mdb2_tx_batch = (next(mdb2_tx_generator) for _ in range(TX_COUNT))
    mdb3_tx_generator = gen_tx()
    mdb3_tx_batch = (next(mdb3_tx_generator) for _ in range(TX_COUNT))

    peer_txids = defaultdict(list)
    all_txids = []

    def simulate_tx_stream(peer, tx_batch, *, delay=0.1):
        for tx in tx_batch:
            peer.bigchain.backlog.insert_one(tx)
            sleep(delay)
            peer_txids[peer.address].append(tx['id'])
            all_txids.append(tx['id'])

    for peer in (mdb1, mdb2, mdb3):
        peer.bigchain.backlog.delete_many({})
        sleep(0.5)
        assert peer.bigchain.backlog.count() == 0

    mdb2_thread = Thread(target=simulate_tx_stream,
                         args=(mdb2, mdb2_tx_batch),
                         kwargs={'delay': 0.0})
    mdb2_thread.start()
    mdb3_thread = Thread(target=simulate_tx_stream,
                         args=(mdb3, mdb3_tx_batch),
                         kwargs={'delay': 0.0})
    mdb3_thread.start()

    while len(peer_txids[mdb3.address]) != TX_COUNT:
        print('transactions left for fastest node: ' +
              str(TX_COUNT - len(peer_txids[mdb2.address])))
        print('transactions left for slowest node: ' +
              str(TX_COUNT - len(peer_txids[mdb3.address])), end='\n\n')
        sleep(1)
    print(100*'1')
    #timeout = 0
    while (mdb1.bigchain.backlog.count({'version': '1.0'}) < 2*TX_COUNT or
           mdb2.bigchain.backlog.count({'version': '1.0'}) < 2*TX_COUNT or
           mdb3.bigchain.backlog.count({'version': '1.0'}) < 2*TX_COUNT):
        print('mdb1: {}'.format(mdb1.bigchain.backlog.count({'version': '1.0'})))
        print('mdb2: {}'.format(mdb2.bigchain.backlog.count({'version': '1.0'})))
        print('mdb3: {}'.format(mdb3.bigchain.backlog.count({'version': '1.0'})))
        sleep(1)

    print(100*'2')
    # check that mdb-1 is up to date
    assert mdb2.bigchain.backlog.count({'version': '1.0'}) == 2*TX_COUNT
    assert mdb3.bigchain.backlog.count({'version': '1.0'}) == 2*TX_COUNT
    assert mdb1.bigchain.backlog.count({'version': '1.0'}) == 2*TX_COUNT

    #for peer_addr, txids in peer_txids.items():
    #    peer = MongoClient(host=(peer_addr[0]))
    #    for txid in txids:
    #        assert peer.bigchain.backlog.find_one({'id': txid}), txid
    #        assert mdb1.bigchain.backlog.find_one({'id': txid}), txid

    print(100*'3')
    for peer in (mdb1, mdb2, mdb3):
        for txid in all_txids:
            assert peer.bigchain.backlog.find_one({'id': txid}), txid


def test_get_spent():
    from bigchaindb.core import Bigchain
    from bigchaindb.models import Transaction
    from bigchaindb.common.crypto import generate_key_pair
    alice, bob = generate_key_pair(), generate_key_pair()

    b = Bigchain()
    #mdb1 = MongoClient('mdb-1')

    create_tx = Transaction.create(
        [alice.public_key],
        [([alice.public_key], 1)],
        asset=dict(time=time()),
    ).sign([alice.private_key])
    #mdb1.bigchain.backlog.insert_one(create_tx.to_dict())
    b.write_transaction(create_tx)

    assert not b.get_spent_from_backlog(create_tx.id, 0)

    transfer_tx = Transaction.transfer(
        create_tx.to_inputs(),
        [([bob.public_key], 1)],
        asset_id=create_tx.id,
    ).sign([alice.private_key])
    b.write_transaction(transfer_tx)
    #mdb1.bigchain.backlog.insert_one(transfer_tx.to_dict())
    assert b.get_spent_from_backlog(create_tx.id, 0)


def test_simple_double_spend_conflict_detection():
    """By double spend conflict is meant that a syncing node receives a
    double spending transaction from another node. So the question is
    then: which one is "correct"? Two main things need to happen:

        1. Detect the divergence
        2. Resolve the conflict so that the nodes recover consistency

    In this simple test, we setup the syncing node with one transfer
    transaction, and we write to another a conflicting transaction.
    Upon syncing, the syncing node should detect the conflict.

    The test should pass if the conflict is detected.

    The test is NOT concerned with resolving the conflict. This is will
    be treated in a another test.

    """
    from bigchaindb.core import Bigchain
    from bigchaindb.models import Transaction
    from bigchaindb.common.crypto import generate_key_pair
    alice, bob = generate_key_pair(), generate_key_pair()
    carol = generate_key_pair()

    b = Bigchain()
    mdb1 = MongoClient('mdb-1')
    mdb2 = MongoClient('mdb-2')

    create_tx = Transaction.create(
        [alice.public_key],
        [([alice.public_key], 1)],
        asset=dict(time=time()),
    ).sign([alice.private_key])
    print(create_tx.id)
    mdb1.bigchain.backlog.insert_one(create_tx.to_dict())
    #b.write_transaction(create_tx)

    #assert not b.get_spent_from_backlog(create_tx.id, 0)

    transfer_tx = Transaction.transfer(
        create_tx.to_inputs(),
        [([bob.public_key], 1)],
        asset_id=create_tx.id,
    ).sign([alice.private_key])
    print(transfer_tx.id)
    mdb1.bigchain.backlog.insert_one(transfer_tx.to_dict())
    conflicting_transfer_tx = Transaction.transfer(
        create_tx.to_inputs(),
        [([carol.public_key], 1)],
        asset_id=create_tx.id,
    ).sign([alice.private_key])
    print(conflicting_transfer_tx.id)
    #b.write_transaction(transfer_tx)
    #assert b.get_spent_from_backlog(create_tx.id, 0)
    mdb2.bigchain.backlog.insert_one(conflicting_transfer_tx.to_dict())



def test_conflict_res_with_vclocks():
    """
    ..todo: explain the test

    """
    from bigchaindb.core import Bigchain
    from bigchaindb.models import Transaction
    from bigchaindb.common.crypto import generate_key_pair
    alice, bob = generate_key_pair(), generate_key_pair()
    carol = generate_key_pair()

    b = Bigchain()
    mdb1 = MongoClient('mdb-1')
    mdb2 = MongoClient('mdb-2')

    create_tx = Transaction.create(
        [alice.public_key],
        [([alice.public_key], 1)],
        asset=dict(time=time()),
    ).sign([alice.private_key])
    print(create_tx.id)
    mdb1.bigchain.backlog.insert_one(create_tx.to_dict())
    #b.write_transaction(create_tx)

    #assert not b.get_spent_from_backlog(create_tx.id, 0)

    transfer_tx = Transaction.transfer(
        create_tx.to_inputs(),
        [([bob.public_key], 1)],
        asset_id=create_tx.id,
    ).sign([alice.private_key])
    print(transfer_tx.id)
    mdb1.bigchain.backlog.insert_one(transfer_tx.to_dict())
    conflicting_transfer_tx = Transaction.transfer(
        create_tx.to_inputs(),
        [([carol.public_key], 1)],
        asset_id=create_tx.id,
    ).sign([alice.private_key])
    print(conflicting_transfer_tx.id)
    #b.write_transaction(transfer_tx)
    #assert b.get_spent_from_backlog(create_tx.id, 0)
    mdb2.bigchain.backlog.insert_one(conflicting_transfer_tx.to_dict())
