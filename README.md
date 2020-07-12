# ITX - Icon Transaction Extractor
This is a command line tool for traversing the blockchain and extracting transactions according to userspecified rules.

## Prerequisites
- A local copy of Icon's blockchain (see the "Accuire a local copy of the blockchain database" section for instructions).
- Program is only tested on Linux.

## Installation
Clone the project and install required packages.
```
git clone https://github.com/Transcranial-Solutions/itx.git
pip install -r requirements.txt
```

## Configuration
Open ./itx.ini and specify where your local blockchain database is located with the leveldb option.

```
[DEFAULT]
leveldb = <enter_path_to_blockchain_database_here>   <-- Edit this.
output = data/output
```

## Usage
```
usage: python3 itx <command> <arguments>

Tool for traversing and extracting transactions from ICON blockchain using
userspecified rules.

optional arguments:
  -h, --help            show this help message and exit

commands:
  {init,extract,update,remove,status}
    init                Creates a file with specified name and saves
                        extractions rules for that file.
    extract             Extracts transactions from a specified block interval
                        to the specified files. Transactions are extracted as
                        per the rules specified when the file was initialized.
    update              Update files to the specified blockheight. Only use
                        this command if you have previously used the
                        extraction command on the file/files. Transactions are
                        extracted as per the rules specified when the file was
                        initialized.
    remove              Remove specified files and their configuration.
    status              Check status for all tracked files.

```

## Example
Imagine you would like to investigate if P-reps lowering their irep had an impact on the vote distribution. To do this, you would need all voting transactions and all transactions where p-reps change their i-rep. In this example we will extract those transactions into two seperate .csv files.

#### 1. Initialize files
First, we create the two files and specify the extraction rules for each file. 
```
python3 itx.py init --to cx0000000000000000000000000000000000000000  --methods setDelegation --file delegations.csv
python3 itx.py init --to cx0000000000000000000000000000000000000000 --methods setGovernanceVariables --params irep --file irep.csv
```
The standard output directory for files is "./data/output/". 

To review your rules you can use the "status" command.
```
python3 itx.py status
```

#### 2. Extraction
Next, we start the extraction. The following command tells the program to traverse blocks 11000000 - 20000000 and compare all transactions to the rules we specified. If a transaction matches the rules for a file, it is appended to that file.
```
python3 itx.py extract --first-block 11000000 --last-block 20000000 --files delegations.csv irep.csv
```

#### 3. Updating files
Assume some time passes and the blockheight increases to 21000000 and you would like to include new transactions into these files. Then you would use the "update" command.
```
python3 itx.py update --files delegations.csv irep.csv
```
If you do not specify the option --last-block, the last available block in your local database will be the default.

## Limitations
- You will need to turn off your node while you are extracting from it. Seems to be a limitation with leveldb.
- If you wish to remove files -> use the remove command. Otherwise the configuration file won't be accurate.
- If you wish to move files -> edit the configuration file accordingly. Otherwise you will break tracking of those files.

## Accuire a local copy of the blockchain database.
Here you have two options. Either set up a local citizen node or download a snapshot of the blockchain. The first option would be more suitable if you would like to keep your extracted transaction data up to date over time. The second option would suffice if you just want some transaction data up to the current point in time.

#### Option 1 - run local citizen node
Follow the instruction on https://www.icondev.io/docs/quickstart. Note that a citizen node does not requirem P-rep registartion.

#### Option 2 - download a snapshot
1. Copy the latest snapshot from this list of snapshots: https://s3.ap-northeast-2.amazonaws.com/icon-leveldb-backup/MainctzNet/backup_list

2. Replace "backup_list" in the previous url with the snapshot you copied.

3. Paste the url into your browser or use a tool such as wget to download.

4. Unpack the database.

## Acknowledgements
Inspiration gathered from Icon P-rep Yudus-lab's chainlytics framework: https://github.com/yudus-lab/chainalytic-framework.
He also provided valuable insight into how to pull data from a local node. Thank you.

## Contact
Feel free to reach out to me at tskyvell@gmail.com.