#!/usr/bin/python3

import unittest

from ..pipeline import Pipeline
from ..source.whitenoise import WhiteNoiseSource
from . import null

class NullTest(unittest.TestCase):
    def testBasicRun(self):
        pipeline = Pipeline()

        source = WhiteNoiseSource()
        pipeline.add_node(source)

        node = null.NullSink()
        pipeline.add_node(node)
        node.inputs['in'].connect(source.outputs['out'])
        node.setup()
        try:
            node.start()
            node.consume(4096)
        finally:
            node.cleanup()


if __name__ == '__main__':
    unittest.main()
