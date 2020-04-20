#!/usr/bin/env python3

import os
import random
from random import randint
import itertools
import numpy as np
from typing import List, Tuple, Dict, Any
from nptyping import Array
from pymatgen import (
  Structure,
  Molecule,
  Lattice,
)
from pymatgen.core.periodic_table import is_valid_symbol
from pymatgen.core.sites import PeriodicSite
from pymatgen.core.surface import (
  generate_all_slabs,
  SlabGenerator,
  get_symmetrically_distinct_miller_indices,
  )
from pymatgen.transformations.site_transformations \
  import ReplaceSiteSpeciesTransformation

class StructureChanger:
  def __init__(self,
               structure: Structure):
    self.old_structure = structure.copy()
    self.operations = []

  def scale_volume(self,
                   scale: float = 0.01) -> Structure:
    '''
    Scale the lattice with given parameter.
    Vol_new = Vol_old * (1 + scale)

    @in
      - scale, float

    @out
      - Structure
    '''
    struct = self.old_structure.copy()
    struct.scale_lattice(
      (1 + scale) * self.old_structure.volume
    )
    self.operations.append({'V scaling': scale})
    return struct

  def apply_defect(self,
                   number:          int,
                   defect_type:     str = 'vac',
                   supercell: List[int] = [1, 1, 1],
                   element:         str = '') -> Structure:
    '''
    Apply the defects, i.e. make changes to the structure including
    removing, substitution and etc.

    @in
      - defect_type, str:
        - vac: randomly remove some sites with given number of atoms
        - subs: randomly substitute some sites with given element
                a number of substitution operations is need.
        - inte: not implemented yet
        - vint: not implemented yet
      - supercell, [int, int, int]
      - element, str, must be a valid element symbol

    @out
      - Structure
    '''
    assert number >= 0, f"Number of defects should be non-negative"
    assert len(supercell) == 3, f"Length of supercell list must be 3"

    sc = self.old_structure.copy()
    sc.make_supercell(supercell)
    indices = random.sample(range(len(sc)), number)  # Select the apply site
    if 'vac' == defect_type:
      rest_id = [i for i in range(len(sc)) if i not in indices]
      new_structure = sc[rest_id].copy()
      self.operations.append({'vacancy': number})
      return new_structure

    elif 'subs' == defect_type:
      assert is_valid_symbol(element), f'Invalid element input: "{element}"'
      ops = {i: element for i in indices}
      trans = ReplaceSiteSpeciesTransformation(ops)
      new_structure = trans.apply_transformation(sc)
      new_structure.sort()
      self.operations.append({'substitution': number})
      return new_structure

    elif 'inte' == defect_type:
      raise Exception(f'This type of defect ({defect_type}) is still in developing')

    elif 'vint' == defect_type:
      raise Exception(f'This type of defect ({defect_type}) is still in developing')

    else:
      raise Exception(f'Invalid defect type input: "{defect_type}"')

  def get_slabs(self,
                max_index:                      int = 1,
                min_slab_size:                float = 5.0,
                min_vacuum_size:              float = 15.0,
                is_fix_vacuum_size:            bool = False,
                bonds: Dict[Tuple[str, str], float] = None,
                tolerance:                    float = 0.001,
                max_broken_bonds:               int = 0,
                is_lll_reduce:                 bool = False,
                is_center_slab:                bool = False,
                is_primitive:                  bool = True,
                max_normal_search:              int = None,
                is_symmetrize:                 bool = False,
                is_repair:                     bool = False,
                is_in_unit_planes:             bool = False) -> List[Structure]:
    '''
    Search and return the slabs found in the given structure.

    @in
      - max_index, int, max of miller index.
        e.g. when max_index = 1 for cubic structure, only (100), (110), (111)
        miller surfaces are searched.
      - min_slab_size, float, minimum size in angstroms of layers containing atoms
      - min_vacuum_size, float, minimum size in angstroms of vacuum layer
      - is_fix_vacuum_size, bool, Not implemented yet
      - bonds, {(str, str): float}, specify the maximum length of bond length for
        given atom pairs to avoid bond broken.
      - tolerance, float, accuracy
      - max_broken_bonds, int
      - is_lll_reduce, bool, whether or not the slabs will be orthogonalized
      - is_center_slab, bool, whether or not the slabs will be centered between
        the vacuum layer
      - is_primitive, bool, whether to reduce any generated slabs to a primitive
        cell
      - max_normal_search, If set to a positive integer, the code will conduct a
        search for a normal lattice vector that is as perpendicular to the surface
        as possible by considering multiples linear combinations of lattice vectors
        up to max_normal_search.
      - is_symmetrize, bool, Whether or not to ensure the surfaces of the slabs
        are equivalent
      - is_repair, bool, whether to repair terminations with broken bonds or just
        omit them
      - is_in_unit_planes, bool, whether to set min_slab_size and min_vac_size
        in units of hkl planes (True) or Angstrom (False/default)
    @out
    '''

    st = self.old_structure.copy()
    all_slabs = []
    for miller in get_symmetrically_distinct_miller_indices(st, max_index):
        if is_fix_vacuum_size:
            pass

        else:
            vacuum_size = random.random() * min_vacuum_size

        gen = SlabGenerator(st,
                            miller,
                            min_slab_size,
                            vacuum_size,
                            lll_reduce=is_lll_reduce,
                            center_slab=is_center_slab,
                            primitive=is_primitive,
                            max_normal_search=max_normal_search,
                            in_unit_planes=is_in_unit_planes)
        slabs = gen.get_slabs(bonds=bonds,
                              tol=tolerance,
                              symmetrize=is_symmetrize,
                              max_broken_bonds=max_broken_bonds,
                              repair=is_repair)

        if len(slabs) > 0:
            all_slabs.extend(slabs)

    self.operations.append({'slabs': len(slabs)})
    return all_slabs

  def swap_site(self,
                 pair: Tuple[Any, Any]) -> Structure:
    '''
    Swap sites according to index

    @in
      - pair, (int, int), or ([int], [int]), must be valid site indices

    @out
      Structure
    '''
    ns = self.old_structure.copy()
    ns[pair[0]] = self.old_structure[pair[1]]
    ns[pair[1]] = self.old_structure[pair[0]]
    self.operations.append({'swap_site': pair.copy()})
    return ns

  def random_swap(self,
                  forbidden_list: List[Tuple[str, str]] = []) -> Structure:
    '''
    Ramdomly swap two sites that not belongs to given list of element pairs.
    ONLY two sites will be swapped.

    @in
      - forbidden_list, [(str, str)], list of element pairs, which contains the
        element pairs that will not be swapped

    @out
      Structure
    '''
    assert len(self.old_structure.composition) > 1
    pairs = list(itertools.combinations(self.old_structure.symbol_set, 2))
    flist = forbidden_list
    for pair in pairs:
      for fpair in flist:
        if pair == tuple(fpair) or pair == tuple(reversed(fpair)):
          pairs.remove(pair)

    pair = random.choice(pairs)  # randomly select two elements

    indices0 = [i for i, x in enumerate(self.old_strcucture.species)
                if x.symbol == pair[0]]
    index0 = random.choice(indices0)  # select one site belongs to element 0

    indices1 = [i for i, x in enumerate(self.old_strcucture.species)
                if x.symbol == pair[1]]
    index1 = random.choice(indices1)  # select one site belongs to element 1
    return self.swap_site((index0, index1))

  def deform_cell(self,
                  stress_eps: Array[float]) -> Structure:
    '''
    Deform the lattice of the structure

    @in
      - stress_eps, 1darray, will be converted to a transform matrix

    @out
      Structure
    '''
    ns = self.old_structure.copy()
    stress = np.eye(3) + np.diag(stress_eps[:3]) +\
      np.array([[          0.0, stress_eps[3], stress_eps[4]],
                [stress_eps[3],           0.0, stress_eps[5]],
                [stress_eps[4], stress_eps[5],           0.0]])
    ns.modify_lattice(Lattice(np.dot(stress, self.old_structure.lattice.matrix)))
    self.operations.append({'deform_cell': stress_eps})
    return ns

  def random_deform_cell(self,
                         is_diag: bool,
                         maxdelta: float = 0.01) -> Structure:
    '''
    Deform a cell slightly and randomly

    @in
      - is_diag, bool, whether generate a diagonal transformation matrix or not
      - maxdelta, float, maximum scalar of deformation

    @out
      Structure
    '''
    stress_eps = np.random.random(6) * 2 * maxdelta - maxdelta
    if is_diag:
      stress_eps[:3] = 0
    else:
      stress_eps[-3:] = 0
    return self.deform_cell(stress_eps)
