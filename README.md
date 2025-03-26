# HydroPulse

HydroPulse is a Windows-based application designed to read sensor or signal data from a COM port via the Modbus protocol and dynamically plot the readings on a graph. It is ideal for test bench environments where multiple sensor readings—such as pressure, flow, and RPM—need to be monitored in real time.

## Overview

HydroPulse communicates with Modbus devices to retrieve sensor data and plots the information using a dynamic 5-minute rolling window. The application simplifies sensor configuration by allowing users to rename channels, set calibration multipliers, define scale values, and apply offsets. This flexibility ensures accurate data visualization and analysis, even when sensors require adjustments due to manufacturing variances or installation quirks.

## Features

- **Auto Detection of COM Port:** Automatically detects available COM ports to ease device connectivity.
- **Customizable Sensor Configuration:**  
  - Rename sensor channels for clarity.  
  - Configure calibration values (e.g., `1.1` for a +10% adjustment).  
  - Set scale values based on the sensor’s full-scale range (e.g., `600 bar` for a pressure sensor).  
  - Apply offsets to correct sensor readings.
- **Selective Channel Reading:** Choose specific channels from a multi-channel Modbus device to plot, without reading unnecessary data.
- **Dynamic Graph Plotting:** Displays sensor data in a rolling 5-minute window, with a cursor that shows exact sensor values upon hovering.
- **Data Saving:**  
  - **Current Window Data:** Saves an Excel file containing data from the current 5-minute window in the `logs` folder.  
  - **Full Session Data:** Saves another Excel file that stores the entire dataset from start until stop in the `logs/full_data` folder.
- **User-Friendly Interface:** Designed for ease-of-use with intuitive dialogs for configuration and operation.

## Installation

### Precompiled EXE
- Download the latest release from the [HydroPulse Releases](https://github.com/Tech-Rx/HydroPulse/releases) page.
- Run the provided EXE file on your Windows machine.

## Usage

#### 1. Connect Your Modbus Device
Plug your Modbus-enabled sensor device into the COM port.

#### 2. Launch the Application
Open the EXE file (or run the Python script if using the source).

#### 3. Select COM Port & Baud Rate
Choose the correct COM port and set the appropriate baud rate in the application.

#### 4. Configure Sensors
Open the sensor configuration dialog to:
- Rename sensor channels.
- Set calibration values, scale values, and offsets as needed.

#### 5. Start Plotting
Click the **Start** button to begin reading sensor data and dynamically plotting it on the graph.

#### 6. Data Saving
When you press **Stop** or close the app:
- **Current 5-Minute Window Data:** An Excel file is saved in the `logs` folder containing data from the current window.
- **Full Session Data:** Another Excel file is saved in the `logs/full_data` folder containing the entire dataset from start until stop.

## Example Use Case

HydroPulse is currently being used on a test bench that monitors:
- **2 Pressure Sensors**
- **1 Flow Sensor**
- **1 RPM Sensor**

These sensors are connected to a Modbus device, and the software continuously graphs their readings during hydraulic tests (e.g., when testing a pump).

## Roadmap

- **Modular Codebase:** Refactor the current code to be more modular and maintainable.
- **Expanded Communication Options:** Implement support for serial communication in addition to Modbus, allowing the reading of data from both protocols.
- **Enhanced UI:** Further improve the user interface to be even more user-friendly and feature-rich.

## Contributing

Contributions are welcome! Whether you’re looking to streamline the code, add new features, or improve documentation, feel free to open an issue or submit a pull request. This project started as a personal project to help a family member, so every bit of support is greatly appreciated.

## Contact and Support

For questions, suggestions, or to report issues, please open an issue on the GitHub repository or contact the project maintainers directly.
