from torch import nn
import torch
from ..utils import spectral_norm
from ..models import bvae
from .. import utils

import numpy as np


def get_activation(activation):
    if activation.lower() == "relu":
        return nn.ReLU(inplace=True)
    elif activation.lower() == "prelu":
        return nn.PReLU()
    elif activation.lower() == "sigmoid":
        return nn.Sigmoid()
    elif activation.lower() == "leakyrelu":
        return nn.LeakyReLU(0.2, inplace=True)


class BasicLayer(nn.Module):
    def __init__(
        self, ch_in, ch_out, output_padding=1, ksize=4, dstep=2, activation="relu"
    ):
        super(BasicLayer, self).__init__()

        self.main = nn.Sequential(
            nn.Conv2d(ch_in, ch_out, ksize, dstep, padding=output_padding, bias=True),
            nn.BatchNorm2d(ch_out),
            get_activation(activation),
        )

    def forward(self, x):
        return self.main(x)


class BasicLayerSpectral(nn.Module):
    def __init__(
        self, ch_in, ch_out, output_padding=1, ksize=4, dstep=2, activation="leakyrelu"
    ):
        super(BasicLayerSpectral, self).__init__()

        self.main = nn.Sequential(
            spectral_norm(
                nn.Conv2d(
                    ch_in, ch_out, ksize, dstep, padding=output_padding, bias=True
                )
            ),
            nn.BatchNorm2d(ch_out),
            get_activation(activation),
        )

    def forward(self, x):
        return self.main(x)


class ProjLayer(nn.Module):
    def __init__(
        self,
        ch_in,
        ch_out,
        ch_proj_class,
        ch_proj_in=None,
        activation="relu",
        output_padding=1,
        ksize=4,
        dstep=2,
    ):
        super(ProjLayer, self).__init__()

        if ch_proj_in is None:
            ch_proj_in = ch_out

        self.conv = nn.Conv2d(
            ch_in, ch_out, ksize, dstep, padding=output_padding, bias=True
        )
        self.bn = nn.BatchNorm2d(ch_out)
        self.activation = get_activation(activation)

        self.proj = BasicLayer(ch_proj_in, ch_out, 0, 1, 1)
        self.proj_class = BasicLayer(ch_proj_class, ch_out, 0, 1, 1)

    def forward(self, x, x_proj, x_class):

        x = self.conv(x)
        x_class = self.proj_class(x_class.unsqueeze(2).unsqueeze(3)).expand(
            x.shape[0], x.shape[1], x.shape[2], x.shape[3]
        )
        x = x + x_class + self.proj(x_proj)
        x = self.bn(x)
        x = self.activation(x)

        return x


class ProjLayerFancy(nn.Module):
    def __init__(
        self,
        ch_in,
        ch_out,
        ch_proj_in=None,
        output_padding=1,
        ksize=4,
        dstep=2,
        activation="leakyrelu",
    ):
        super(ProjLayerFancy, self).__init__()

        if ch_proj_in is None:
            ch_proj_in = ch_out

        self.conv = spectral_norm(
            nn.Conv2d(ch_in, ch_out, ksize, dstep, padding=output_padding, bias=True)
        )
        self.bn = nn.BatchNorm2d(ch_out)
        self.activation = get_activation(activation)

        self.proj = nn.Sequential(
            spectral_norm(nn.Conv2d(ch_proj_in, ch_out, 1, 1, 0, bias=True)),
            nn.BatchNorm2d(ch_out),
            nn.LeakyReLU(0.2, inplace=True),
        )

    def forward(self, x, x_proj):
        x = self.conv(x)
        x_proj = self.proj(x_proj.unsqueeze(2).unsqueeze(3)).expand(
            x.shape[0], x.shape[1], x.shape[2], x.shape[3]
        )

        x = x + x_proj
        x = self.bn(x)
        x = self.activation(x)

        return x


class BasicLayerTranspose(nn.Module):
    def __init__(
        self, ch_in, ch_out, output_padding=0, ksize=4, dstep=2, activation="relu"
    ):
        super(BasicLayerTranspose, self).__init__()

        self.main = nn.Sequential(
            nn.ConvTranspose2d(
                ch_in, ch_out, ksize, dstep, 1, output_padding=output_padding, bias=True
            ),
            nn.BatchNorm2d(ch_out),
            get_activation(activation),
        )

    def forward(self, x):
        return self.main(x)


class ProjLayerTranspose(nn.Module):
    def __init__(
        self,
        ch_in,
        ch_out,
        ch_proj_in=None,
        activation="relu",
        output_padding=0,
        ksize=4,
        dstep=2,
    ):
        super(ProjLayerTranspose, self).__init__()

        if ch_proj_in is None:
            ch_proj_in = ch_out

        self.conv = nn.ConvTranspose2d(
            ch_in, ch_out, ksize, dstep, 1, output_padding=output_padding, bias=True
        )
        self.bn = nn.BatchNorm2d(ch_out)
        self.activation = get_activation(activation)

        self.proj = BasicLayer(ch_proj_in, ch_out, 0, 1, 1)

    def forward(self, x, x_proj):
        x = self.conv(x) + x.proj(x_proj)
        x = self.bn(x)
        x = self.activation(x)

        return x


class ProjLayerTransposeFancy(nn.Module):
    def __init__(
        self,
        ch_in,
        ch_out,
        ch_proj_class,
        ch_proj_in=None,
        activation="relu",
        output_padding=0,
        ksize=4,
        dstep=2,
        batch_norm=True,
    ):
        super(ProjLayerTransposeFancy, self).__init__()

        if ch_proj_in is None:
            ch_proj_in = ch_out

        self.conv = nn.ConvTranspose2d(
            ch_in, ch_out, ksize, dstep, 1, output_padding=output_padding, bias=True
        )

        if batch_norm:
            self.bn = nn.BatchNorm2d(ch_out)
        else:
            self.bn = None

        self.activation = get_activation(activation)

        self.proj = BasicLayer(ch_proj_in, ch_out, 0, 1, 1)
        self.proj_class = BasicLayer(ch_proj_class, ch_out, 0, 1, 1)

    def forward(self, x, x_proj, x_class):

        x = self.conv(x)
        x_class = self.proj_class(x_class.unsqueeze(2).unsqueeze(3)).expand(
            x.shape[0], x.shape[1], x.shape[2], x.shape[3]
        )

        x = x + x_class + self.proj(x_proj)

        if self.bn is not None:
            x = self.bn(x)

        x = self.activation(x)

        return x


class Enc(nn.Module):
    def __init__(
        self,
        n_latent_dim,
        n_classes,
        n_ref,
        n_channels,
        n_channels_target,
        gpu_ids,
        activation="ReLU",
        pretrained_path=None,
        ch_ref=[0, 2],
        ch_target=[1],
    ):
        super(Enc, self).__init__()

        self.gpu_ids = gpu_ids
        self.fcsize = 2

        self.ch_ref = ch_ref
        self.ch_target = ch_target

        self.n_ref = n_ref
        self.n_latent_dim = n_latent_dim

        if pretrained_path is not None:
            pass
        else:
            self.ref_path = nn.ModuleList([BasicLayer(n_channels, 64)])

            self.target_path = nn.ModuleList(
                [ProjLayer(n_channels_target, 64, n_classes)]
            )

            ch_in = 64
            ch_max = 1024

            for i in range(5):
                ch_out = ch_in * 2
                if ch_out > ch_max:
                    ch_out = ch_max

                self.ref_path.append(BasicLayer(ch_in, ch_out))
                self.target_path.append(ProjLayer(ch_in, ch_out, n_classes))

                ch_in = ch_out

        if self.n_ref > 0:
            self.ref_out_mu = nn.Sequential(
                nn.Linear(ch_in * int(self.fcsize * 1 * 1), self.n_ref, bias=True)
            )

            self.ref_out_sigma = nn.Sequential(
                nn.Linear(ch_in * int(self.fcsize * 1 * 1), self.n_ref, bias=True)
            )

        if self.n_latent_dim > 0:
            self.latent_out_mu = nn.Sequential(
                nn.Linear(
                    ch_in * int(self.fcsize * 1 * 1), self.n_latent_dim, bias=True
                )
            )

            self.latent_out_sigma = nn.Sequential(
                nn.Linear(
                    ch_in * int(self.fcsize * 1 * 1), self.n_latent_dim, bias=True
                )
            )

    def forward(self, x, x_class):
        # gpu_ids = None
        # if isinstance(x.data, torch.cuda.FloatTensor) and len(self.gpu_ids) > 1:
        gpu_ids = self.gpu_ids

        x_ref = x[:, self.ch_ref]
        x_target = x[:, self.ch_target]

        for ref_path, target_path in zip(self.ref_path, self.target_path):
            x_ref = nn.parallel.data_parallel(ref_path, x_ref, gpu_ids)
            x_target = nn.parallel.data_parallel(
                target_path, (x_target, x_ref, x_class), gpu_ids
            )

        x_ref = x_ref.view(x_ref.size()[0], 1024 * int(self.fcsize * 1 * 1))
        x_target = x_target.view(x_target.size()[0], 1024 * int(self.fcsize * 1 * 1))

        xOut = list()

        if self.n_ref > 0:
            xRefMu = nn.parallel.data_parallel(self.ref_out_mu, x_ref, gpu_ids)
            xRefLogSigma = nn.parallel.data_parallel(self.ref_out_sigma, x_ref, gpu_ids)

            xOut.append([xRefMu, xRefLogSigma])

        if self.n_latent_dim > 0:
            xLatentMu = nn.parallel.data_parallel(self.latent_out_mu, x_target, gpu_ids)
            xLatentLogSigma = nn.parallel.data_parallel(
                self.latent_out_sigma, x_target, gpu_ids
            )

            xOut.append([xLatentMu, xLatentLogSigma])

        return xOut


class Dec(nn.Module):
    def __init__(
        self,
        n_latent_dim,
        n_classes,
        n_ref,
        n_channels,
        n_channels_target,
        gpu_ids,
        output_padding=(0, 1),
        pretrained_path=None,
        ch_ref=[0, 2],
        ch_target=[1],
    ):

        super(Dec, self).__init__()

        self.gpu_ids = gpu_ids
        self.fcsize = 2

        self.n_latent_dim = n_latent_dim
        self.n_classes = n_classes
        self.n_ref = n_ref

        self.n_channels = n_channels
        self.n_channels_target = n_channels_target

        self.ch_ref = ch_ref
        self.ch_target = ch_target

        if pretrained_path is not None:
            pass

        else:

            self.ref_fc = nn.Linear(
                self.n_ref, 1024 * int(self.fcsize * 1 * 1), bias=True
            )
            self.target_fc = nn.Linear(
                self.n_latent_dim, 1024 * int(self.fcsize * 1 * 1), bias=True
            )
            self.ref_bn_relu = nn.Sequential(
                nn.BatchNorm2d(1024), nn.ReLU(inplace=True)
            )
            self.target_bn_relu = nn.Sequential(
                nn.BatchNorm2d(1024), nn.ReLU(inplace=True)
            )

            self.proj_ref_bn_relu = BasicLayer(
                1024, 1024, output_padding=0, ksize=4, dstep=2
            )
            self.proj_class_bn_relu = BasicLayer(
                1024, 1024, output_padding=0, ksize=4, dstep=2
            )

            self.ref_path = nn.ModuleList([])
            self.target_path = nn.ModuleList([])

            l_sizes = [1024, 1024, 512, 256, 128, 64]
            for i in range(len(l_sizes) - 1):
                if i == 0:
                    padding = output_padding
                else:
                    padding = 0

                self.ref_path.append(
                    BasicLayerTranspose(
                        l_sizes[i], l_sizes[i + 1], output_padding=padding
                    )
                )
                self.target_path.append(
                    ProjLayerTransposeFancy(
                        l_sizes[i],
                        l_sizes[i + 1],
                        ch_proj_class=n_classes,
                        output_padding=padding,
                    )
                )

            self.ref_path.append(
                nn.Sequential(
                    nn.ConvTranspose2d(l_sizes[i + 1], n_channels, 4, 2, 1, bias=True),
                    nn.Sigmoid(),
                )
            )

            self.target_path.append(
                ProjLayerTransposeFancy(
                    l_sizes[i + 1],
                    n_channels_target,
                    ch_proj_in=n_channels,
                    ch_proj_class=n_classes,
                    output_padding=padding,
                    batch_norm=False,
                    activation="sigmoid",
                )
            )

    def forward(self, x_in):
        # gpu_ids = None
        # if isinstance(x.data, torch.cuda.FloatTensor) and len(self.gpu_ids) > 1:
        gpu_ids = self.gpu_ids

        x_class, x_ref, x_target = x_in

        x_target = self.target_fc(x_target).view(
            x_target.size()[0], 1024, self.fcsize, 1
        )
        x_target = self.target_bn_relu(x_target)

        x_ref = self.ref_fc(x_ref).view(x_ref.size()[0], 1024, self.fcsize, 1)
        x_ref = self.ref_bn_relu(x_ref)

        for ref_path, target_path in zip(self.ref_path, self.target_path):
            x_ref = nn.parallel.data_parallel(ref_path, x_ref, gpu_ids)

            x_target = nn.parallel.data_parallel(
                target_path, (x_target, x_ref, x_class), gpu_ids
            )

        out_shape = list(x_target.shape)
        out_shape[1] = self.n_channels + self.n_channels_target
        out = torch.zeros(out_shape).type_as(x_ref)

        out[:, self.ch_ref] = x_ref
        out[:, self.ch_target] = x_target

        return out


class DecD(nn.Module):
    def __init__(self, n_classes, n_channels, gpu_ids, noise_std, **kwargs):
        super(DecD, self).__init__()

        self.noise_std = noise_std

        self.noise = torch.zeros(0)

        self.gpu_ids = gpu_ids
        self.fcsize = 2

        self.noise = torch.zeros(0)

        self.path = nn.ModuleList([])

        l_sizes = [n_channels, 64, 128, 256, 512, 1024, 1024]
        for i in range(len(l_sizes) - 1):
            self.path.append(
                BasicLayerSpectral(l_sizes[i], l_sizes[i + 1], activation="leakyrelu")
            )

        self.fc = spectral_norm(
            nn.Linear(1024 * int(self.fcsize), n_classes, bias=True)
        )

    def forward(self, x_in):
        # gpu_ids = None
        # if isinstance(x.data, torch.cuda.FloatTensor) and len(self.gpu_ids) > 1:
        gpu_ids = self.gpu_ids

        if self.noise_std > 0:
            # allocate an appropriately sized variable if it does not exist
            if self.noise.size() != x_in.size():
                self.noise = torch.zeros(x_in.size()).cuda(gpu_ids[0])

            # sample random noise
            self.noise.normal_(mean=0, std=self.noise_std)
            noise = torch.autograd.Variable(self.noise)

            # add to input
            x = x_in + noise
        else:
            x = x_in

        for layer in self.path:
            x = nn.parallel.data_parallel(layer, x, gpu_ids)

        x = x.view(x.size()[0], x.shape[1] * int(self.fcsize))
        out = self.fc(x)

        return out