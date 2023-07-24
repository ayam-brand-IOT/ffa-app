import time
import matplotlib.pyplot as plt

# Import the TLB_MODBUS class and instantiate an object
import TLB_MODBUS as net

def apply_force_until_break(initial_tension, tolerance=10):
    force_data = []  # List to store applied forces

    while True:
        tension = net.readWeight()
        force_data.append(tension)

        # if theres more than 2 data points, check if the tension is decreasing
        if len(force_data) > 2 :
        # Check if the tension is close to the initial tension within the given tolerance
            if abs(tension - initial_tension) <= tolerance and force_data[-2] > force_data[-1]:
                break

        # You might want to add some delay between force applications
        time.sleep(0.1)  # Adjust the delay as needed

    return force_data

def main():
    # Instantiate the TLB_MODBUS object with appropriate configurations


    # Get the initial tension
    initial_tension = net.readWeight()
    print(f"Initial tension: {initial_tension}")

    # Apply force until the tension comes back to the initial tension and record the data
    force_data = apply_force_until_break(initial_tension)

    # Analyze the data to find the break point
    break_point = max(force_data)

    # Print and visualize the results (optional)
    print(f"Material broke at {break_point} tension.")
    plt.plot(force_data)
    plt.xlabel("Time")
    plt.ylabel("Tension")
    plt.title("Tension vs. Time")
    plt.show()

if __name__ == "__main__":
    main()