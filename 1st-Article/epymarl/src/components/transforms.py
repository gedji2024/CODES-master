"""Data transforms applied to episode batch fields before storage.

The OneHot transform converts discrete action indices to one-hot vectors.
It includes a clamp guard against the MPS max() bug that can produce index -1.
"""
import torch as th


class Transform:
    def transform(self, tensor):
        raise NotImplementedError

    def infer_output_info(self, vshape_in, dtype_in):
        raise NotImplementedError


class OneHot(Transform):
    def __init__(self, out_dim):
        self.out_dim = out_dim

    def transform(self, tensor):
        y_onehot = tensor.new(*tensor.shape[:-1], self.out_dim).zero_()
        # Clamp indices to valid range to prevent scatter_ crash from MPS max() bug
        safe_tensor = tensor.long().clamp(0, self.out_dim - 1)
        y_onehot.scatter_(-1, safe_tensor, 1)
        return y_onehot.float()

    def infer_output_info(self, vshape_in, dtype_in):
        return (self.out_dim,), th.float32