"""Shared plot style for all deck / manuscript figures.

Usage (top of every plot script, after imports):

    from src.plot_style import apply_style, PALETTE
    apply_style()

Design rules:
  * One accent palette across every figure (Israel teal, UK blue,
    cost red, neutral slate, highlight amber).
  * No top/right spines, subtle y-grid only, left-aligned bold titles.
  * Direct value labels preferred over legends where practical.
  * savefig dpi 180 for crisp deck embedding.
"""

import matplotlib as mpl

PALETTE = {
    "israel":   "#0f766e",   # teal — Israeli series
    "israel_lt":"#99d5cd",
    "uk":       "#1d4ed8",   # blue — UK series
    "uk_lt":    "#bfdbfe",
    "cost":     "#b91c1c",   # red — costs / degradation
    "cost_lt":  "#fecaca",
    "neutral":  "#475569",   # slate — annotations
    "amber":    "#d97706",   # highlight
    "amber_lt": "#fde68a",
    "grid":     "#94a3b8",
}


def apply_style() -> None:
    mpl.rcParams.update({
        "font.family":      "DejaVu Sans",
        "font.size":        11,
        "axes.titlesize":   12.5,
        "axes.titleweight": "bold",
        "axes.titlelocation": "left",
        "axes.titlepad":    12,
        "axes.labelsize":   11,
        "axes.edgecolor":   "#334155",
        "axes.linewidth":   0.8,
        "axes.spines.top":    False,
        "axes.spines.right":  False,
        "axes.grid":        True,
        "axes.axisbelow":   True,
        "grid.alpha":       0.25,
        "grid.linewidth":   0.6,
        "grid.color":       PALETTE["grid"],
        "legend.frameon":   False,
        "legend.fontsize":  9.5,
        "figure.facecolor": "white",
        "savefig.facecolor": "white",
        "savefig.dpi":      180,
        "xtick.labelsize":  10,
        "ytick.labelsize":  10,
        "xtick.color":      "#334155",
        "ytick.color":      "#334155",
    })
