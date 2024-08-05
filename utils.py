import numpy as np
from math import asin, sqrt
from math import floor
from qiskit.circuit import QuantumCircuit
from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager
from qiskit_ibm_runtime import QiskitRuntimeService, Session, Sampler, Options
from qiskit_ibm_runtime import SamplerV2 

# silence warnings
# import warnings
# warnings.filterwarnings('ignore')



######## utility functions ############
#### Utility functions for QBN ######

def prob_to_angle(prob):
    return 2*asin(sqrt(prob))


def bit_str_2_arr(bitstring):
	my_state = bitstring[::-1]
	bit_array = np.zeros(len(my_state))
	for i in range(len(my_state)):
		if int(my_state[i]) == 0:
			pass
		else:
			bit_array[i] = int(my_state[i])
	return bit_array



def custom_mcry(circuit,angle,control_qubits,target,control_state):
	# Multi-coltrolled Ry gate #
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
    if method == 'on_axis':
        if x > np.pi/2:
            theta = np.pi 
        elif x <= np.pi/2:
            theta = 0    
        else:
            theta = x
    elif method == 'shift':
        if x > np.pi/2:
            theta = x + np.pi/4 + (x - np.pi/2)
        elif x < np.pi/2:
            theta = x - np.pi/4 - (np.pi/2 - x)
        else:
            theta = x
    elif method == 'default':
        theta = x
    return theta


def encode_data(data_row,method='default'): # Encoding angle data to quantum circuit Ry gates
    qc= QuantumCircuit([]) #,cr)

    quantum_data = QuantumCircuit(data_row.shape[0],)
    for j in range(len(data_row)):
        quantum_data.ry(feature_map(data_row[j],method=method),j)

    quantum_data.barrier()
    return quantum_data


def my_trade(state,price,prev_log):

# log = {'state':np.nan,'buy_price':np.nan,'sell_price':np.nan,'signal':0,
#       'position':0,'portfolio value':0, 'cash':initial_cash,'last purchase price': np.nan}

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
        sampler.options.simulator.seed_simulator = seed
        
        job = sampler.run([isa_circuit],shots=num_shots)
        result = job.result()
        pub_result = result[0]
        counts = eval('pub_result.data.'+isa_circuit.cregs[0].name +'.get_counts()')
        prob_dist = {key:counts[key]/num_shots for key in counts}
        print("The output probability distribution:",prob_dist)

    else:
        pass 
    state = int(max(zip(prob_dist.values(), prob_dist.keys()))[1])
    return prob_dist, state
