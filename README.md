## IMPORTANT NOTE
This repository is intended for my personal notes and portfolio purposes on LinkedIn. I do not expect any contributions from others. Thank you for understanding!

# POC IG.com Trading Robot API

This repository contains a Proof of Concept (POC) for a trading robot designed for the IG.com trading platform. The trading robot automates trading strategies and interacts with the IG API to execute trades based on predefined rules.

## Features

- **Automated Trading**: Executes trades automatically based on predefined strategies.
- **IG API Integration**: Interacts with the IG trading platform using their API.
- **Strategy Customization**: Allows users to define and customize their trading strategies.
- **Real-time Data**: Fetches real-time market data to make informed trading decisions.
- **Logging and Monitoring**: Logs trading activities and monitors performance.

## Getting Started

### Prerequisites

- Python 3.x
- IG API credentials

### Installation

1. Clone the repository:
    ```bash
    git clone https://github.com/ariogunawan/POC-IGcom-Trading-Robot-API.git
    cd POC-IGcom-Trading-Robot-API
    ```

2. Install the required packages:
    ```bash
    pip install -r requirements.txt
    ```

### Configuration

1. Set up your IG API credentials:
    - Create a `.env` file in the root directory.
    - Add your IG API credentials to the `.env` file:
        ```
        IG_API_KEY=your_api_key
        IG_ACCOUNT_ID=your_account_id
        ```

### Usage

1. Run the trading robot:
    ```bash
    python main.py
    ```

2. The trading robot will:
    - Fetch real-time market data from IG.
    - Execute trades based on the predefined strategies.
    - Log all trading activities and monitor performance.

## Project Structure

- `ig_main.py`: The main script to run the trading robot.
- `ig_api.py`: Contains functions to interact with the IG API.
- `requirements.txt`: List of required Python packages.
- `.env.example`: Example environment file for IG API credentials.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

## Acknowledgements

- [IG API](https://labs.ig.com/)
- [Python](https://www.python.org/)

## IMPORTANT NOTE
This repository is intended for my personal notes and portfolio purposes on LinkedIn. I do not expect any contributions from others. Thank you for understanding!
