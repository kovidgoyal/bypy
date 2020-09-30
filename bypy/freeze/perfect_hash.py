#!/usr/bin/env python
# From: https://github.com/ilanschnell/perfect-hash
"""
Generate a minimal perfect hash function for the keys in a file,
desired hash values may be specified within this file as well.
A given code template is filled with parameters, such that the
output is code which implements the hash function.
Templates can easily be constructed for any programming language.

The code is based on an a program A.M. Kuchling wrote:
http://www.amk.ca/python/code/perfect-hash

The algorithm the program uses is described in the paper
'Optimal algorithms for minimal perfect hashing',
Z. J. Czech, G. Havas and B.S. Majewski.
http://citeseer.ist.psu.edu/122364.html

The algorithm works like this:

1.  You have K keys, that you want to perfectly hash against some
    desired hash values.

2.  Choose a number N larger than K.  This is the number of
    vertices in a graph G, and also the size of the resulting table G.

3.  Pick two random hash functions f1, f2, that return values from 0..N-1.

4.  Now, for all keys, you draw an edge between vertices f1(key) and f2(key)
    of the graph G, and associate the desired hash value with that edge.

5.  If G is cyclic, go back to step 2.

6.  Assign values to each vertex such that, for each edge, you can add
    the values for the two vertices and get the desired (hash) value
    for that edge.  This task is easy, because the graph is acyclic.
    This is done by picking a vertex, and assigning it a value of 0.
    Then do a depth-first search, assigning values to new vertices so that
    they sum up properly.

7.  f1, f2, and vertex values of G now make up a perfect hash function.


For simplicity, the implementation of the algorithm combines steps 5 and 6.
That is, we check for loops in G and assign the vertex values in one procedure.
If this procedure succeeds, G is acyclic and the vertex values are assigned.
If the procedure fails, G is cyclic, and we go back to step 2, replacing G
with a new graph, and thereby discarding the vertex values from the failed
attempt.
"""

import sys
import random
import string
from collections import defaultdict
from io import StringIO

__version__ = '0.4.2'

verbose = False
trials = 5


class Graph(object):
    """
    Implements a graph with 'N' vertices.  First, you connect the graph with
    edges, which have a desired value associated.  Then the vertex values
    are assigned, which will fail if the graph is cyclic.  The vertex values
    are assigned such that the two values corresponding to an edge add up to
    the desired edge value (mod N).
    """
    def __init__(self, N):
        self.N = N  # number of vertices

        # maps a vertex number to the list of tuples (vertex, edge value)
        # to which it is connected by edges.
        self.adjacent = defaultdict(list)

    def connect(self, vertex1, vertex2, edge_value):
        """
        Connect 'vertex1' and 'vertex2' with an edge, with associated
        value 'value'
        """
        # Add vertices to each other's adjacent list
        self.adjacent[vertex1].append((vertex2, edge_value))
        self.adjacent[vertex2].append((vertex1, edge_value))

    def assign_vertex_values(self):
        """
        Try to assign the vertex values, such that, for each edge, you can
        add the values for the two vertices involved and get the desired
        value for that edge, i.e. the desired hash key.
        This will fail when the graph is cyclic.

        This is done by a Depth-First Search of the graph.  If the search
        finds a vertex that was visited before, there's a loop and False is
        returned immediately, i.e. the assignment is terminated.
        On success (when the graph is acyclic) True is returned.
        """
        self.vertex_values = self.N * [-1]  # -1 means unassigned

        visited = self.N * [False]

        # Loop over all vertices, taking unvisited ones as roots.
        for root in range(self.N):
            if visited[root]:
                continue

            # explore tree starting at 'root'
            self.vertex_values[root] = 0  # set arbitrarily to zero

            # Stack of vertices to visit, a list of tuples (parent, vertex)
            tovisit = [(None, root)]
            while tovisit:
                parent, vertex = tovisit.pop()
                visited[vertex] = True

                # Loop over adjacent vertices, but skip the vertex we arrived
                # here from the first time it is encountered.
                skip = True
                for neighbor, edge_value in self.adjacent[vertex]:
                    if skip and neighbor == parent:
                        skip = False
                        continue

                    if visited[neighbor]:
                        # We visited here before, so the graph is cyclic.
                        return False

                    tovisit.append((vertex, neighbor))

                    # Set new vertex's value to the desired edge value,
                    # minus the value of the vertex we came here from.
                    self.vertex_values[neighbor] = (
                        edge_value - self.vertex_values[vertex]) % self.N

        # check if all vertices have a valid value
        for vertex in range(self.N):
            assert self.vertex_values[vertex] >= 0

        # We got though, so the graph is acyclic,
        # and all values are now assigned.
        return True


class StrSaltHash(object):
    """
    Random hash function generator.
    Simple byte level hashing: each byte is multiplied to another byte from
    a random string of characters, summed up, and finally modulo NG is
    taken.
    """
    chars = string.ascii_letters + string.digits

    def __init__(self, N):
        self.N = N
        self.salt = ''

    def __call__(self, key):
        while len(self.salt) < len(key):  # add more salt as necessary
            self.salt += random.choice(self.chars)

        return sum(ord(self.salt[i]) * ord(c)
                   for i, c in enumerate(key)) % self.N

    template = """
def hash_f(key, T):
    return sum(ord(T[i % $NS]) * ord(c) for i, c in enumerate(key)) % $NG

def perfect_hash(key):
    return (G[hash_f(key, "$S1")] +
            G[hash_f(key, "$S2")]) % $NG
"""


class IntSaltHash(object):
    """
    Random hash function generator.
    Simple byte level hashing, each byte is multiplied in sequence to a table
    containing random numbers, summed tp, and finally modulo NG is taken.
    """
    def __init__(self, N):
        self.N = N
        self.salt = []

    def __call__(self, key):
        while len(self.salt) < len(key):  # add more salt as necessary
            self.salt.append(random.randint(1, self.N - 1))

        return sum(self.salt[i] * ord(c) for i, c in enumerate(key)) % self.N

    template = """
S1 = [$S1]
S2 = [$S2]
assert len(S1) == len(S2) == $NS

def hash_f(key, T):
    return sum(T[i % $NS] * ord(c) for i, c in enumerate(key)) % $NG

def perfect_hash(key):
    return (G[hash_f(key, S1)] + G[hash_f(key, S2)]) % $NG
"""


def builtin_template(Hash):
    return """\
# =======================================================================
# ================= Python code for perfect hash function ===============
# =======================================================================

G = [$G]
""" + Hash.template + """
# ============================ Sanity check =============================

K = [$K]
assert len(K) == $NK

for h, k in enumerate(K):
    if perfect_hash(k) != h:
        raise ValueError(
    f'perfect_hash failed for key: {k} got: {perfect_hash(k)} expected: {h}')
"""


class TooManyInterationsError(Exception):
    pass


def generate_hash(keys, Hash=StrSaltHash):
    """
    Return hash functions f1 and f2, and G for a perfect minimal hash.
    Input is an iterable of 'keys', whos indicies are the desired hash values.
    'Hash' is a random hash function generator, that means Hash(N) returns a
    returns a random hash function which returns hash values from 0..N-1.
    """
    if not isinstance(keys, (list, tuple)):
        raise TypeError("list or tuple expected")
    NK = len(keys)
    if NK != len(set(keys)):
        raise ValueError("duplicate keys")
    for key in keys:
        if not isinstance(key, str):
            raise TypeError("key a not string: %r" % key)
    if NK > 10000 and Hash == StrSaltHash:
        print("""\
WARNING: You have %d keys.
         Using --hft=1 is likely to fail for so many keys.
         Please use --hft=2 instead.
""" % NK)

    # the number of vertices in the graph G
    NG = NK + 1
    if verbose:
        print('NG = %d' % NG)

    trial = 0  # Number of trial graphs so far
    while True:
        if (trial % trials) == 0:  # trials failures, increase NG slightly
            if trial > 0:
                NG = max(NG + 1, int(1.05 * NG))
            if verbose:
                sys.stdout.write('\nGenerating graphs NG = %d ' % NG)
        trial += 1

        if NG > 100 * (NK + 1):
            raise TooManyInterationsError("%d keys" % NK)

        if verbose:
            sys.stdout.write('.')
            sys.stdout.flush()

        G = Graph(NG)  # Create graph with NG vertices
        f1 = Hash(NG)  # Create 2 random hash functions
        f2 = Hash(NG)

        # Connect vertices given by the values of the two hash functions
        # for each key.  Associate the desired hash value with each edge.
        for hashval, key in enumerate(keys):
            G.connect(f1(key), f2(key), hashval)

        # Try to assign the vertex values.  This will fail when the graph
        # is cyclic.  But when the graph is acyclic it will succeed and we
        # break out, because we're done.
        if G.assign_vertex_values():
            break

    if verbose:
        print('\nAcyclic graph found after %d trials.' % trial)
        print('NG = %d' % NG)

    # Sanity check the result by actually verifying that all the keys
    # hash to the right value.
    for hashval, key in enumerate(keys):
        assert hashval == (G.vertex_values[f1(key)] +
                           G.vertex_values[f2(key)]) % NG

    if verbose:
        print('OK')

    return f1, f2, G.vertex_values


class Format(object):
    def __init__(self, width=76, indent=4, delimiter=', '):
        self.width = width
        self.indent = indent
        self.delimiter = delimiter

    def print_format(self):
        print("Format options:")
        for name in 'width', 'indent', 'delimiter':
            print('  %s: %r' % (name, getattr(self, name)))

    def __call__(self, data, quote=False):
        if not isinstance(data, (list, tuple)):
            return str(data)

        lendel = len(self.delimiter)
        aux = StringIO()
        pos = 20
        for i, elt in enumerate(data):
            last = bool(i == len(data) - 1)

            s = ('"%s"' if quote else '%s') % elt

            if pos + len(s) + lendel > self.width:
                aux.write('\n' + (self.indent * ' '))
                pos = self.indent

            aux.write(s)
            pos += len(s)
            if not last:
                aux.write(self.delimiter)
                pos += lendel

        return aux.getvalue()


def generate_code(keys, Hash=None, template=None, num_of_trials=5):
    """
    Takes a list of keys and inserts the generated parameter
    lists into the 'template' string.  'Hash' is the random hash function
    generator.
    The return value is data for formatting templates
    """
    global trials
    trials = num_of_trials
    keys = tuple(keys)
    if Hash is None:
        Hash = StrSaltHash if len(keys) < 10000 else IntSaltHash

    f1, f2, G = generate_hash(keys, Hash)

    assert f1.N == f2.N == len(G)
    try:
        salt_len = len(f1.salt)
        assert salt_len == len(f2.salt)
    except TypeError:
        salt_len = None

    fmt = Format()
    fmt_info = dict(
        NS=salt_len,
        S1=fmt(f1.salt),
        S2=fmt(f2.salt),
        NG=len(G),
        G=fmt(G),
        NK=len(keys),
        K=fmt(list(keys), quote=True),
        Hash=Hash
    )
    return fmt_info


def format_template(fmt_info, template=None):
    if template is None:
        template = builtin_template(fmt_info['Hash'])
    return string.Template(template).substitute(**fmt_info)


def get_c_code(keys):
    fmt_info = generate_code(keys)
    source = format_template(fmt_info)
    m = {}
    exec(source, m, m)
    perfect_hash = m['perfect_hash']
    return perfect_hash, format_template(fmt_info, '''
static int
get_perfect_hash_index_for_key(const char *key) {
    static const int ph_G[] = {$G};
    static const char *ph_K[$NK] = {$K};

    int f1 = 0, f2 = 0, i;
    for (i = 0; key[i] != 0 && i < $NS; i++) {
        f1 += "$S1"[i] * key[i];
        f2 += "$S2"[i] * key[i];
    }
    i = (ph_G[f1 % $NG] + ph_G[f2 % $NG]) % $NG;
    if (i < $NK && i >= 0 && strcmp(key, ph_K[i]) == 0) return i;
    return -1;
}
''')


def main():
    keys = filter(None, open(sys.argv[-1]).read().splitlines())
    print(format_template(generate_code(keys)))


if __name__ == '__main__':
    main()
