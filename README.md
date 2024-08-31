# PyInterface

**PyInterface** is a Python-based application designed to facilitate socket and serial communication between different applications in a controlled and efficient manner. It also provides the capability to log data to an InfluxDB database for real-time monitoring and analysis.

## Features

- **Socket and Serial Communication**: Enables seamless communication between applications using socket and serial protocols.
- **Data Logging**: Logs data to an InfluxDB database, allowing for real-time data visualization and analysis.
- **Configuration Files**: Customizable communication and database settings through YAML configuration files.

## Files

### `main.py`
The main entry point of the application. It initializes and manages the communication interface, handling both socket and serial communications as specified in the configuration files. It also integrates the logging functionality to InfluxDB.

### `writer.py`
Handles the writing of data to the InfluxDB database. This module is responsible for formatting the data correctly and ensuring that it is stored efficiently and accurately.

### `Communication.yaml`
A YAML configuration file that contains the settings for the socket and serial communication protocols. This file allows you to customize the communication parameters such as port numbers, baud rates, and IP addresses.

### `Database.yaml`
A YAML configuration file that holds the configuration settings for connecting to the InfluxDB database. This includes details such as the database name, server URL, and authentication credentials.

## Installation
    
1. Clone the repository:

    ```bash
    git clone https://github.com/MrPubs/PyInterface.git
    cd PyInterface
    ```
2. Preperation:

    Make Sure the following:
    * the Communication.yaml file is properly configured with your communicators
    * if intending on using an InfluxDB database, Make sure to properly configure the Database.yaml for Database connection, and that the Database is up.
    * Make sure to properly define the Brain_IO Pipelines(foo & bar), and linking them using the _link Decorator to Properly Link the right Index Communicators & DBLink Settings.

3. Create a Virtual Environment:

    **Note**: This project uses Python 3.11.9.

    ```bash
    python.exe -m venv venv
    venv\Scripts\activate
    ```

4. Install the required Python packages:

    ```bash
    pip install -r requirements.txt
    ```

5. Set up your `Communication.yaml` and `Database.yaml` files with the appropriate settings.

## Usage

To run the application, simply execute the `main.py` file:

```bash
venv\Scripts\python.exe main.py
```
