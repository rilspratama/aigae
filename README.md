# Aigaea Multi-Proxy Pinger

Multi-threaded network pinger for Aigaea using multiple proxies. This tool allows you to run concurrent ping requests through different proxies using HTTP, SOCKS4, or SOCKS5 protocols.

Link register : [Here](https://app.aigaea.net/register?ref=gaBv4hsbaxZuD1)

## Features

- 🚀 Multi-threading support - each proxy runs in its own thread
- 🔄 Support for multiple proxy protocols (HTTP, SOCKS4, SOCKS5)
- 📝 Easy proxy management through text file
- 🔑 Support for authenticated and non-authenticated proxies
- 📊 Detailed logging system
- ⏰ Dynamic sleep intervals based on server response
- 🛡️ Robust error handling and retry mechanism

## Prerequisites

- Python 3.7 or higher
- pip (Python package installer)

## Installation

1. Clone this repository or download the source code

```bash
git clone https://github.com/rilspratama/aigae
cd aigae
```

2. Install the required packages

```bash
pip install -r requirements.txt
```

## Configuration

1. Create a `.env` file in the project root directory with your credentials:

```env
TOKEN=your_token_here
UID=your_uid_here
```

2. Create a `proxy.txt` file with your proxies. Each proxy should be on a new line.

## How to get Token & UID

1. Open devtoosl -> Console

2. Copy UID To .env

3. Execute this command to getting token copy into .env
```shell
localStorage.getItem("gaea_token")
```
![Devtools img](img/devtools.png)


## Proxy Format Examples

```text
# With scheme and authentication
http://ip:port@username:password
socks5://ip:port@username:password
socks4://ip:port@username:password

# Without scheme (defaults to http)
ip:port@username:password

# Without authentication
http://ip:port
ip:port

# All formats above are supported for all proxy types (http, socks4, socks5)
```

## Usage

Run the script using Python:

```bash
python main.py
```

The program will:
1. Load your environment variables
2. Read proxies from `proxy.txt`
3. Start a separate thread for each valid proxy
4. Begin sending ping requests through each proxy
5. Log all activities and responses

## Logging

The program logs all activities with timestamps and thread names. Log format:
```
YYYY-MM-DD HH:MM:SS,ms - WorkerName - Message
```

Log levels:
- INFO: Successful pings and general operation info
- ERROR: Failed requests, invalid proxies, and other errors

## Error Handling

The program includes comprehensive error handling:
- Invalid proxy formats are skipped with error messages
- Network errors trigger automatic retries
- Connection timeouts are handled gracefully
- Default 60-second sleep on errors

## Adding/Removing Proxies

To add or remove proxies:
1. Open `proxy.txt`
2. Add new proxies or remove existing ones (one per line)
3. Restart the program to apply changes

## Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| TOKEN | Your Aigaea token | Yes |
| UID | Your Aigaea user ID | Yes |

## Troubleshooting

Common issues and solutions:

1. **Invalid Proxy Format**
   - Check if your proxy string follows one of the supported formats
   - Verify credentials if using authenticated proxies

2. **Connection Errors**
   - Verify proxy is online and accessible
   - Check if proxy supports the specified protocol
   - Verify network connectivity

3. **Authorization Errors**
   - Verify TOKEN and UID in .env file
   - Check if credentials are still valid
