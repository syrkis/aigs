# %% Imports (add as needed) #############################################
import gymnasium as gym  # not jax based
from jax import random, jit, grad
import jax.numpy as jnp
import numpy as np
import jax
from tqdm import tqdm
from collections import deque, namedtuple

# %% Constants ###########################################################
env = gym.make("CartPole-v1", render_mode="human")  #  render_mode="human")
rng = random.PRNGKey(0)
entry = namedtuple("Memory", ["obs", "action", "reward", "next_obs", "done"])
memory = deque(maxlen=1000)  # <- replay buffer
# define more as needed
state_size = env.observation_space.shape[0] # 4    
print("state_space:", state_size)
action_size= env.action_space.n # 2
print("action_space:", action_size)

learning_rate = 0.001 # how fast the model learns
gamma = 0.99 # discount factor
batch_size = 32 # how many samples to use for training
epsilon = 1.0 # initial exploration rate
epsilon_decay = 0.995 # how much to decay the exploration rate  
epsilon_min = 0.1 # minimum exploration rate
update_target_every = 5 # how often to update the target network   

# %% Init params for NN
def init_params(key, input_size, output_size):
    rng, key = random.split(key) # split the key into two keys
    params = {}
    params['w1'] = random.normal(key, (input_size, 32)) * 0.01 # initialize the weights
    params['b1'] = jnp.zeros((32,)) # initialize the biases
    params['w2'] = random.normal(key, (32, 32)) * 0.01 # initialize the weights
    params['b2'] = jnp.zeros((32,)) # initialize the biases
    params['w3'] = random.normal(key, (32, output_size)) * 0.01 # initialize the weights
    params['b3'] = jnp.zeros((output_size,)) # initialize the biases
    return params

# %% Q network
def q_network(params, state):
    x = jax.nn.relu(jnp.dot(state, params['w1']) + params['b1']) # first layer
    x = jax.nn.relu(jnp.dot(x, params['w2']) + params['b2']) # second layer
    return jnp.dot(x, params['w3']) + params['b3'] # output layer

# %% Loss function
def loss_fn(params, target_params, obs, actions, rewards, next_obs, dones):
    q_values = q_network(params, obs) #
    q_values = jnp.take_along_axis(q_values, actions[:, None], axis=1).squeeze() 
    next_q_values = jnp.max(q_network(target_params, next_obs), axis=1)
    target_q_values = rewards + (gamma * next_q_values * (1 - dones))
    return jnp.mean((q_values - target_q_values) ** 2)

# %% Initialize
key = random.PRNGKey(0)
params = init_params(key, state_size, action_size)
target_params = params

# %% Optimizer
@jit
def update(params, grads, lr):
    def update_param(param, grad):
        return param - lr * grad
    # Apply the update function to each parameter and its gradient
    updated_params = jax.tree_map(update_param, params, grads)

    return updated_params

# %% Model ###############################################################
def random_policy_fn(rng, obs): # action (shape: ())
    n = action_size
    return random.randint(rng, (1,), 0, n).item()

# %% Epsilon greedy policy - custom
def epsilon_greedy_policy(params, state, epsilon):
    if np.random.rand() < epsilon:
        return np.random.choice(action_size)
    else:
        q_values = q_network(params, state)
        return jnp.argmax(q_values)


# %% Sample from memory
def sample_memory(memory, batch_size):
    indices = np.random.choice(len(memory), batch_size, replace=False)
    batch = [memory[idx] for idx in indices]
    return map(np.array, zip(*batch))

# %% Training Loop
for episode in range(1000): #how many episodes/times to train
    state, _ = env.reset() #reset the environment
    done = False #done is false
    total_reward = 0 #total reward is 0

    while not done: #while done is not true
        action = epsilon_greedy_policy(params, state, epsilon) #choose an action and policy
        next_state, reward, terminated, truncated, _ = env.step(action) #take the action and get the next state, reward, and done
        done = terminated or truncated #if terminated or truncated, then done is true

        memory.append(entry(state, action, reward, next_state, done))
        state = next_state
        total_reward += reward

        if len(memory) >= batch_size:
            obs, actions, rewards, next_obs, dones = sample_memory(memory, batch_size)
            
            # Compute gradients
            grads = grad(loss_fn)(params, target_params, obs, actions, rewards, next_obs, dones)
            params = update(params, grads, learning_rate)

    if epsilon > epsilon_min:
        epsilon *= epsilon_decay

    if episode % update_target_every == 0:
        target_params = params

    print(f"Episode {episode}, Total Reward: {total_reward}")

env.close()


# %% Environment #########################################################
# obs, info = env.reset() 
# for i in tqdm(range(1000)):

#     rng, key = random.split(rng)
#     action = random_policy_fn(key, obs)

#     next_obs, reward, terminated, truncated, info = env.step(action)
#     memory.append(entry(obs, action, reward, next_obs, terminated | truncated))
#     obs, info = next_obs, info if not (terminated | truncated) else env.reset()

# env.close()
