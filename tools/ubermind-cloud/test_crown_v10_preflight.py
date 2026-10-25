"""Focused regression tests for crown_v10.preflight runtime/billing-route classification."""
import importlib.util, json, unittest
from pathlib import Path

_spec=importlib.util.spec_from_file_location('crown_v10',Path(__file__).with_name('crown_v10.py'))
crown=importlib.util.module_from_spec(_spec);_spec.loader.exec_module(crown)

SECRET='sk-ant-SHOULD-NEVER-APPEAR-0123456789'
HOST={'CLAUDE_CODE_REMOTE':'true','CLAUDE_CODE_PROVIDER_MANAGED_BY_HOST':'host-marker',
      'CLAUDECODE':'1','ANTHROPIC_BASE_URL':'https://proxy.invalid','AWS_ACCESS_KEY_ID':'AKIA-FAKE-VALUE'}

class PreflightTest(unittest.TestCase):
    def assertNeverCertified(self,r):
        self.assertFalse(r['authenticated_plan_verified']);self.assertFalse(r['api_charge_absence_verified'])
        self.assertFalse(r['allow_live_model_call'])
        out=json.dumps(r)
        for v in (SECRET,'https://proxy.invalid','AKIA-FAKE-VALUE','host-marker'):self.assertNotIn(v,out)

    def test_hosted_cloud_routing_names_do_not_false_alarm(self):
        r=crown.preflight(dict(HOST))
        self.assertEqual(r['state'],'HOST_MANAGED_ROUTE_SUBSCRIPTION_UNVERIFIED')
        self.assertEqual(r['runtime_class'],'HOST_MANAGED_REMOTE')
        self.assertEqual(r['credential_or_provider_override_names'],[])
        self.assertEqual(r['host_managed_routing_names'],['ANTHROPIC_BASE_URL','AWS_ACCESS_KEY_ID'])
        self.assertNeverCertified(r)

    def test_explicit_api_key_holds_even_in_remote_host(self):
        r=crown.preflight(dict(HOST,ANTHROPIC_API_KEY=SECRET))
        self.assertEqual(r['state'],'HOLD_BILLING_ROUTE')
        self.assertEqual(r['credential_or_provider_override_names'],['ANTHROPIC_API_KEY'])
        self.assertNeverCertified(r)

    def test_ordinary_local_cli_routing_names_still_hold(self):
        clean=crown.preflight({'CLAUDECODE':'1'})
        self.assertEqual(clean['state'],'SUBSCRIPTION_IDENTITY_UNVERIFIED')
        self.assertEqual(clean['runtime_class'],'LOCAL_CLI');self.assertNeverCertified(clean)
        routed=crown.preflight({'CLAUDECODE':'1','ANTHROPIC_BASE_URL':'https://proxy.invalid'})
        self.assertEqual(routed['state'],'HOLD_BILLING_ROUTE')
        self.assertEqual(routed['host_managed_routing_names'],[])
        # A lone or non-'true' remote marker is not recognized host management.
        partial=crown.preflight({'CLAUDECODE':'1','CLAUDE_CODE_REMOTE':'1','CLAUDE_CODE_PROVIDER_MANAGED_BY_HOST':'x','AWS_ACCESS_KEY_ID':'k'})
        self.assertEqual(partial['state'],'HOLD_BILLING_ROUTE');self.assertEqual(partial['runtime_class'],'LOCAL_CLI')

    def test_missing_evidence_fails_closed(self):
        r=crown.preflight({})
        self.assertEqual(r['state'],'HOLD_RUNTIME_EVIDENCE_MISSING')
        self.assertEqual(r['runtime_class'],'UNKNOWN');self.assertNeverCertified(r)

if __name__=='__main__':unittest.main()
