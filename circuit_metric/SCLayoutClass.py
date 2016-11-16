import bidict as bd
import itertools as it
from math import copysign
from operator import add
import sparse_pauli as sp 


#------------------------------constants------------------------------#
SHIFTS = {
            'N': ((-1, 1), (1, 1)),
            'E': ((1, 1), (1, -1)),
            'W': ((-1, 1), (-1, -1)),
            'S': ((1, -1), (-1, -1))
            }
SHIFTS['A'] = SHIFTS['E'] + SHIFTS['W']
SHIFTS_README = """(dx, dy) so that, given an ancilla co-ordinate
                   (x, y), there will be data qubits at
                   (x + dx, y + dy)."""
LOCS_README = """dict of whitelists for location types, including
                 single/two-qubit gates, X/Z preparations,
                 and X/Z measurements, with other special gates 
                 in for good measure"""
LOCS = dict()
LOCS['SINGLE_GATES'] = ['I', 'H', 'P',
                        'X90', 'Y90', 'Z90',
                        'X', 'Y', 'Z',
                        'X180', 'Y180', 'Z180']
LOCS['DOUBLE_GATES'] = ['CNOT', 'CPHASE', 'ZZ90', 'SWAP']
LOCS['PREPARATIONS'] = ['P_X', 'P_Z']
LOCS['MEASUREMENTS'] = ['M_X', 'M_Z']
#---------------------------------------------------------------------#


class SCLayout(object):
    """
    wraps a bunch of lists of 2d co-ordinates that I use for producing
    surface code circuits.

    Ancilla-symmetry is broken by the convention that there is a 
    weight-2 XX stabiliser at the top left. 
    """
    def __init__(self, d):
        
        self.datas = list(it.product(range(1, 2 * d, 2), repeat=2))

        anc = {'x_sq': (), 'z_sq': (), 'x_top': (), 'x_bot': (), 'z_left': (), 'z_right': ()}

        anc['x_top'] = tuple([(x, 2 * d) for x in range(2, 2 * d, 4)])
        anc['z_right'] = tuple([(2 * d, y) for y in range(4, 2 * d, 4)])
        anc['z_left'] = tuple([(0, y) for y in range(2 * d - 4, 0, -4)])
        anc['x_bot'] = tuple([(x, 0) for x in range(2 * d - 2, 0, -4)])
        x_sq_anc = tuple(it.product(range(4, 2 * d, 4),
                                    range(2 * d - 2, 0, -4)))
        x_sq_anc += tuple(it.product(range(2, 2 * d, 4), 
                                     range(2 * d - 4, 0, -4)))
        anc['x_sq'] = x_sq_anc

        z_sq_anc = tuple(it.product(range(2, 2 * d, 4), 
                                    range(2 * d - 2, 0, -4)))
        z_sq_anc += tuple(it.product(range(4, 2 * d, 4), 
                                     range(2 * d - 4, 0, -4)))
        anc['z_sq'] = z_sq_anc
        self.ancillas = anc
        
        bits = self.datas + list(it.chain.from_iterable(anc.values()))

        self.map = bd.bidict(zip(sorted(bits), range(len(bits))))
        self.d = d
        self.n = 2 * d**2 - 1

    # @property
    def x_ancs(self, dx=None):
        names = ['x_sq', 'x_top', 'x_bot']
        if dx == 0:
            names.remove('x_top')
        elif dx == 1:
            names.remove('x_bot')
        return reduce(add, [self.ancillas[key] for key in names])
    
    # @property
    def z_ancs(self, dx=None):
        names = ['z_sq', 'z_left', 'z_right']
        if dx == 0:
            names.remove('z_right')
        elif dx == 1:
            names.remove('z_left')
        return reduce(add, [self.ancillas[key] for key in names])

    def anc_type(self, anc):
        """
        Super-dangerous, I've assumed correct input.
        FIXME
        TODO
        """
        if isinstance(anc, int):
            anc = self.map.inv[anc]
        return 'X' if anc in self.x_ancs() else 'Z'

    def stabilisers(self):
        """
        Sometimes it's convenient to have the stabilisers of a surface
        code, especially when doing a 2d example. 
        """
        x_stabs, z_stabs = {}, {}
        
        #TODO: Fix Copypasta, PEP8 me.

        for crd_tag, shft_tag in zip(['x_sq', 'x_top', 'x_bot'],
                                     ['A',    'S',     'N'    ]): 
            for crd in self.ancillas[crd_tag]:
                pauli = sp.Pauli(
                    x_set=[self.map[ad(crd, dx)]
                    for dx in SHIFTS[shft_tag]])
                x_stabs[self.map[crd]] = pauli
        
        for crd_tag, shft_tag in zip(['z_sq', 'z_left', 'z_right'],
                                     ['A',    'E',      'W'    ]): 
            for crd in self.ancillas[crd_tag]:
                pauli = sp.Pauli(
                    z_set=[self.map[ad(crd, dx)]
                    for dx in SHIFTS[shft_tag]])
                z_stabs[self.map[crd]] = pauli
        
        return {'X' : x_stabs, 'Z' : z_stabs}
    
    def logicals(self):
        x_set = [
                    self.map[_] 
                    for _ in 
                    filter(lambda pr: pr[0] == 1, self.datas)
                    ]
        z_set = [
                    self.map[_] 
                    for _ in
                    filter(lambda pr: pr[1] == 1, self.datas)
                    ]
        return [sp.Pauli(x_set, []), sp.Pauli([], z_set)]

    def boundary_points(self, log_type):
        """
        Returns a set of fictional points that you can use to turn a 
        boundary distance finding problem into a pairwise distance 
        finding problem, with the typical IID XZ 2D scenario.
        logicals of the type 'log_type' have to traverse between pairs
        of output boundary points 
        """
        d = self.d
        x_top = tuple([(x, 2 * d) for x in range(0, 2 * d, 4)])
        z_right = tuple([(2 * d, y) for y in range(2, 2 * d + 1, 4)])
        z_left = tuple([(0, y) for y in range(2 * d - 2, -1, -4)])
        x_bot = tuple([(x, 0) for x in range(2 * d, 0, -4)])
        return x_top + x_bot if log_type == 'X' else z_right + z_left

    def extractor(self):
        """
        Returns a circuit for doing syndrome extraction, including:
        + Preparation at the right time (ancilla qubits are prepared
          immediately before their first CNOT gate)
        + Four CNOT timesteps in line with Tomita/Svore
        + Measurement at the right time (syndrome qubits are measured 
          immediately after their last CNOT)
        """       
        # Tomita/Svore six-step circuit
        t_0 = self.op_set_1('P_X', self.x_ancs(0))
        t_0 += self.op_set_1('P_Z', self.z_ancs(0))

        t_1 = self.x_cnot((1, 1), self.x_ancs(0))
        t_1 += self.z_cnot((1, 1), self.z_ancs(0))
        
        t_2 = self.x_cnot((-1, 1), self.x_ancs(0))
        t_2 += self.z_cnot((1, -1), self.z_ancs(0))
        t_2 += self.op_set_1('P_X', self.ancillas['x_top'])
        t_2 += self.op_set_1('P_Z', self.ancillas['z_right'])
        
        t_3 = self.x_cnot((1, -1), self.x_ancs(1))
        t_3 += self.z_cnot((-1, 1), self.z_ancs(1))
        t_3 += self.op_set_1('M_X', self.ancillas['x_bot'])
        t_3 += self.op_set_1('M_Z', self.ancillas['z_left'])
        
        t_4 = self.x_cnot((-1, -1), self.x_ancs(1))
        t_4 += self.z_cnot((-1, -1), self.z_ancs(1))
        
        t_5 = self.op_set_1('M_X', self.x_ancs(1))
        t_5 += self.op_set_1('M_Z', self.z_ancs(1))
        timesteps = [t_0, t_1, t_2, t_3, t_4, t_5]
        
        # pad with waits, assuming destructive measurement
        dat_locs = {self.map[q] for q in self.datas}
        for step in timesteps:
            step.extend([('I', q) for q in dat_locs - support(step)])

        return timesteps

    def op_set_1(self, name, qs):
        return [(name, self.map[q]) for q in qs]

    def x_cnot(self, shft, lst): 
        return [('CNOT', self.map[q], self.map[ad(q, shft)]) for q in lst]

    def z_cnot(self, shft, lst): 
        return [('CNOT', self.map[ad(q, shft)], self.map[q]) for q in lst]

    def path_pauli(self, crd_0, crd_1, err_type):
        """
        Returns a minimum-length Pauli between two ancillas, given the
        type of error that joins the two.

        This function is awkward, because it works implicitly on the
        un-rotated surface code, first finding a "corner" (a place on
        the lattice for the path to turn 90 degrees), then producing
        two diagonal paths on the rotated lattice that go to and from
        this corner. 
        """
        
        mid_v = diag_intersection(crd_0, crd_1, self.ancillas.values())
        
        pth_0, pth_1 = diag_pth(crd_0, mid_v), diag_pth(mid_v, crd_1)

        #path on lattice, uses idxs
        p = [self.map[crd] for crd in pth_0 + pth_1]
        
        pl = sp.Pauli(p, []) if err_type == 'X' else sp.Pauli([], p)
        
        return pl

# -----------------------convenience functions-------------------------#
ad = lambda tpl_0, tpl_1: tuple(a + b for a, b, in zip(tpl_0, tpl_1))


def support(timestep):
    output = []
    for elem in timestep:
        output += elem[1:]
    return set(output)

def diag_pth(crd_0, crd_1):
    """
    Produces a path between two points which takes steps (\pm 2, \pm 2)
    between the two, starting (\pm 1, \pm 1) away from the first.
    """
    dx, dy = crd_1[0] - crd_0[0], crd_1[1] - crd_0[1]
    shft_x, shft_y = map(int, [copysign(1, dx), copysign(1, dy)])
    step_x, step_y = map(int, [copysign(2, dx), copysign(2, dy)])
    return zip(range(crd_0[0] + shft_x, crd_1[0], step_x), 
                range(crd_0[1] + shft_y, crd_1[1], step_y))

def diag_intersection(crd_0, crd_1, ancs=None):
    """
    Uses a little linear algebra to determine where diagonal paths that
    step outward from ancilla qubits intersect.
    This allows us to reduce the problems of length-finding and
    path-making to a pair of 1D problems. 
    """
    a, b, c, d = crd_0[0], crd_0[1], crd_1[0], crd_1[1]
    vs = [
            ( ( d + c - b + a ) / 2, ( d + c + b - a ) / 2 ),
            ( ( d - c - b - a ) / -2, ( -d + c - b - a ) / -2 )
        ]
    
    if ancs:
        if vs[0] in sum(ancs, ()):
            mid_v = vs[0]
        else:
            mid_v = vs[1]
    else:
        mid_v = vs[0]

    return mid_v

# ---------------------------------------------------------------------#

