import argparse
import configparser
from blockchain import Block
from blockchain import Transaction
import csv
import json
import plyvel
import signal
import time
from threading import Timer, Thread
import datetime
import os
import sys
from tqdm import tqdm
from txfile import TxFile


COLUMNS = ["block", "from", "to", "value", "datatype", "data", "txhash", "blocktimestamp"]
INTERVAL = 30
CONFIG = "./itx.ini"


#Get default arguments from file.
config = configparser.ConfigParser()
config.read(CONFIG)
df_args = dict(config['DEFAULT'])

OUTPUT = df_args['output']
LEVELDB = df_args['leveldb']

def main():
    
    # Create parser object.
    parser = argparse.ArgumentParser(prog = "itx",
                                     usage = "python3 itx <command> <arguments>",
                                     description = "Tool for traversing and extracting transactions from " 
                                                   "ICON blockchain using userspecified rules. ",
                                     add_help = True)

    #parser.add_argument('--help', '-h', action = "store_true")
    

    # Add subparser to main parser object.
    subparsers = parser.add_subparsers(title = "commands",
                                       prog = "python3")


    # Create parser for initialize.
    parser_initialize = subparsers.add_parser('init',
                                           usage = 'python3 itx.py initialize <arguments>',
                                           help = 'Creates a file with specified name and saves extractions rules '
                                                  'for that file.',
                                           add_help = True)

    parser_initialize._action_groups.pop()
    required_init = parser_initialize.add_argument_group('required arguments')
    optional_init = parser_initialize.add_argument_group('optional arguments')
    
    required_init.add_argument('--file', type = str, required = True, metavar = "<file>",
                                help = "Filename for transaction storage. Csv file.")
    
    optional_init.add_argument('--from', metavar = '<addr>', type = str, nargs = "+", dest = "from_",
                                action = CustomAction1, default = [], 
                                help = "Sending addresses. It's possible to give a .txt file as an argument to this option. "
                                       "Each address should be on a new line.")

    optional_init.add_argument('--to', metavar = '<addr>', type = str, nargs = "+",
                                action = CustomAction1, default = [], 
                                help = "Recieving addresses. It's possible to give a .txt file as an argument to this option. "
                                       "Each address should be on a new line.")

    optional_init.add_argument('--datatypes', metavar = '<datatypes>', type=str,
                                nargs = '+', help='Transaction datatypes.', default = [])

    optional_init.add_argument('--methods', metavar = '<methods>', type = str, nargs = "+",
                                help = "Transaction method called", default = [])

    optional_init.add_argument('--params', metavar = '<paramaters>', type = str, nargs = "+", 
                                help = 'Parameters in method call.', default = [])

    optional_init.add_argument('--columns', metavar = '<columns>', choices = COLUMNS, type = str, nargs = "+",
                                   help = 'Table structure in file.', default = COLUMNS)

    optional_init.add_argument('--include-failed-transactions', action = 'store_true', dest = "include_failed_tx",
                                help = "By default only successful transactions are extracted. "
                                       "With this option there will be no test if transactions where successful or not. "
                                       "Both successful and failed transactions will be included, "
                                       "without a way to differetiate the two. "
                                       "This option will increase the extraction speed by many factors if your rules "
                                       "target many transactions.")

    parser_initialize.set_defaults(func = initialize)

    # Create parser for extract.
    parser_extract = subparsers.add_parser('extract',
                                            usage = 'python3 itx.py extract <arguments>',
                                            help = 'Extracts transactions from a specified block interval to the specified files. '
                                                   'Transactions are extracted as per the rules '
                                                   'specified when the file was initialized.',
                                            add_help = True)

    parser_extract._action_groups.pop()
    required_extract = parser_extract.add_argument_group('required arguments')
    optional_extract = parser_extract.add_argument_group('optional arguments')

    required_extract.add_argument('--files', type = str, required = True, nargs = "+", metavar =  "<files>",
                                help = "File to store extracted transactions in.")
    
    required_extract.add_argument('--first-block', type = int, metavar = "<block>", required = True, dest = "firstblock",
                                help = 'First block to extraction from.')

    required_extract.add_argument('--last-block', type = int, metavar = "<block>", required = True, dest = "lastblock",
                                help = "Last block to extract from.")
    
    parser_extract.set_defaults(func = extract)

    
    # Create parser for update command.
    parser_update = subparsers.add_parser('update', 
                                          usage = "python3 itx update <arguments>",
                                          help = 'Update files to the specified blockheight. '
                                                 'Only use this command if you have previously used the '
                                                 'extraction command on the file/files. '
                                                 'Transactions are extracted as per the rules '
                                                 'specified when the file was initialized.',
                                          add_help = True)

    parser_update.add_argument('--files', type = str, required = True, nargs = "+",
                                help = "Files to update.")

    parser_update.add_argument('--last-block', type = int, metavar = "<block>", dest = "lastblock",
                                help = 'Update files up to this block.')    

    parser_update.set_defaults(func = update)

#    # Create parser for syncronize command.
#    parser_syncronize = subparsers.add_parser('syncronize',
#                                              usage='python3 itx.py syncronize [options] <file>',
#                                              help='Keep files syncronized via RPC.',
#                                              add_help=True)


    # Create parser for remove command.
    parser_remove = subparsers.add_parser('remove',
                                           usage = 'python3 itx.py remove <arguments>',
                                           help = 'Remove specified files and their configuration.',
                                           add_help=True)
    
    mutally_exclusive = parser_remove.add_mutually_exclusive_group()
    mutally_exclusive.add_argument('--files', type = str, nargs = "+", help = "Files to remove, including their configurations.")
    mutally_exclusive.add_argument('--all', action = 'store_true', help = 'Remove all files and their configuration.')

    parser_remove.set_defaults(func = remove)

    # Create parser for status command.
    parser_status = subparsers.add_parser('status',
                                          usage='python3 itx.py status <arguments>',
                                          help='Check status for all tracked files.',
                                          add_help=True)
    
    parser_status.add_argument('--files', type = str, nargs = "+", help = "File(s) for status check.")

    parser_status.set_defaults(func = status)
    # Custom helpfile
    #if namespace.help:
    #	with open('help_file.txt', 'r') as f:
    #		content = f.read()
    #       print(content)

    args = parser.parse_args()
    args.func(args)

def initialize(args):

    # Check if outputfolder exists -> create if not.
    if not os.path.isdir(OUTPUT):
    	os.makedirs(OUTPUT)

    # Check if filetype specified.
    if not args.file.endswith(".csv"):
        print("Did you forget to specify filetype? Only .csv files are supported.")
        sys.exit(1)
    
    # Handle file already exists.
    filepath = OUTPUT + args.file
    if os.path.exists(filepath):
        while True:
            response = input(f"{args.file} already exists. Overwrite? (Y/n): ")
            if response in ["Y", "y", ""]:
                os.remove(filepath)
                break
            
            elif response in ["N", "n"]:
                print("Aborting program.")
                sys.exit(2)
            
            else:
                continue
    
    # Initialize txfile with its extraction settings.
    txfile = TxFile(name = args.file, folder = OUTPUT, inifile = CONFIG, from_ = args.from_,
                    to = args.to, datatypes = args.datatypes, methods = args.methods, params = args.params,
                    columns = args.columns, include_failed_tx = args.include_failed_tx)
   
    # Save settings to configuration file.
    txfile.delete_config()
    txfile.save_config()

    # Create file and write header row to file.
    txfile.create_file()
    txfile.open('w')
    txfile.write_header_row()
    txfile.close()

def extract(args):

    # Ignore genesisblock.
    if args.firstblock == 0:
        args.firstblock = 1
        print("- Genesisblock ignored.")

    # Open local blockchaindb.
    plyveldb = plyvel.DB(LEVELDB, create_if_missing = False)
    
    # Prepare list of TxFile objects.
    txfiles = []
    for file in args.files:
        txfile = TxFile(name = file, inifile = CONFIG)
        txfile.load_config()
        txfile.firstblock = args.firstblock
        txfile.set_rules()
        txfile.open('a')
        txfiles.append(txfile)

    print("Extracting transactions...")
    
    # Extract all transactions form each block.
    loop_broken = False
    counter = -1
    flag = GracefulExiter()
    for block in tqdm(range(args.firstblock, args.lastblock + 1), mininterval = 1, unit = "blocks"):
        try:
            block = Block(block, plyveldb)
        except TypeError:
            loop_broken = True
            break
        transactions = block.transactions
        
        # Test each transaction against rules.
        for transaction in transactions:
            transaction = Transaction(transaction, plyveldb, blockheight = block.height, blocktimestamp = block.timestamp)
            
            for txfile in txfiles:    
                if not transaction.fulfills_criteria(**txfile.rules):
                    continue

                if not txfile.include_failed_tx:
                    if not transaction.was_successful():
                        continue

                # Write to file if all tests passed
                txfile.append_transaction(transaction.get_transaction())
                txfile.transactions += 1
        
        counter += 1

        if flag.exit():
            break

    if loop_broken:
        print(f"Block {block} not found in database. Ending extraction ...")

    # Update config and close files 
    for txfile in txfiles:
        txfile.lastblock = txfile.firstblock + counter
        txfile.save_config()
        txfile.close() 
    plyveldb.close()
    
    if flag.exit():
        print("Exited gracefully.")

def update(args):

    # Open local leveldb blockchain database.
    plyveldb = plyvel.DB(LEVELDB, create_if_missing = False)

    # Prepare list of TxFile objects.
    txfiles = []
    for file in args.files:
        txfile = TxFile(name = file, inifile = CONFIG)
        txfile.load_config()
        txfile.set_rules()
        txfile.open('a')
        txfiles.append(txfile)

    # Find lowest blockheight among txfiles.
    block_heights = []
    for txfile in txfiles:
        block_heights.append(txfile.lastblock)
    lowest_blockheight = min(block_heights)

    # Starting block for extraction.
    startblock = lowest_blockheight + 1

    # If not lastblock specified -> find latest blockheight available in blockchain database.
    if not args.lastblock:
        block = Block(2, plyveldb)
        lastblock = block.find_last_block()
    else:
        lastblock = args.lastblock

    # Extract transactions.
    print("Updating files with new transactions...")
    flag = GracefulExiter()
    for block in tqdm(range(startblock, lastblock + 1), mininterval = 1, unit = "blocks"):
        block = Block(block, plyveldb)
        transactions = block.transactions

        for transaction in transactions:
            transaction = Transaction(transaction, plyveldb, blockheight = block.height, blocktimestamp = block.timestamp)
            
            # ===Inefficiency here===
            for txfile in txfiles:
                if txfile.lastblock != lowest_blockheight:
                    continue
                
                if not transaction.fulfills_criteria(**txfile.rules):
                    continue

                if not txfile.include_failed_tx:
                    if not transaction.was_successful():
                        continue
                
                txfile.append_transaction(transaction.get_transaction())
                txfile.transactions += 1
        
        # Update blockheights of txfiles.
        for txfile in txfiles:
            if txfile.lastblock == lowest_blockheight:
                txfile.lastblock +=1
        
        # New lowest blockheight among txfiles.
        lowest_blockheight += 1

        # Break here if ctrl + c.
        if flag.exit():
            break

    # Update config and close files.
    for txfile in txfiles:
        txfile.lastblock = lowest_blockheight
        txfile.save_config()
        txfile.close() 
    plyveldb.close()

    if flag.exit():
        print("Exited gracefully.")


def remove(args) -> None:
    """
    Remove file from output directory and clear configurations for that file itx.ini.
    """
    config = configparser.ConfigParser()
    config.read(CONFIG)
    
    if args.all:
        txfiles = config.sections()

    else:
        txfiles = args.files

    for txfile in txfiles:
        txfile = TxFile(name = txfile, inifile = CONFIG)
        txfile.load_config()
        txfile.delete_file()
        txfile.delete_config()

def syncronize():
    ## TODO
    pass


def status(args) -> None:
    """
    Print status of transaction files.
    """
    if  args.files:
        txfiles = args.files
    else:
        config = configparser.ConfigParser()
        config.read(CONFIG)
        txfiles = config.sections()

    for txfile in txfiles:
        txfile = TxFile(name = txfile, inifile = CONFIG)
        txfile.load_config()
        txfile.print_status()


def proceed() -> bool:
    """
    Ask to prooceed with extraction or not
    """
    while True:
        response = input("::Proocced with extraction ([y]/n)?")
        if response in ["Y", "y", ""]:
            return True
        elif response in ["N", "n"]:
            return False
        else:
            continue
        

class GracefulExiter():

    def __init__(self):
        self.state = False
        signal.signal(signal.SIGINT, self.change_state)

    def change_state(self, signum, frame):
        self.state = True

    def exit(self):
        return self.state


class ProgressTracker(Thread):

    def __init__(self, start_block, end_block, report_interval = 60):
        Thread.__init__(self)
        self.start_time = time.time()
        self.start_block = start_block
        self.end_block = end_block
        self.block_counter = 0
        self.transaction_counter = 0
        self.blockheight_last_report = start_block
        self.report_interval = report_interval


    def run(self):
        while True:
            time.sleep(self.report_interval)
            self.report_progress()
            self.blockheight_last_report = self.block_counter


    def report_progress(self):
        print("Progress report")
        print("---------------")
        print(f"Runtime:                           {self.runtime()}")
        print(f"Speed:                             {self.speed()} b/s")
        print(f"Blocks:                            {self.block_counter}/{self.end_block}  ")
        print(f"Transactions:                      {self.transaction_counter}  ")
        print(f"Eta:                               {self.eta()}  ")


    def report_summary(self):
        print("End report")
        print("---------------")
        print(f"Finnished in:                      {self.runtime()}")
        print(f"Blocks processed:                  {self.start_block}-{self.start_block + self.block_counter}")
        print(f"Transactions written to file:      {self.transaction_counter}")


    def runtime(self):
        return datetime.timedelta(seconds(time.time() - self.start_time))


    def speed(self):
        return round((self.block_counter - self.blockheight_last_report) / 60)


    def eta(self):
        return datetime.timedelta(seconds(args.last-block - self.block_counter) / self.speed())


# Check if file was entered as argument.
# Return list.
class CustomAction1(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        if values[0].endswith(".txt"):
            values_2 = []
            with open(values[0], 'r') as fileobj:
                for line in fileobj:
                    values_2.append(line.rstrip())
            setattr(namespace, self.dest, values_2)
        else:
            setattr(namespace, self.dest, values)


# Convert argument to set
class CustomAction2(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        setattr(namespace, self.dest, set(values))


if __name__ == '__main__':
    main()
