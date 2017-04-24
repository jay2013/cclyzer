import blox.connect
import json
import pandas as pd
import sys

class JSONCollector(object):
    def __init__(self, analysis):
        self.analysis = analysis
        self.objects = {}

    def _read_facts(self, predicate, ncolumns):
        csvfile = self.analysis.facts_file(predicate)
        hdr = ['col_{}'.format(i) for i in range(ncolumns)]
        return pd.read_csv(csvfile, header=None, sep='\t', names=hdr)

    def canonpred(self, predicate):
        if predicate.startswith('di:'):
            return 'debuginfo_' + predicate[3:]
        return predicate

    def consume_predicate(self, predicate, argspec, **kwargs):
        """Feed a predicate to the collector.

        Args:
          predicate (str): the predicate to consume
          argspec (str): the argument specifier (see below)

        Regarding the argument specifier, it encodes the meaning of
        each argument of the predicate. For example, the argspec 'oip'
        states that there are three arguments:
        - The first one holds the id of the object (o) that owns this
          predicate
        - The second one is an integer index (i), implying that the
          predicate values should be accumulated in a list.
        - The third one is the actual value of the property (p).

        We define the following specifiers:
        - o : id of the owner object
        - s : same as o, but domain is a superset of objects. This is helpful
              when merging relations that belong to a supertype, to filter the
              objects so that only the relevant subtype is considered
        - i : index into the property list
        - p : value of the property
        - P : value of the property. Multiple values are allowed and
              will be accumulated into a list, without any specific
              order (except if index arg is also specified)
        - n : property value is a nested object that will be inlined directly
              into the given position
        """
        nargs = len(argspec)
        dataframe = self._read_facts(predicate, nargs)

        # Infer entity and property names
        entity, prop = (self.canonpred(predicate).split(':') + [None])[:2]

        # Process optional arguments to override default behavior
        entity = kwargs.pop('entity', entity)
        prop = kwargs.pop('property', prop)
        inlineby = kwargs.pop('inlineby', None)
        transform = kwargs.pop('transform', None)
        indexto = kwargs.pop('indexto', None)

        # Get objects under construction
        objects = self.objects.setdefault(entity, {})

        # Iterate over rows
        for index, row in dataframe.iterrows():
            if len(row) != nargs:
                print row
                print len(row)
                raise ValueError('invalid argument specifier')

            # Number of arguments processed so far
            nprocessed = 0

            # Find the object
            if 's' in argspec:
                objid = row[argspec.index('s')]
                if objid not in objects:
                    continue
                obj = objects[objid]
                nprocessed += 1
            else:
                objid = row[argspec.index('o')]
                obj = objects.setdefault(objid, dict())
                obj['id'] = objid
                nprocessed += 1

            multival = False

            # Find value of property
            for spec in 'pPnN':
                if spec in argspec:
                    val = row[argspec.index(spec)]
                    multival = spec.isupper() or multival
                    nprocessed += 1
                    break
            else:
                val = None

            # Transform value
            if transform is not None:
                val = transform(val)

            # Inlined objects
            if 'n' in argspec or 'N' in argspec:
                try:
                    val = self.objects[self.canonpred(inlineby)][val]
                except KeyError:
                    continue

            if not prop:
                continue

            # Handle indexed properties
            if 'i' in argspec:
                idx = int(row[argspec.index('i')])
                nprocessed += 1
                nindices = idx + 1

                # Create empty list
                if indexto is not None:
                    if isinstance(indexto, int):
                        nindices = i
                    elif callable(indexto):
                        nindices = indexto(obj)
                    else:
                        raise ValueError('invalid indexto argument')

                items = obj.setdefault(prop, [None] * nindices)
                assert idx < nindices

                # Grow list of values if necessary
                if idx >= len(items):
                    items.extend([None] * (nindices - len(items)))

                if multival:
                    items[idx] = (items[idx] or []).append(val)
                else:
                    items[idx] = val
            else:
                # Record property
                if multival:
                    obj.setdefault(prop, []).append(val)
                else:
                    obj[prop] = val or True

            # Sanity checks
            if nprocessed != nargs:
                raise ValueError('unknown argument specifier')
            if kwargs:
                raise ValueError('unprocessed keyword arguments: ' + kwargs.keys())
        return


    def run(self):
        self.consume_predicate('function', 'o')
        self.consume_predicate('function_decl', 'o',
                               entity='function', property='is_declaration')

        self.consume_predicate('function:type', 'op')
        self.consume_predicate('function:name', 'op')
        self.consume_predicate('function:signature', 'op')
        self.consume_predicate('function:alignment', 'op')
        self.consume_predicate('function:unnamed_addr', 'o')
        self.consume_predicate('function:calling_convention', 'op')
        self.consume_predicate('function:visibility', 'op')
        self.consume_predicate('function:linkage_type', 'op')
        self.consume_predicate('function:gc', 'op')
        self.consume_predicate('function:section', 'op')
        self.consume_predicate('function:param', 'oip')
        self.consume_predicate('function:attribute', 'oP')
        self.consume_predicate('function:return_attribute', 'oP')
        self.consume_predicate('function:param_attribute', 'oiP',
                               indexto=lambda obj: len(obj['params']))

        self.consume_predicate('di:file', 'o')
        self.consume_predicate('di:file:filename', 'op')
        self.consume_predicate('di:file:directory', 'op')

        self.consume_predicate('di:subprogram', 'o')
        self.consume_predicate('di:subprogram:is_definition', 'o')
        self.consume_predicate('di:subprogram:is_local_to_unit', 'o')
        self.consume_predicate('di:subprogram:is_optimized', 'o')
        self.consume_predicate('di:subprogram:name', 'op')
        self.consume_predicate('di:subprogram:linkage_name', 'op')
        self.consume_predicate('di:subprogram:line', 'op')
        self.consume_predicate('di:subprogram:flag', 'oP')
        self.consume_predicate('di:subprogram:file', 'on', inlineby='di:file')

        self.consume_predicate('di:subprogram:function', 'no', entity='function',
                               property='debuginfo', inlineby='di:subprogram')

        self.consume_predicate('di:location', 'o')
        self.consume_predicate('di:location:line', 'op')
        self.consume_predicate('di:location:column', 'op')
        # TODO fix, may fail because of local scopes that are not subprograms
        self.consume_predicate('di:location:scope', 'on', inlineby='di:subprogram')

        self.consume_predicate('call_instruction', 'o')
        self.consume_predicate('call_instruction:calling_convention', 'op')
        self.consume_predicate('call_instruction:return_attribute', 'oP')
        self.consume_predicate('call_instruction:fn_attribute', 'oP')
        # self.consume_predicate('call_instruction:param_attribute', 'oiP')
        # self.consume_predicate('call_instruction:signature', 'op')
        # self.consume_predicate('call_instruction:return_type', 'op')
        self.consume_predicate('instruction:location', 'sn', inlineby='di:location',
                               entity='call_instruction', property='location')

        for key, value  in self.objects.iteritems():
            print 'Printing', key
            print

            items = list(value.itervalues())
            print json.dumps(items, indent=4, separators=(',', ': '))
            print