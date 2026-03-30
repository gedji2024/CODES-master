"""Run 200 episodes standalone QTRAN to get robust PDR estimate."""
import sys, os, glob, torch, time
import numpy as np

sys.path.insert(0, 'src')
from controllers.basic_controller import BasicMAC
from components.episode_buffer import EpisodeBatch
from components.transforms import OneHot
from envs import REGISTRY as env_REGISTRY
from types import SimpleNamespace as SN

# Don't seed numpy (let it be random like subprocess would be)
torch.manual_seed(42)

env = env_REGISTRY['gymma'](key='gym_examples:WSNRouting-v0', time_limit=30,
                             pretrained_wrapper=None, seed=42)
info = env.get_env_info()

scheme = {
    'state': {'vshape': info['state_shape']},
    'obs': {'vshape': info['obs_shape'], 'group': 'agents'},
    'actions': {'vshape': (1,), 'group': 'agents', 'dtype': torch.long},
    'avail_actions': {'vshape': (info['n_actions'],), 'group': 'agents', 'dtype': torch.int},
    'reward': {'vshape': (1,)},
    'terminated': {'vshape': (1,), 'dtype': torch.uint8},
}
groups = {'agents': info['n_agents']}
preprocess = {'actions': ('actions_onehot', [OneHot(out_dim=info['n_actions'])])}
mac_scheme = dict(scheme)
mac_scheme['actions_onehot'] = {'vshape': (info['n_actions'],), 'dtype': torch.float32, 'group': 'agents'}

mac_args = SN(n_agents=info['n_agents'], n_actions=info['n_actions'], obs_shape=None,
    hidden_dim=64, use_rnn=True, agent='rnn', obs_last_action=True, obs_agent_id=True,
    agent_output_type='q', action_selector='epsilon_greedy',
    epsilon_start=0.01, epsilon_finish=0.01, epsilon_anneal_time=1,
    evaluation_epsilon=0.01, mask_before_softmax=True, device='cpu')

mac = BasicMAC(mac_scheme, groups, mac_args)
dirs = sorted(glob.glob(os.path.join('results', 'models', 'qtran_seed*')))
steps = [int(n) for n in os.listdir(dirs[-1]) if n.isdigit()]
mac.load_models(os.path.join(dirs[-1], str(max(steps))))
for p in mac.parameters():
    p.requires_grad_(False)
mac.agent.eval()

N = 200
print(f'Running {N} episodes (standalone QTRAN, time_limit=30)...')
t0 = time.perf_counter()
pdrs = []
for ep in range(N):
    env.reset()
    mac.init_hidden(batch_size=1)
    batch = EpisodeBatch(scheme, groups, 1, 31, preprocess=preprocess, device='cpu')
    done = False
    for t in range(30):
        if done:
            break
        batch.update({'state': [env.get_state()], 'avail_actions': [env.get_avail_actions()], 'obs': [env.get_obs()]}, ts=t)
        actions = mac.select_actions(batch, t_ep=t, t_env=t, test_mode=True)
        reward, done, info2 = env.step(actions[0])
        terminated_flag = done and not info2.get('episode_limit', False)
        batch.update({'actions': actions.unsqueeze(-1), 'reward': [(reward,)], 'terminated': [(terminated_flag,)]}, ts=t)
    pdr = env.original_env.__dict__['env'].__dict__['packet_delivery_ratio']
    pdrs.append(pdr)
    if (ep + 1) % 50 == 0:
        print(f'  [{ep+1}/{N}] mean_pdr={np.mean(pdrs)*100:.1f}% elapsed={time.perf_counter()-t0:.0f}s')

print(f'\nFinal: Mean PDR = {np.mean(pdrs)*100:.1f}% +/- {np.std(pdrs)*100:.1f}%')
print(f'>50%: {sum(1 for p in pdrs if p>0.5)}/{N}')
print(f'>20%: {sum(1 for p in pdrs if p>0.2)}/{N}')
print(f'==0:  {sum(1 for p in pdrs if p==0)}/{N}')
