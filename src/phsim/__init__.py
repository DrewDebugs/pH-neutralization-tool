"""phsim: pH neutralization design and control model (pure Python, standard library only).

Modules, in the order they build on each other:
    constants  -> chemistry -> titration -> plant -> control -> simulate
    linear (linearization + Routh-Hurwitz), design (staging comparison)
    api (JSON bridge for the website), theory_map (equation <-> code index)
"""
