import torch
import torch.nn as nn
from torch.distributions import Categorical

class ActorCritic(nn.Module):
    def __init__(self, state_dim, action_dim):
        super(ActorCritic, self).__init__()
        
        # Camada compartilhada para extração de features
        self.base = nn.Sequential(
            nn.Linear(state_dim, 128),
            nn.ReLU(),
            nn.Linear(128, 128),
            nn.ReLU()
        )
        
        # Cabeça do Ator (Gera probabilidades das ações)
        self.actor = nn.Sequential(
            nn.Linear(128, action_dim),
            nn.Softmax(dim=-1)
        )
        
        # Cabeça do Crítico (Gera o valor estimado do estado)
        self.critic = nn.Sequential(
            nn.Linear(128, 1)
        )
        
    def forward(self):
        raise NotImplementedError("Utilize act() ou evaluate()")
        
    def act(self, state):
        """Usado durante a coleta de dados (interação com o ambiente)."""
        features = self.base(state)
        action_probs = self.actor(features)
        dist = Categorical(action_probs)
        action = dist.sample()
        action_logprob = dist.log_prob(action)
        state_val = self.critic(features)
        
        return action.detach(), action_logprob.detach(), state_val.detach(), action_probs.detach()
        
    def evaluate(self, state, action):
        """Usado durante a atualização (treinamento) da rede."""
        features = self.base(state)
        action_probs = self.actor(features)
        dist = Categorical(action_probs)
        
        action_logprobs = dist.log_prob(action)
        dist_entropy = dist.entropy()
        state_values = self.critic(features)
        
        return action_logprobs, state_values, dist_entropy
