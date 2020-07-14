from __future__ import annotations
import json
import plyvel


class Block:
    """
    Used for retrieving blockchain data from a local citizen node
    and parse the data.
    """
    BLOCK_HEIGHT_KEY = b'block_height_key'
    BLOCK_HEIGHT_BYTES_LEN = 12
    V1_BLOCK_HEIGH = 0
    V3_BLOCK_HEIGHT = 10324749
    V4_BLOCK_HEIGHT = 12640761
    V5_BLOCK_HEIGHT = 14473622

    def __init__(self, height: int, db: Leveldb) -> Block:
        # Parse blockdata into block class.
        # More attributes should be added as needed.
        block = self.get_block(height, db)
        self.db = db
        self.height = height
        
        if height < self.V3_BLOCK_HEIGHT:
            self.transactions = block['confirmed_transaction_list']
            self.timestamp = block['time_stamp']
        else:
            self.transactions = block['transactions']
            self.timestamp = int(block['timestamp'], 16)

    
    def get_block(self, height, db):
        heightkey = self.BLOCK_HEIGHT_KEY + height.to_bytes(self.BLOCK_HEIGHT_BYTES_LEN, byteorder='big')
        blockhash = db.get(heightkey)
        block = json.loads(db.get(blockhash))  # --> TypeError: Argument 'key' has incorrect type (expected bytes, got NoneType)
        return block


    def find_last_block(self) -> int:
        increment = 1000000
        lastblock = 0
        while True:
            try:
                self.get_block(lastblock + increment, self.db)
            except TypeError:
                if increment == 1:
                    return lastblock
                increment = increment // 10
                continue
            lastblock = lastblock + increment


class Transaction:
    """
    Transaction class is used for parsing transaction data, retrieving transaction data from a local citizen node
    and perform various tests on a transaction.
    """
    def __init__(self, transaction: dict, db: Leveldb, blockheight = None, blocktimestamp = None) -> Transaction:
        self.db = db
        self.tested = False
        self.successful = None
        self.raw_transaction = transaction

        # Set blockheight and block_timestamp.
        if blockheight:
            self.blockheight = blockheight
        else:
            self.blockheight = None
        
        if blocktimestamp:
            self.blocktimestamp = blocktimestamp
        else:
            self.blocktimestamp = None

        # Set transaction version.
        try:
            self.version = transaction['version']
        except KeyError:
            self.version = "0x1"

        # Initialize transaction based on different versions.
        if self.version == "0x1":
            self.parse_v1()

        elif self.version == "0x3":
            self.parse_v3()
        
        else:
            raise Exception(f"{self.version} not handled by class.")

    def parse_v1(self):
        """
        Parse version 1 transactions.
        """
        try:
            self.from_ = self.raw_transaction['from']
        except KeyError:
            self.from_ = None
            
        try: 
            self.to = self.raw_transaction['to']
        except KeyError:
            self.to = None

        try:
            self.value = self.raw_transaction['value']
        except KeyError:
            self.value = None

        self.datatype = None
        self.data = None
                
        try:
            self.method = self.raw_transaction['data']['method']
        except KeyError:
            self.method = None

        try:
            self.params = self.raw_transaction['data']['params']
        except KeyError:
            self.params = None

        try:
            self.txhash = self.raw_transaction['tx_hash']
        except KeyError:
            self.txhash = None

    def parse_v3(self):
        """
        Parse version 3 transactions.
        """
        try:
            self.from_ = self.raw_transaction['from']
        except KeyError:
            self.from_ = None

        try: 
            self.to = self.raw_transaction['to']
        except KeyError:
            self.to = None
        
        try:
            self.value = self.raw_transaction['value']
        except KeyError:
            self.value = None
        
        try:
            self.datatype = self.raw_transaction['dataType']
        except KeyError:
            self.datatype = None
        
        try:
            self.data = self.raw_transaction['data']
        except KeyError:
            self.data = None

        try:
            self.method = self.raw_transaction['data']['method']
        except (KeyError, TypeError):
            self.method = None
    
        try:
            self.params = self.raw_transaction['data']['params']
        except (KeyError, TypeError):
            self.params = None

        try:
            self.txhash = self.raw_transaction['txHash']
        except KeyError:
            self.txhash = None

    def convert_units(self) -> None:
        ##TODO
        pass

    def is_from(self, from_: set) -> bool:
        if self.from_ in from_:
            return True
        else:
            return False

    def is_to(self, to: set) -> bool:
        if self.to in to:
            return True
        else:
            return False     

    def has_datatype(self, datatypes: set) -> bool:
        if self.datatype in datatypes:
            return True
        else:
            return False

    def has_method(self, methods: set) -> bool:
        if self.method in methods:
            return True
        else:
            return False

    def has_parameter(self, parameters: set) -> bool:
        try:    
            for param in self.params.keys():
                if param in parameters:
                    return True
        except AttributeError:
            pass
        return False

    def was_successful(self) -> bool:
        if self.get_transaction_result()['result']['status'] == "0x1":
            return True
        else:
            return False

    def fulfills_criteria(self, from_ = None, to = None, datatypes = None,
                          methods = None, params = None) -> bool:
        if from_:
            if not self.is_from(from_):
                return False
        if to:
            if not self.is_to(to):
                return False
        if datatypes:
            if not self.has_datatype(datatypes):
                return False    
        if methods:
            if not self.has_method(methods):
                return False
        if params:
            if not self.has_parameter(params):
                return False
        return True
        
    def get_transaction(self):
        return {"block": self.blockheight, "from": self.from_, "to": self.to, "value": self.value, "datatype": self.datatype,
                "data": self.data, "txhash": self.txhash, "blocktimestamp": self.blocktimestamp}
    
    def get_transaction_result(self):
        """
        Get transaction result from blockchain database.
        Return
           txresult (dict) - transaction result
        """
        return json.loads(self.db.get(self.txhash.encode()))
