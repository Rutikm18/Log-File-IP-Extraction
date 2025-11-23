# IP Extractor: Dynamic Log File IP Processing

## Overview

The **IP Extractor** is a sophisticated Python application designed to dynamically extract and classify IP addresses from log files. The tool provides real-time IP address identification, classification, and MongoDB storage with continuous monitoring and processing capabilities.

## Key Features

- 🔍 Dynamic log file processing
- 🌐 Automatic IP address extraction
- 🏗️ IP classification (private vs. public)
- 📦 MongoDB storage integration
- 🚀 Concurrent processing for efficiency
- ♻️ Continuous monitoring and extraction

## How It Works

The application continuously monitors a specified log file and performs the following tasks:

1. **Dynamic File Scanning**: 
   - Automatically processes the designated log file
   - Supports real-time updates and file changes
   - Configurable scanning interval (default: 10 seconds)

2. **IP Address Extraction**:
   - Uses advanced regex for comprehensive IP detection
   - Supports IPv4 address extraction
   - Filters out unspecified, reserved, and multicast addresses

3. **IP Classification**:
   - Categorizes IPs into private and public networks
   - Identifies IPs within standard private network ranges:
     - 10.0.0.0/8
     - 172.16.0.0/12
     - 192.168.0.0/16

4. **MongoDB Integration**:
   - Stores extracted IPs in separate collections
   - Supports easy configuration of MongoDB connection
   - Provides clear logging of extraction process

## Project Structure

```
-Log-File-IP-Extraction/
│
├── src/
│   └── main.py             # Core extraction logic
├── data/
│   └── access.log          # Log file to be processed
├── docker/
│   └── Dockerfile          # Docker containerization
├── docker-compose.yml      # Docker composition
├── requirements.txt        # Python dependencies
└── README.md              # Project documentation
```

## Requirements

### Prerequisites

- **Python**: 3.9 or higher (uses built-in `ipaddress` module)
- **MongoDB**: 4.0 or higher (can be run via Docker)
- **Docker & Docker Compose**: For containerized deployment (optional)

### Python Dependencies

Install required Python packages:

```bash
pip install -r requirements.txt
```

**Dependencies:**
- `pymongo==4.6.1` - MongoDB driver for Python

**Note**: The `ipaddress` module is part of Python's standard library (Python 3.3+), so no additional package is needed.

## Installation

### Local Development

1. Clone the repository:
   ```bash
   git clone https://github.com/Rutikm18/Log-File-IP-Extraction.git
   cd -Log-File-IP-Extraction
   ```

2. Install Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Ensure MongoDB is running locally or update the connection URI in the code.

4. Place your log file in the `data/` directory as `access.log`.

5. Run the application:
   ```bash
   python src/main.py
   ```

## Configuration

### Log File Configuration

- **Default Location**: `data/access.log`
- **Customization**: Easily change log file path in `main.py`
- **Supports**: Any text-based log file with IPv4 addresses

### MongoDB Configuration

The application uses environment variables for MongoDB configuration:

- **MONGODB_URI**: MongoDB connection string (default: `mongodb://mongodb:27017/`)
- **DATABASE_NAME**: Database name (default: `ip_extraction`)

**Collections:**
- `private_ips`: Stores private IP addresses with `first_seen` and `last_seen` timestamps
- `public_ips`: Stores public IP addresses with `first_seen` and `last_seen` timestamps

**Note**: Both collections have unique indexes on the `ip` field to prevent duplicates.

## Docker Deployment

### Prerequisites
- Docker
- Docker Compose

### Deployment Steps

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd -Log-File-IP-Extraction
   ```

2. Add your log file under `data/` directory with name `access.log`

3. Run deployment:
   ```bash
   docker-compose up --build
   ```

The Docker setup includes:
- **ip-extractor service**: Runs the Python application
- **mongodb service**: MongoDB database instance
- **Volume mounting**: Log file is mounted from host to container
- **Automatic retry**: Application retries MongoDB connection if database isn't ready

### Environment Variables (Docker)

You can customize the following environment variables in `docker-compose.yml`:
- `MONGODB_URI`: MongoDB connection string
- `DATABASE_NAME`: Database name


## Performance Considerations

- Uses `ProcessPoolExecutor` for concurrent processing
- Chunk-based file reading for memory efficiency
- Minimal resource consumption

## Logging

Comprehensive logging provides insights into:
- MongoDB connection status
- IP extraction details
- Bulk operation results (inserted/updated counts)
- Error tracking and retry attempts

**Log Format**: 
```
2024-03-28 10:15:00 - INFO: Successfully connected to MongoDB! (URI: mongodb://mongodb:27017/)
2024-03-28 10:15:00 - INFO: Created unique indexes on IP fields
2024-03-28 10:15:05 - INFO: Processed 10 private IPs - Inserted: 8, Updated: 2
2024-03-28 10:15:05 - INFO: Processed 5 public IPs - Inserted: 5, Updated: 0
```

## Features

- **Continuous Monitoring**: The application runs in a loop, processing the log file every 10 seconds
- **Duplicate Prevention**: Uses MongoDB unique indexes to prevent storing duplicate IPs
- **Timestamp Tracking**: Tracks `first_seen` and `last_seen` timestamps for each IP
- **Bulk Operations**: Efficiently processes IPs using MongoDB bulk write operations
- **Connection Resilience**: Automatic retry logic for MongoDB connections with configurable retry attempts

## Extensibility

Future enhancements can include:
- Advanced IP reputation checking
- Support for IPv6
- Enhanced error handling
- More granular IP classification
