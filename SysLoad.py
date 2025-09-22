import multiprocessing
import time
import os
import sys

try:
    import psutil
except ImportError:
    print("ERROR: 'psutil' library not found.", file=sys.stderr)
    print("Please install it using 'pip3 install psutil'", file=sys.stderr)
    sys.exit(1)

# --- Settings ---
TARGET_CPU_PERCENT = 81.0
TARGET_RAM_PERCENT = 81.0
ADJUSTMENT_INTERVAL_SECONDS = 15  # Control and adjustment frequency (seconds)

def cpu_worker(shared_cpu_target_ratio):
    """
    A worker process that dynamically adjusts CPU load by reading a shared value.
    shared_cpu_target_ratio: A value between 0.0 and 1.0 (e.g., 0.81)
    """
    while True:
        try:
            # Read the current target from the main process in each loop
            target_ratio = shared_cpu_target_ratio.value
            
            # Work/sleep within a 1-second cycle according to the target ratio
            start_time = time.time()
            while time.time() - start_time < target_ratio:
                pass  # Occupy the CPU
            
            time.sleep(max(0, 1.0 - target_ratio))
        except Exception:
            # Prevent crashing on potential errors
            time.sleep(1)

def resource_manager():
    """
    The main function that periodically checks system resources and manages
    CPU workers and RAM usage to meet the targets.
    """
    print("Dynamic Resource Manager Initialized.")
    print(f"Targets -> CPU: {TARGET_CPU_PERCENT}%, RAM: {TARGET_RAM_PERCENT}%")
    
    # 1. Start CPU Workers
    cpu_count = os.cpu_count()
    # Create a shared memory value for the processes. 'd' -> double (float)
    # The initial value is the target percentage divided by 100.
    shared_cpu_target = multiprocessing.Value('d', TARGET_CPU_PERCENT / 100.0)

    workers = []
    for _ in range(cpu_count):
        worker = multiprocessing.Process(target=cpu_worker, args=(shared_cpu_target,))
        worker.daemon = True
        worker.start()
        workers.append(worker)
    print(f"Started {cpu_count} CPU worker processes.")

    # 2. Start the main RAM and CPU Adjustment Loop
    ram_hog = bytearray(0)  # Start with an empty bytearray
    current_script_ram_mb = 0

    while True:
        try:
            # --- Read System Resources ---
            # interval=1 provides a more accurate reading by measuring over 1 second
            overall_cpu_usage = psutil.cpu_percent(interval=1)
            memory_info = psutil.virtual_memory()
            overall_ram_usage = memory_info.percent
            total_system_ram_mb = memory_info.total / (1024 * 1024)

            # --- CPU Adjustment ---
            cpu_error = TARGET_CPU_PERCENT - overall_cpu_usage
            # A simple proportional controller. The larger the error, the larger the adjustment.
            # A gain factor of 0.5 prevents drastic overshooting.
            adjustment = (cpu_error / 100.0) * 0.5
            
            # Calculate the new target and clamp it within safe limits (0.05 - 1.0)
            new_cpu_target_ratio = shared_cpu_target.value + adjustment
            new_cpu_target_ratio = max(0.05, min(1.0, new_cpu_target_ratio))
            
            # Write the new target to the shared value
            shared_cpu_target.value = new_cpu_target_ratio

            # --- RAM Adjustment ---
            # Calculate how many MB of memory to add or remove
            ram_error_percent = TARGET_RAM_PERCENT - overall_ram_usage
            ram_adjustment_mb = (ram_error_percent / 100.0) * total_system_ram_mb
            
            new_script_ram_mb = current_script_ram_mb + ram_adjustment_mb
            # Check to ensure we don't allocate negative memory
            new_script_ram_mb = max(0, new_script_ram_mb)

            # To prevent flickering, only reallocate if the change is significant (e.g., > 10MB)
            if abs(new_script_ram_mb - current_script_ram_mb) > 10:
                try:
                    print(f"Adjusting RAM: {int(current_script_ram_mb)} MB -> {int(new_script_ram_mb)} MB")
                    ram_hog = bytearray(int(new_script_ram_mb) * 1024 * 1024)
                    current_script_ram_mb = new_script_ram_mb
                except MemoryError:
                    print("Failed to allocate new RAM amount, maintaining current state.")
            
            # --- Print Status Report ---
            print(
                f"Status | Total CPU: {overall_cpu_usage:.1f}% (Target: {TARGET_CPU_PERCENT}%) | "
                f"Total RAM: {overall_ram_usage:.1f}% (Target: {TARGET_RAM_PERCENT}%) | "
                f"Worker Load: {shared_cpu_target.value*100:.1f}%"
            )

            # Sleep for the configured adjustment interval
            # Subtracting 1 second already spent on cpu_percent measurement
            time.sleep(ADJUSTMENT_INTERVAL_SECONDS - 1) 

        except KeyboardInterrupt:
            print("\nShutting down...")
            for worker in workers:
                worker.terminate()
            break
        except Exception as e:
            print(f"An error occurred in the main loop: {e}", file=sys.stderr)
            time.sleep(ADJUSTMENT_INTERVAL_SECONDS)

if __name__ == '__main__':
    resource_manager()