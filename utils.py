import numpy as np
from math import asin, sqrt
from math import floor
from qiskit.circuit import QuantumCircuit, QuantumRegister
from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager
from qiskit_ibm_runtime import QiskitRuntimeService, Session, Sampler, Options
from qiskit_ibm_runtime import SamplerV2 
from qiskit.quantum_info import Statevector
from qiskit.visualization import plot_bloch_multivector
from qiskit_aer import AerSimulator

import matplotlib.pyplot as plt
# %matplotlib inline
# silence warnings
# import warnings
# warnings.filterwarnings('ignore')



######## utility functions ############
#### Utility functions for QBN ######

def prob_to_angle(prob):
    return 2*asin(sqrt(prob))


def bit_str_2_arr(bitstring):
    """
    Converts a bitstring to a NumPy array of integers.

    This function takes a bitstring as input and converts it into a 
    NumPy array where each element represents a bit.

    Args:
        bitstring: The input bitstring.

    Returns:
        A NumPy array of integers representing the bitstring.
    """
    my_state = bitstring[::-1]
    bit_array = np.zeros(len(my_state))
    for i in range(len(my_state)):
        if int(my_state[i]) == 0:
            pass
        else:
            bit_array[i] = int(my_state[i])
    return bit_array



def custom_mcry(circuit,angle,control_qubits,target,control_state):# Multi-coltrolled Ry gate #
    """
    Applies a multi-controlled Ry gate to a quantum circuit.

    This function constructs a multi-controlled Ry gate based 
    on the provided parameters and appends it to the given circuit.

    Args:
        circuit: The QuantumCircuit to add the gate to.
        angle: The rotation angle for the Ry gate.
        control_qubits: A list of control qubits for the gate.
        target: The target qubit for the Ry gate.
        control_state: A string representing the desired control state (e.g., '011').

    Returns:
        The modified QuantumCircuit with the added multi-controlled Ry gate.
    """
    Id = []
    for i in range(len(control_state)):
        c = control_state[i]
        if c == '0':
            Id.append(control_qubits[i])			
        else:
            pass
    if len(Id) == 0:
        pass
    else:
        circuit.x(Id)
    circuit.mcry(angle,control_qubits,target)
    if len(Id) == 0:
        pass
    else:
        circuit.x(Id)
    return circuit


def feature_map(x,method = 'default'):
    """
    Applies a specified transformation to the input value.

    This function maps an input value `x` to a new value `theta` based on the chosen method.

    Args:
        x: The input value to be transformed.
        method: The transformation method to apply. Can be one of 
        'on_axis', 'shifted', or 'default' (default).

    Returns:
        The transformed value, theta.
    """
    if method == 'on_axis':
        if x > np.pi/2:
            theta = np.pi 
        elif x <= np.pi/2:
            theta = 0    
        else:
            theta = x
    elif method == 'shifted':
        if x < np.pi/2:
            theta = (np.pi/4)-(x/4)
        elif x > np.pi/2:
            theta = (3*np.pi/4)+(x/4)
        else:
            theta = x
    elif method == 'default':
        theta = x
    return theta


def encode_data(data_row,show_bloch_sphere=False): # Encoding angle data to quantum circuit Ry gates
    """
    Encodes classical data into a quantum circuit with Ry gates.

    This function takes a row of classical data and encodes each element as the rotation angle of an Ry gate in a quantum circuit.

    Args:
        data_row: A NumPy array representing a row of classical data.
        show_bloch_sphere (bool, optional): Whether to visualize the encoded state on the Bloch sphere (default: False).

    Returns:
        A QuantumCircuit object containing the encoded data
    """
    quantum_data = QuantumCircuit(data_row.shape[0],)
    for j in range(len(data_row)):
        quantum_data.ry(data_row[j],j)

    if show_bloch_sphere == True:
        plt.figure()
        plot_bloch_multivector(Statevector(quantum_data))
        plt.show()
    else:
        pass

    return quantum_data


def my_trade(state,price,prev_log):
    """
    Executes a trading strategy based on state changes.

    This function determines a trading action (buy, sell, or hold) based on the current state and previous trade log. 
    It updates the trade log with relevant information including position, cash, and portfolio value.

    Args:
        state: The current state of the system.
        price: The current price of the asset.
        prev_log: A dictionary containing previous trade information, including:
            - state: Previous state.
            - position: Previous position.
            - cash: Previous cash balance.
            - buy_price: Previous buy price.
            - sell_price: Previous sell price.
            - last purchase price: Price of the last purchase.
            - portfolio value: Previous portfolio value.

    Returns:
        A dictionary containing the updated trade log information, including:
            - state: Current state.
            - signal: Trading signal (1: buy, -1: sell, 0: hold).
            - position: Current position.
            - cash: Current cash balance.
            - buy_price: Updated buy price (if applicable).
            - sell_price: Updated sell price (if applicable).
            - last purchase price: Updated last purchase price (if applicable).
            - portfolio value: Current portfolio value
    """
# sample log = {'state':np.nan,'buy_price':np.nan,
#               'sell_price':np.nan,'signal':0,
#               'position':0,'portfolio value':0, 
#               'cash':initial_cash,'last purchase price': np.nan}

    prev_state = prev_log['state']
    trade_log = {'state':state,}

    if state > prev_state: 
        # print("Prev {}, current {} ---> BUY!".format(prev_state,state))
        trade_log['signal'] = +1

        if prev_log['cash'] > 0:
            trade_log['position'] = prev_log['cash']/price
            trade_log['cash'] = 0
            trade_log['buy_price'] = price
            trade_log['sell_price'] = np.nan
            trade_log['last purchase price'] = trade_log['buy_price']
        else:
            trade_log['position'] = prev_log['position']
            trade_log['cash'] = prev_log['cash']
            trade_log['buy_price'] = np.nan
            trade_log['sell_price'] = np.nan
            trade_log['last purchase price'] = 0

    elif state < prev_state: 
        # print("Prev {}, current {} ---> SELL!".format(prev_state,state))
        trade_log['signal'] = -1
        if prev_log['position'] > 0 and price > prev_log['last purchase price']: # include buy price and if purchase price < current price
            trade_log['cash'] = prev_log['position']*price
            trade_log['position'] = 0
            trade_log['buy_price'] = np.nan
            trade_log['sell_price'] = price
            trade_log['last purchase price'] = 0
        else:
            trade_log['position'] = prev_log['position']
            trade_log['cash'] = prev_log['cash']
            trade_log['buy_price'] = np.nan
            trade_log['sell_price'] = np.nan
            trade_log['last purchase price'] = prev_log['last purchase price']
    else:
        # print("Prev {}, current {} ---> HOLD!".format(prev_state,state))
        trade_log['signal'] = 0
        trade_log['buy_price'] = np.nan
        trade_log['sell_price'] = np.nan
        trade_log['position'] = prev_log['position']
        trade_log['cash'] = prev_log['cash']
        trade_log['last purchase price'] = prev_log['last purchase price']

    # print(">>-----",prev_log)
    # print("----->>",trade_log)
    trade_log['portfolio value'] = trade_log['cash'] + (trade_log['position']*price)
    return trade_log


def quantum_compute(service,circuit,backend,sampler,
                    optimization=0,
                    num_shots=1000,seed=None):
    """
    Executes a quantum circuit on a backend and retrieves the most likely state.

    This function takes a quantum circuit, backend, sampler type (`v1` or `v2`), and other optional
    parameters and executes the circuit to determine the most likely state based on the sampled probability
    distribution.

    Args:
        service: A Quantum Experience service object (specific to a quantum computing library).
        circuit: The QuantumCircuit object to be executed.
        backend: The backend on which to run the circuit (e.g., simulator or real hardware).
        sampler: The type of sampler to use ('v1' or 'v2').
        optimization (int, optional): Optimization level for circuit transpilation (default: 0).
        num_shots (int, optional): Number of shots (executions) to run the circuit (default: 1000).
        seed (int, optional): Seed for the simulator (default: None).

    Returns:
        A tuple containing:
            * prob_dist: A dictionary representing the probability distribution of the measurement outcomes.
            * state: The most likely state based on the probability distribution.

    Raises:
        ValueError: If an unsupported sampler type is provided
    """
    pm = generate_preset_pass_manager(backend=backend, optimization_level=optimization)
    isa_circuit = pm.run(circuit)    
    prob_dist = None
    print("\n\n\nCircuit pre-transpilation depth is:",circuit.depth())
    print("Circuit post-transpilation depth is:",isa_circuit.depth())

    if sampler == 'v1':
        with Session(service, backend=backend) as session:
            sampler = Sampler(session=session)
            # sampler.options.simulator.seed_simulator = seed

            job = sampler.run(circuit,shots=num_shots)
            result = job.result()
            pub_result = result.quasi_dists[0]
            prob_dist = pub_result.binary_probabilities()
            print("The output probability distribution:",prob_dist)

    elif sampler == 'v2':
        sampler = SamplerV2(mode=backend)
        if backend == AerSimulator():
            sampler.options.simulator.seed_simulator = seed
        else:
            pass
        
        job = sampler.run([isa_circuit],shots=num_shots)
        result = job.result()
        pub_result = result[0]
        counts = eval('pub_result.data.'+isa_circuit.cregs[0].name +'.get_counts()')
        prob_dist = {key:counts[key]/num_shots for key in counts}
        print("The output probability distribution:",prob_dist)

    else:
        raise ValueError("Unsupported sampler type: {}".format(sampler))
    state = int(max(zip(prob_dist.values(), prob_dist.keys()))[1])
    return prob_dist, state
