"""Validation errors must distinguish hostile output from server outages."""
import contextlib
import io
import json
from pathlib import Path
import subprocess
import sys
import unittest
from unittest import mock

sys.path.insert(0,str(Path(__file__).parent))
import test_science
import boinc_validate
from validation_errors import ScientificValidationError, ValidationInfrastructureError


class ValidatorOutages(unittest.TestCase):
    setUp=test_science.Science.setUp
    tearDown=test_science.Science.tearDown
    command=test_science.Science.command
    run_app=test_science.Science.run_app
    validate=test_science.Science.validate

    def valid_output(self):
        result=self.run_app()
        self.assertEqual(result.returncode,0,result.stderr)

    def test_unavailable_or_broken_oracle_is_infrastructure(self):
        self.valid_output()
        bad=self.d/'bad-oracle'
        bad.write_text('#!/bin/sh\nprintf "not JSON"\n')
        bad.chmod(0o755)
        for oracle in (self.d/'missing-oracle',Path('/bin/false'),bad):
            with self.subTest(oracle=str(oracle)):
                with self.assertRaises(ValidationInfrastructureError):
                    boinc_validate.validate(self.d/'manifest.json',self.d/'result.json',oracle,self.hash,'A')

    def test_oracle_timeout_is_infrastructure(self):
        self.valid_output()
        with mock.patch('validate_result.subprocess.run',side_effect=subprocess.TimeoutExpired('oracle',120)):
            with self.assertRaises(ValidationInfrastructureError):self.validate()

    def test_untrusted_shapes_are_scientific_rejections(self):
        self.valid_output()
        original=json.loads((self.d/'result.json').read_text())
        for output in ([],None,dict(original,receipts=[None]*3)):
            with self.subTest(output=type(output).__name__):
                (self.d/'result.json').write_text(json.dumps(output))
                with self.assertRaises(ScientificValidationError):self.validate()

    def test_corrupt_trusted_manifest_is_not_worker_failure(self):
        self.valid_output()
        (self.d/'manifest.json').write_text('{')
        with self.assertRaises(ValueError) as exc:self.validate()
        self.assertNotIsInstance(exc.exception,ScientificValidationError)

    def test_database_command_failure_defers_without_leaking_arguments(self):
        cfg=dict(mysql_command=['mysql','--password=TEST_SECRET_DO_NOT_LOG'],database='fifth42')
        failure=subprocess.CalledProcessError(1,cfg['mysql_command'])
        with mock.patch('boinc_validate.subprocess.check_output',side_effect=failure):
            with self.assertRaises(ValidationInfrastructureError) as exc:boinc_validate.resolve(cfg,'1')
        self.assertNotIn('TEST_SECRET_DO_NOT_LOG',str(exc.exception))

    def test_exit_codes_preserve_scientific_vs_server_failures(self):
        cases=[(None,0),(ScientificValidationError('bad count'),1),
               (ValidationInfrastructureError('DB unavailable'),3),
               (FileNotFoundError('server config'),3),(ValueError('trusted config'),3),
               (RuntimeError('unexpected bug'),3)]
        for failure,expected in cases:
            with self.subTest(failure=type(failure).__name__):
                stderr=io.StringIO()
                with mock.patch('boinc_validate.main',side_effect=failure),contextlib.redirect_stderr(stderr):
                    self.assertEqual(boinc_validate.cli(['hook','1','output']),expected)
                if expected==3:self.assertIn('Validation deferred',stderr.getvalue())


if __name__=='__main__':unittest.main()
