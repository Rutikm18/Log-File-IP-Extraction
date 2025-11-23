import re
import ipaddress
import os
import logging
from typing import Set, Tuple, List
from concurrent.futures import ProcessPoolExecutor, as_completed
from pymongo.mongo_client import MongoClient
from pymongo.operations import UpdateOne
import time

class IPExtractor:
    """Efficient and robust IP address extraction from log files with MongoDB storage."""
    
    # Comprehensive private network ranges
    PRIVATE_NETWORKS = [
        ipaddress.ip_network('10.0.0.0/8'),
        ipaddress.ip_network('172.16.0.0/12'),
        ipaddress.ip_network('192.168.0.0/16')
    ]
    
    # Advanced IP matching regex
    IP_PATTERN = re.compile(
        rb'\b(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}'
        rb'(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\b'
    )
    
    @classmethod
    def validate_ip(cls, ip: str) -> bool:
        """Validate and check IP address."""
        try:
            ip_obj = ipaddress.ip_address(ip)
            return not (
                ip_obj.is_unspecified or 
                ip_obj.is_reserved or 
                ip_obj.is_multicast
            ) and any(ip_obj in network for network in cls.PRIVATE_NETWORKS)
        except ValueError:
            return False
    
    @classmethod
    def extract_ips_from_file(
        cls,
        file_path: str,
        chunk_size: int = 1024 * 1024
    ) -> Tuple[List[str], List[str]]:
        """Extract IPs from log file."""
        # Validate file
        if not os.path.isfile(file_path) or os.path.getsize(file_path) == 0:
            logging.error(f"Invalid file: {file_path}")
            return [], []
        
        private_ips, public_ips = set(), set()
        
        try:
            with open(file_path, 'rb') as file:
                with ProcessPoolExecutor() as executor:
                    # Process file in chunks
                    futures = []
                    while True:
                        chunk = file.read(chunk_size)
                        if not chunk:
                            break
                        
                        futures.append(executor.submit(cls._process_chunk, chunk))
                    
                    # Collect results
                    for future in as_completed(futures):
                        chunk_private, chunk_public = future.result()
                        private_ips.update(chunk_private)
                        public_ips.update(chunk_public)
        except Exception as e:
            logging.error(f"Processing error: {e}")
            return [], []
        
        return sorted(list(private_ips)), sorted(list(public_ips))
    
    @classmethod
    def _process_chunk(cls, chunk: bytes) -> Tuple[Set[str], Set[str]]:
        """
        Process a chunk of log file data.
        
        Args:
            chunk (bytes): File chunk to process
        
        Returns:
            Tuple of private and public IP sets
        """
        private_ips, public_ips = set(), set()
        
        # Extract unique IPs
        ips = set(ip.decode('utf-8', errors='ignore')
                  for ip in cls.IP_PATTERN.findall(chunk))
        
        # Classify IPs
        for ip in ips:
            (private_ips if cls.validate_ip(ip) else public_ips).add(ip)
        
        return private_ips, public_ips

def connect_to_mongodb(uri: str, database: str = 'ip_extraction', 
                       private_collection: str = 'private_ips', 
                       public_collection: str = 'public_ips',
                       max_retries: int = 5,
                       retry_delay: int = 5):
    """
    Establish a connection to MongoDB with retry logic and return client and collections.
    
    Args:
        uri (str): MongoDB connection URI
        database (str): Database name
        private_collection (str): Collection name for private IPs
        public_collection (str): Collection name for public IPs
        max_retries (int): Maximum number of connection retry attempts
        retry_delay (int): Delay in seconds between retry attempts
    
    Returns:
        Tuple of (MongoClient, private collection, public collection)
    """
    for attempt in range(max_retries):
        try:
            # Create a new client and connect to the server
            # Use serverSelectionTimeoutMS for better connection handling
            client = MongoClient(
                uri, 
                serverSelectionTimeoutMS=5000,
                connectTimeoutMS=5000,
                socketTimeoutMS=5000
            )
            
            # Verify the connection
            client.admin.command('ping')
            logging.info(f"Successfully connected to MongoDB! (URI: {uri})")
            
            # Get or create database and collections
            db = client[database]
            private_coll = db[private_collection]
            public_coll = db[public_collection]
            
            # Create unique indexes for better query performance and uniqueness
            # This ensures only unique IPs are stored
            try:
                private_coll.create_index("ip", unique=True)
                public_coll.create_index("ip", unique=True)
                logging.info("Created unique indexes on IP fields")
            except Exception as index_error:
                # Index might already exist, which is fine
                logging.debug(f"Index creation note: {index_error}")
            
            logging.info(f"Using database: {database}, collections: {private_collection}, {public_collection}")
            
            return client, private_coll, public_coll
        
        except Exception as e:
            if attempt < max_retries - 1:
                logging.warning(f"MongoDB connection attempt {attempt + 1} failed: {e}. Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
            else:
                logging.error(f"Failed to connect to MongoDB after {max_retries} attempts: {e}")
                return None, None, None
    
    return None, None, None

def main(log_file):
    """Main execution for IP extraction and MongoDB storage."""
    try:
        # Configure logging
        logging.basicConfig(
            level=logging.INFO, 
            format='%(asctime)s - %(levelname)s: %(message)s'
        )
        
        # MongoDB connection URI from environment variable or default
        mongodb_uri = os.getenv('MONGODB_URI', 'mongodb://mongodb:27017/')
        database_name = os.getenv('DATABASE_NAME', 'ip_extraction')
        
        # Connect to MongoDB
        client, private_coll, public_coll = connect_to_mongodb(
            mongodb_uri, 
            database=database_name
        )
        
        if not client:
            logging.error("MongoDB connection failed. Exiting.")
            return
        
        # Extract IPs from log file
        private_ips, public_ips = IPExtractor.extract_ips_from_file(log_file)
        
        current_time = time.time()
        
        # Use bulk operations with upsert to store only unique values
        # This preserves all previous entries and only adds new unique IPs
        if private_ips:
            bulk_operations_private = []
            for ip in private_ips:
                bulk_operations_private.append(
                    UpdateOne(
                        {'ip': ip},
                        {
                            '$set': {'ip': ip, 'last_seen': current_time},
                            '$setOnInsert': {'first_seen': current_time}
                        },
                        upsert=True
                    )
                )
            
            if bulk_operations_private:
                result_private = private_coll.bulk_write(bulk_operations_private, ordered=False)
                logging.info(f"Processed {len(private_ips)} private IPs - "
                           f"Inserted: {result_private.upserted_count}, "
                           f"Updated: {result_private.modified_count}")
        
        if public_ips:
            bulk_operations_public = []
            for ip in public_ips:
                bulk_operations_public.append(
                    UpdateOne(
                        {'ip': ip},
                        {
                            '$set': {'ip': ip, 'last_seen': current_time},
                            '$setOnInsert': {'first_seen': current_time}
                        },
                        upsert=True
                    )
                )
            
            if bulk_operations_public:
                result_public = public_coll.bulk_write(bulk_operations_public, ordered=False)
                logging.info(f"Processed {len(public_ips)} public IPs - "
                           f"Inserted: {result_public.upserted_count}, "
                           f"Updated: {result_public.modified_count}")
        
        # Display results
        print(f"Private IPs: {len(private_ips)}")
        print(f"Public IPs: {len(public_ips)}")
        
        # Display MongoDB collection counts
        private_count = private_coll.count_documents({})
        public_count = public_coll.count_documents({})
        print(f"MongoDB - Total Private IPs stored: {private_count}")
        print(f"MongoDB - Total Public IPs stored: {public_count}")

        
        # Close MongoDB connection
        client.close()
    
    except Exception as e:
        logging.error(f"Execution error: {e}")

if __name__ == "__main__":
    while(True):
        log_file = 'data/access.log'
        print("Calling Main Function")
        main(log_file=log_file)
        print("Sleeping for 10 seconds")
        time.sleep(10)