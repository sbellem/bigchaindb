import pytest
from unittest.mock import patch

from ..db.conftest import inputs  # noqa


@pytest.mark.usefixtures('inputs')
def test_asset_transfer(b, user_pk, user_sk):
    from bigchaindb.models import Transaction

    tx_input = b.get_owned_ids(user_pk).pop()
    tx_create = b.get_transaction(tx_input.txid)

    tx_transfer = Transaction.transfer(tx_create.to_inputs(), [([user_pk], 1)],
                                       tx_create.asset)
    tx_transfer_signed = tx_transfer.sign([user_sk])

    assert tx_transfer_signed.validate(b) == tx_transfer_signed
    assert tx_transfer_signed.asset.data_id == tx_create.asset.data_id


def test_validate_bad_asset_creation(b, user_pk):
    from bigchaindb.models import Transaction, Asset

    # `divisible` needs to be a boolean
    tx = Transaction.create([b.me], [([user_pk], 1)])
    tx.asset.divisible = 1
    with patch.object(Asset, 'validate_asset', return_value=None):
        tx_signed = tx.sign([b.me_private])
    with pytest.raises(TypeError):
        tx_signed.validate(b)

    # `refillable` needs to be a boolean
    tx = Transaction.create([b.me], [([user_pk], 1)])
    tx.asset.refillable = 1
    with patch.object(Asset, 'validate_asset', return_value=None):
        tx_signed = tx.sign([b.me_private])
    with pytest.raises(TypeError):
        b.validate_transaction(tx_signed)

    # `updatable` needs to be a boolean
    tx = Transaction.create([b.me], [([user_pk], 1)])
    tx.asset.updatable = 1
    with patch.object(Asset, 'validate_asset', return_value=None):
        tx_signed = tx.sign([b.me_private])
    with pytest.raises(TypeError):
        b.validate_transaction(tx_signed)

    # `data` needs to be a dictionary
    tx = Transaction.create([b.me], [([user_pk], 1)])
    tx.asset.data = 'a'
    with patch.object(Asset, 'validate_asset', return_value=None):
        tx_signed = tx.sign([b.me_private])
    with pytest.raises(TypeError):
        b.validate_transaction(tx_signed)


@pytest.mark.usefixtures('inputs')
def test_validate_transfer_asset_id_mismatch(b, user_pk, user_sk):
    from bigchaindb.common.exceptions import AssetIdMismatch
    from bigchaindb.models import Transaction

    tx_create = b.get_owned_ids(user_pk).pop()
    tx_create = b.get_transaction(tx_create.txid)
    tx_transfer = Transaction.transfer(tx_create.to_inputs(), [([user_pk], 1)],
                                       tx_create.asset)
    tx_transfer.asset.data_id = 'aaa'
    tx_transfer_signed = tx_transfer.sign([user_sk])
    with pytest.raises(AssetIdMismatch):
        tx_transfer_signed.validate(b)


def test_get_asset_id_create_transaction(b, user_pk):
    from bigchaindb.models import Transaction, Asset

    tx_create = Transaction.create([b.me], [([user_pk], 1)])
    asset_id = Asset.get_asset_id(tx_create)

    assert asset_id == tx_create.asset.data_id


@pytest.mark.usefixtures('inputs')
def test_get_asset_id_transfer_transaction(b, user_pk, user_sk):
    from bigchaindb.models import Transaction, Asset

    tx_create = b.get_owned_ids(user_pk).pop()
    tx_create = b.get_transaction(tx_create.txid)
    # create a transfer transaction
    tx_transfer = Transaction.transfer(tx_create.to_inputs(), [([user_pk], 1)],
                                       tx_create.asset)
    tx_transfer_signed = tx_transfer.sign([user_sk])
    # create a block
    block = b.create_block([tx_transfer_signed])
    b.write_block(block)
    # vote the block valid
    vote = b.vote(block.id, b.get_last_voted_block().id, True)
    b.write_vote(vote)
    asset_id = Asset.get_asset_id(tx_transfer)

    assert asset_id == tx_transfer.asset.data_id


def test_asset_id_mismatch(b, user_pk):
    from bigchaindb.models import Transaction, Asset
    from bigchaindb.common.exceptions import AssetIdMismatch

    tx1 = Transaction.create([b.me], [([user_pk], 1)])
    tx2 = Transaction.create([b.me], [([user_pk], 1)])

    with pytest.raises(AssetIdMismatch):
        Asset.get_asset_id([tx1, tx2])


@pytest.mark.usefixtures('inputs')
def test_get_transactions_by_asset_id(b, user_pk, user_sk):
    from bigchaindb.models import Transaction

    tx_create = b.get_owned_ids(user_pk).pop()
    tx_create = b.get_transaction(tx_create.txid)
    asset_id = tx_create.asset.data_id
    txs = b.get_transactions_by_asset_id(asset_id)

    assert len(txs) == 1
    assert txs[0].id == tx_create.id
    assert txs[0].asset.data_id == asset_id

    # create a transfer transaction
    tx_transfer = Transaction.transfer(tx_create.to_inputs(), [([user_pk], 1)],
                                       tx_create.asset)
    tx_transfer_signed = tx_transfer.sign([user_sk])
    # create the block
    block = b.create_block([tx_transfer_signed])
    b.write_block(block)
    # vote the block valid
    vote = b.vote(block.id, b.get_last_voted_block().id, True)
    b.write_vote(vote)

    txs = b.get_transactions_by_asset_id(asset_id)

    assert len(txs) == 2
    assert tx_create.id in [t.id for t in txs]
    assert tx_transfer.id in [t.id for t in txs]
    assert asset_id == txs[0].asset.data_id
    assert asset_id == txs[1].asset.data_id


@pytest.mark.usefixtures('inputs')
def test_get_transactions_by_asset_id_with_invalid_block(b, user_pk, user_sk):
    from bigchaindb.models import Transaction

    tx_create = b.get_owned_ids(user_pk).pop()
    tx_create = b.get_transaction(tx_create.txid)
    asset_id = tx_create.asset.data_id
    txs = b.get_transactions_by_asset_id(asset_id)

    assert len(txs) == 1
    assert txs[0].id == tx_create.id
    assert txs[0].asset.data_id == asset_id

    # create a transfer transaction
    tx_transfer = Transaction.transfer(tx_create.to_inputs(), [([user_pk], 1)],
                                       tx_create.asset)
    tx_transfer_signed = tx_transfer.sign([user_sk])
    # create the block
    block = b.create_block([tx_transfer_signed])
    b.write_block(block)
    # vote the block invalid
    vote = b.vote(block.id, b.get_last_voted_block().id, False)
    b.write_vote(vote)

    txs = b.get_transactions_by_asset_id(asset_id)

    assert len(txs) == 1


@pytest.mark.usefixtures('inputs')
def test_get_asset_by_id(b, user_pk, user_sk):
    from bigchaindb.models import Transaction

    tx_create = b.get_owned_ids(user_pk).pop()
    tx_create = b.get_transaction(tx_create.txid)
    asset_id = tx_create.asset.data_id

    # create a transfer transaction
    tx_transfer = Transaction.transfer(tx_create.to_inputs(), [([user_pk], 1)],
                                       tx_create.asset)
    tx_transfer_signed = tx_transfer.sign([user_sk])
    # create the block
    block = b.create_block([tx_transfer_signed])
    b.write_block(block)
    # vote the block valid
    vote = b.vote(block.id, b.get_last_voted_block().id, True)
    b.write_vote(vote)

    txs = b.get_transactions_by_asset_id(asset_id)
    assert len(txs) == 2

    asset = b.get_asset_by_id(asset_id)
    assert asset == tx_create.asset


def test_create_invalid_divisible_asset(b, user_pk, user_sk):
    from bigchaindb.models import Transaction, Asset
    from bigchaindb.common.exceptions import AmountError

    # non divisible assets cannot have amount > 1
    # Transaction.__init__ should raise an exception
    asset = Asset(divisible=False)
    with pytest.raises(AmountError):
        Transaction.create([user_pk], [([user_pk], 2)], asset=asset)

    # divisible assets need to have an amount > 1
    # Transaction.__init__ should raise an exception
    asset = Asset(divisible=True)
    with pytest.raises(AmountError):
        Transaction.create([user_pk], [([user_pk], 1)], asset=asset)

    # even if a transaction is badly constructed the server should raise the
    # exception
    asset = Asset(divisible=False)
    with patch.object(Asset, 'validate_asset', return_value=None):
        tx = Transaction.create([user_pk], [([user_pk], 2)], asset=asset)
        tx_signed = tx.sign([user_sk])
    with pytest.raises(AmountError):
        tx_signed.validate(b)
    assert b.is_valid_transaction(tx_signed) is False

    asset = Asset(divisible=True)
    with patch.object(Asset, 'validate_asset', return_value=None):
        tx = Transaction.create([user_pk], [([user_pk], 1)], asset=asset)
        tx_signed = tx.sign([user_sk])
    with pytest.raises(AmountError):
        tx_signed.validate(b)
    assert b.is_valid_transaction(tx_signed) is False


def test_create_valid_divisible_asset(b, user_pk, user_sk):
    from bigchaindb.models import Transaction, Asset

    asset = Asset(divisible=True)
    tx = Transaction.create([user_pk], [([user_pk], 2)], asset=asset)
    tx_signed = tx.sign([user_sk])
    assert b.is_valid_transaction(tx_signed)
