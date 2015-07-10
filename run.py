import re
import tempfile
import os.path
import random
import stat


class PythonExtractor(object):

    name = 'Python'

    def __init__(self, target = ''):
        self.re_setup = re.compile('^#setup: (.*)$')
        self.re_run = re.compile('^#run: (.*)$')
        self.options = ''
        targetsplit = target.split(':')
        self.executable = targetsplit[0]
        self.name = targetsplit[0]
        if len(targetsplit) >= 2:
            self.executable = targetsplit[1]
        if len(targetsplit) >= 3:
            self.options = targetsplit[2]

    def process_lines(self, filename, lines):
        content = []
        for line in lines:
            m = self.re_setup.match(line)
            if m:
                setup = m.group(1)
            m = self.re_run.match(line)
            if m:
                run = 'res = ' + m.group(1)
            content.append(line)
        try:
            return setup, run, content
        except NameError as n:
            raise RuntimeError('%s has invalid header' % filename)

    def __call__(self, filename):
        with open(filename) as fd:
            s, r, c = self.process_lines(filename, fd)
            return s, r, ''.join(c)

    def compile(self, filename):
        pass


class PypyExtractor(PythonExtractor):

    name = 'pypy'

class PypyvExtractor(PythonExtractor):

    name = 'pypyv'

class PythranExtractor(PythonExtractor):

    name = 'pythran'

    def compile(self, filename):
        import pythran
        pythran.compile_pythranfile(filename)


class ParakeetExtractor(PythonExtractor):

    name = 'parakeet'

    def __init__(self, target = ''):
        super(ParakeetExtractor, self).__init__(target)
        self.extra_import = 'import parakeet\n'
        self.decorator = '@parakeet.jit\n'

    def process_lines(self, filename, lines):
        s, r, c = super(ParakeetExtractor, self).process_lines(filename, lines)
        lines = [self.extra_import]
        for line in c:
            if line.startswith('def '):
                lines.append(self.decorator)
            lines.append(line)
        return s, r, lines


class NumbaExtractor(ParakeetExtractor):

    name = 'numba'

    def __init__(self, target = ''):
        super(NumbaExtractor, self).__init__(target)
        self.extra_import = 'import numba\n'
        self.decorator = '@numba.jit\n'


class HopeExtractor(ParakeetExtractor):

    name = 'hope'

    def __init__(self, target = ''):
        super(HopeExtractor, self).__init__(target)
        self.extra_import = 'import hope\n'
        self.decorator = '@hope.jit\n'


def run(filenames, extractors):
    location = tempfile.mkdtemp(prefix='rundir_', dir='.')
    shelllines = []
    for extractor in extractors:
        for filename in filenames:
            basename = os.path.basename(filename)
            function, _ = os.path.splitext(basename)
            tmpfilename = '_'.join([extractor.name, basename])
            tmpmodule, _ = os.path.splitext(tmpfilename)
            where = os.path.join(location, tmpfilename)
            try:
                setup, run, content = extractor(filename)
                with open(where, 'w') as fd:
                    fd.write(content)
                extractor.compile(where)
                path = "PYPYLOG=vec-opt-loop,jit-log-opt,jit-backend,jit:logfile PYTHONPATH=..:$PYTHONPATH"
                #path = "PYTHONPATH=..:$PYTHONPATH"
                shelllines.append('printf "{function} {extractor} in {where} " && '
                                  '{path} {executable} {options} -m benchit -r 5 -n 500 -v -p \'{function} {extractor}\' -s '
                                  '"{setup}; from {module} import {function} ; {run}" '
                                  '"{run}" || echo unsupported' \
                                     .format(setup=setup,
                                             module=tmpmodule,
                                             function=function,
                                             run=run,
                                             where=where,
                                             extractor=extractor.name,
                                             executable=extractor.executable,
                                             options=extractor.options,
                                             path=path)
                                )
            except:
                shelllines.append('echo "{function} {extractor} unsupported"'.format(function=function, extractor=extractor.name))

    random.shuffle(shelllines)
    shelllines = ['#!/bin/sh', 'export OMP_NUM_THREADS=1', 'cd `dirname $0`'] + shelllines

    shellscript = os.path.join(location, 'run.sh')
    with open(shellscript, 'w') as fd:
        fd.write('\n'.join(shelllines))
    os.chmod(shellscript, stat.S_IXUSR | stat.S_IRUSR)
    return shellscript

if __name__ == '__main__':
    import glob
    import argparse
    import sys
    parser = argparse.ArgumentParser(prog='numpy-benchmarks',
                                     description='run synthetic numpy benchmarks',
                                     epilog="It's a megablast!")
    parser.add_argument('benchmarks', nargs='*',
                        help='benchmark to run, default is benchmarks/*',
                        default=glob.glob('benchmarks/*.py'))
    default_targets=['python', 'pythran', 'parakeet', 'numba', 'pypy', 'pypyv', 'hope']
    parser.add_argument('-t', action='append', dest='targets', metavar='TARGET',
                        help='target compilers to use, default is %s' % ', '.join(default_targets))
    args = parser.parse_args(sys.argv[1:])

    if args.targets is None:
        args.targets = default_targets

    # -t <target>[:<executable>][:<options>]
    # -t 'pypy:/home/.../pypy:--jit vectorize=1'
    conv = lambda t: globals()[t.split(':')[0].capitalize() + 'Extractor']
    args.targets = [conv(t)(t) for t in args.targets]

    script = run(args.benchmarks, args.targets)
    os.execl(script, script)
