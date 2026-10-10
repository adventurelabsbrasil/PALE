"""Small randomly initialized temporal convolutional encoder."""

import torch
from torch import nn


class MaskedPredictor(nn.Module):
    def __init__(self, frequency_bins: int, hidden_channels: int = 64) -> None:
        super().__init__()
        layers: list[nn.Module] = [nn.Conv1d(frequency_bins + 1, hidden_channels, 3, padding=1), nn.GELU()]
        for dilation in (2, 4, 8):
            layers.extend((nn.Conv1d(hidden_channels, hidden_channels, 3, padding=dilation, dilation=dilation), nn.GELU()))
        self.encoder = nn.Sequential(*layers)
        self.decoder = nn.Conv1d(hidden_channels, frequency_bins, 1)
        nn.init.zeros_(self.decoder.weight)
        nn.init.zeros_(self.decoder.bias)

    def forward(self, masked: torch.Tensor, mask: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
        hidden = self.encoder(torch.cat((masked, mask), dim=1))
        return masked + self.decoder(hidden), hidden.mean(dim=-1)


class FuturePredictor(nn.Module):
    """Small from-scratch predictor used for the second exploratory world."""

    def __init__(self, frequency_bins: int, hidden_size: int = 32) -> None:
        super().__init__()
        self.encoder = nn.Sequential(
            nn.Linear(frequency_bins, hidden_size),
            nn.GELU(),
            nn.Linear(hidden_size, hidden_size),
            nn.GELU(),
        )
        self.decoder = nn.Linear(hidden_size, frequency_bins)

    def forward(self, past: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
        hidden = self.encoder(past)
        return self.decoder(hidden), hidden
