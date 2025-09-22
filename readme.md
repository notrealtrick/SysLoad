# SysLoad - Dynamic System Resource Balancer

A Python script designed to dynamically maintain a target system-wide CPU and RAM utilization. This tool is ideal for creating a stable baseline load in various environments, especially on cloud platforms with burstable performance or "always-free" tiers where consistent usage is desired.

## 📊 Overview

The `SysLoad.py` script continuously monitors the system's overall CPU and memory usage. Every 15 seconds, it intelligently adjusts its own resource consumption to guide the total system load towards a predefined target (e.g., 81% CPU and 81% RAM).

Instead of applying a static, unintelligent load, this agent acts as a balancer. If another process starts consuming resources, the agent reduces its own footprint to maintain the target. Conversely, if the system becomes idle, the agent increases its load.

## ✨ Key Features

-   **Self-Regulating:** Automatically adjusts its workload every 15 seconds.
-   **Dynamic CPU Control:** Spawns a worker process for each CPU core and dynamically adjusts their work/sleep ratio to meet the target utilization.
-   **Dynamic RAM Control:** Allocates or deallocates memory on the fly to match the target system-wide RAM usage.
-   **Multi-Core Aware:** Utilizes all available CPU cores for an even and effective load distribution.
-   **Configurable Targets:** Easily set your desired CPU and RAM percentage targets at the top of the script.
-   **Robust:** Designed to run as a persistent background service using `systemd`.

## 🚀 Use Cases

This tool is particularly useful for:

1.  **Cloud Free Tiers (e.g., Oracle Cloud):** Some "always-free" cloud instances may be reclaimed if they appear idle. This script can ensure the instance shows consistent activity.
2.  **Performance Testing:** Create a stable and predictable baseline load on a server to test how a new application performs under sustained resource pressure.
3.  **Monitoring & Alerting Setup:** Test your monitoring dashboards (like Grafana, Prometheus, Datadog) and alerting rules by creating a controlled, high-utilization scenario.
4.  **Autoscaling Demonstrations:** Simulate high-load conditions in a Kubernetes or cloud environment to test and demonstrate autoscaling policies.

## ⚙️ How It Works

The script operates on a simple yet effective control loop logic:

1.  **Monitor:** Every 15 seconds, it uses the `psutil` library to get the current system-wide CPU and RAM usage percentages.
2.  **Calculate Error:** It calculates the difference (the "error") between the current usage and the target usage (e.g., `Target: 81% - Current: 75% = Error: 6%`).
3.  **Adjust CPU:**
    -   Based on the CPU error, it calculates a new work/sleep ratio for its worker processes.
    -   This new ratio is communicated to all worker processes through a shared memory value (`multiprocessing.Value`), ensuring they all adjust their workload in the next cycle.
4.  **Adjust RAM:**
    -   Based on the RAM error, it calculates how many megabytes of memory it needs to allocate or release.
    -   It then resizes a large `bytearray` object in its memory to increase or decrease its RAM footprint, pushing the total system memory usage closer to the target.

## 📋 Prerequisites

-   Linux OS (tested on Ubuntu 22.04)
-   Python 3.6+
-   `pip` for Python 3

## 🛠️ Installation & Setup

1.  **Clone the repository:**
    ```bash
    git clone [https://github.com/notrealtrick/SysLoad.git](https://github.com/notrealtrick/SysLoad.git)
    cd SysLoad
    ```
    *(Note: Ensure the Python script inside the repository is named `SysLoad.py`)*

2.  **Install the required Python library:**
    ```bash
    pip3 install psutil
    ```

## 🚀 Usage (as a `systemd` service)

Running the script as a `systemd` service is the recommended way to ensure it runs persistently in the background and starts automatically on boot.

1.  **The script `SysLoad.py` should now be in your current directory (`/home/your_user/SysLoad`).**

2.  **Create a `systemd` service file:**
    ```bash
    sudo nano /etc/systemd/system/SysLoad.service
    ```

3.  **Paste the following configuration into the file.**
    **Important:** Replace `your_user` with your actual username (e.g., `ubuntu`, `oracle`).

    ```ini
    [Unit]
    Description=SysLoad Dynamic Resource Balancer
    After=network.target

    [Service]
    # Replace 'your_user' with your actual username
    User=your_user
    Group=your_user

    # Set the working directory to where you cloned the repo
    WorkingDirectory=/home/your_user/SysLoad/
    ExecStart=/usr/bin/python3 /home/your_user/SysLoad/SysLoad.py

    # Set a lower priority to not interfere with critical system processes
    Nice=15

    # Automatically restart the service if it fails
    Restart=on-failure
    RestartSec=5s

    [Install]
    WantedBy=multi-user.target
    ```

4.  **Enable and Start the Service:**
    ```bash
    # Reload systemd to recognize the new service
    sudo systemctl daemon-reload

    # Enable the service to start on boot
    sudo systemctl enable SysLoad.service

    # Start the service immediately
    sudo systemctl start SysLoad.service
    ```

5.  **Check the status and logs:**
    ```bash
    # Check if the service is active and running
    sudo systemctl status SysLoad.service

    # View the live output of the script
    sudo journalctl -u SysLoad.service -f
    ```

## 🔧 Configuration

You can easily configure the resource targets by editing the constants at the top of the `SysLoad.py` file:

```python
# --- Settings ---
TARGET_CPU_PERCENT = 81.0
TARGET_RAM_PERCENT = 81.0
ADJUSTMENT_INTERVAL_SECONDS = 15
```

-   `TARGET_CPU_PERCENT`: The target system-wide CPU utilization percentage.
-   `TARGET_RAM_PERCENT`: The target system-wide RAM utilization percentage.
-   `ADJUSTMENT_INTERVAL_SECONDS`: How often (in seconds) the agent checks and adjusts the load.

After modifying these values, restart the service to apply the changes:
```bash
sudo systemctl restart SysLoad.service
```