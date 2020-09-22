"""
"""
__all__ = [
    "Optimizer",
    "SGD",
    "Adam",
    "AdamW"
]

import math

import torch
from torch.optim.optimizer import Optimizer as TorchOptimizer


class Optimizer(object):
    """
    Optimizer
    """
    
    def __init__(self, model_params, **kwargs):
        """
        
        :param model_params: a generator. E.g. ``model.parameters()`` for PyTorch models.
        :param kwargs: additional parameters.
        """
        if model_params is not None and not hasattr(model_params, "__next__"):
            raise RuntimeError("model parameters should be a generator, rather than {}.".format(type(model_params)))
        self.model_params = model_params
        self.settings = kwargs
    
    def construct_from_pytorch(self, model_params):
        raise NotImplementedError

    @staticmethod
    def _get_require_grads_param(params):
        """

        :param iterable params: parameters
        :return: list(nn.Parameters)
        """
        return [param for param in params if param.requires_grad]


class NullOptimizer(Optimizer):
    """

    """
    def __init__(self):
        super().__init__(None)

    def construct_from_pytorch(self, model_params):
        return self

    def __getattr__(self, item):
        def pass_func(*args, **kwargs):
            pass

        return pass_func


class SGD(Optimizer):
    """
    SGD
    """
    
    def __init__(self, lr=0.001, momentum=0, model_params=None):
        """
        :param float lr: learning rate. Default: 0.01
        :param float momentum: momentum. Default: 0
        :param model_params: a generator. E.g. ``model.parameters()`` for PyTorch models.
        """
        if not isinstance(lr, float):
            raise TypeError("learning rate has to be float.")
        super(SGD, self).__init__(model_params, lr=lr, momentum=momentum)
    
    def construct_from_pytorch(self, model_params):
        if self.model_params is None:
            # careful! generator cannot be assigned.
            return torch.optim.SGD(self._get_require_grads_param(model_params), **self.settings)
        else:
            return torch.optim.SGD(self._get_require_grads_param(self.model_params), **self.settings)


class Adam(Optimizer):
    """
    Adam
    """
    
    def __init__(self, lr=0.001, weight_decay=0, betas=(0.9, 0.999), eps=1e-8, amsgrad=False, model_params=None):
        """
        
        :param float lr: learning rate
        :param float weight_decay:
        :param eps:
        :param amsgrad:
        :param model_params: a generator. E.g. ``model.parameters()`` for PyTorch models.
        """
        if not isinstance(lr, float):
            raise TypeError("learning rate has to be float.")
        super(Adam, self).__init__(model_params, lr=lr, betas=betas, eps=eps, amsgrad=amsgrad,
                                   weight_decay=weight_decay)
    
    def construct_from_pytorch(self, model_params):
        if self.model_params is None:
            # careful! generator cannot be assigned.
            return torch.optim.Adam(self._get_require_grads_param(model_params), **self.settings)
        else:
            return torch.optim.Adam(self._get_require_grads_param(self.model_params), **self.settings)


class AdamW(TorchOptimizer):
    r"""
    """

    def __init__(self, params, lr=1e-3, betas=(0.9, 0.999), eps=1e-8,
                 weight_decay=1e-2, amsgrad=False):
        """
        """
        if not 0.0 <= lr:
            raise ValueError("Invalid learning rate: {}".format(lr))
        if not 0.0 <= eps:
            raise ValueError("Invalid epsilon value: {}".format(eps))
        if not 0.0 <= betas[0] < 1.0:
            raise ValueError("Invalid beta parameter at index 0: {}".format(betas[0]))
        if not 0.0 <= betas[1] < 1.0:
            raise ValueError("Invalid beta parameter at index 1: {}".format(betas[1]))
        defaults = dict(lr=lr, betas=betas, eps=eps,
                        weight_decay=weight_decay, amsgrad=amsgrad)
        super(AdamW, self).__init__(params, defaults)

    def __setstate__(self, state):
        super(AdamW, self).__setstate__(state)
        for group in self.param_groups:
            group.setdefault('amsgrad', False)

    def step(self, closure=None):
        """
        """
        loss = None
        if closure is not None:
            loss = closure()

        for group in self.param_groups:
            for p in group['params']:
                if p.grad is None:
                    continue

                # Perform stepweight decay
                p.data.mul_(1 - group['lr'] * group['weight_decay'])

                # Perform optimization step
                grad = p.grad.data
                if grad.is_sparse:
                    raise RuntimeError('Adam does not support sparse gradients, please consider SparseAdam instead')
                amsgrad = group['amsgrad']

                state = self.state[p]

                # State initialization
                if len(state) == 0:
                    state['step'] = 0
                    # Exponential moving average of gradient values
                    state['exp_avg'] = torch.zeros_like(p.data)
                    # Exponential moving average of squared gradient values
                    state['exp_avg_sq'] = torch.zeros_like(p.data)
                    if amsgrad:
                        # Maintains max of all exp. moving avg. of sq. grad. values
                        state['max_exp_avg_sq'] = torch.zeros_like(p.data)

                exp_avg, exp_avg_sq = state['exp_avg'], state['exp_avg_sq']
                if amsgrad:
                    max_exp_avg_sq = state['max_exp_avg_sq']
                beta1, beta2 = group['betas']

                state['step'] += 1

                # Decay the first and second moment running average coefficient
                exp_avg.mul_(beta1).add_(1 - beta1, grad)
                exp_avg_sq.mul_(beta2).addcmul_(1 - beta2, grad, grad)
                if amsgrad:
                    # Maintains the maximum of all 2nd moment running avg. till now
                    torch.max(max_exp_avg_sq, exp_avg_sq, out=max_exp_avg_sq)
                    # Use the max. for normalizing running avg. of gradient
                    denom = max_exp_avg_sq.sqrt().add_(group['eps'])
                else:
                    denom = exp_avg_sq.sqrt().add_(group['eps'])

                bias_correction1 = 1 - beta1 ** state['step']
                bias_correction2 = 1 - beta2 ** state['step']
                step_size = group['lr'] * math.sqrt(bias_correction2) / bias_correction1

                p.data.addcdiv_(-step_size, exp_avg, denom)

        return loss