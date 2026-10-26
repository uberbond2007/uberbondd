"""Offline adversarial distillation fixtures. No provider calls."""
import hashlib
import importlib.util
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path

_spec=importlib.util.spec_from_file_location('distill_v11',Path(__file__).with_name('distill_v11.py'))
d=importlib.util.module_from_spec(_spec);_spec.loader.exec_module(d)

TRIGGERS=['source_changed','new_input','new_task_class','novelty','high_risk','failed_check','missing_evidence']

def rec(root):
    p=[]
    for n,v in [('source','Original trusted source'),('input','Synthetic task input'),('output','Accepted synthetic result')]:
        f=root/(n+'.txt');f.write_text(v)
        p.append({'path':f.name,'sha256':hashlib.sha256(f.read_bytes()).hexdigest()})
    recipe={'id':'lesson_001','task_class':'synthetic_reuse','teacher_model':'opus','source':p[0],
       'input':p[1],'output':p[2],'acceptance_checks':['fixture_exact','regression'], 'escalation_triggers':TRIGGERS}
    return recipe

def case(r):
    return {'task_class':r['task_class'],'risk':'low','novel':False,'source':r['source'],'input':r['input'],
         'output':r['output'],'checks':{'fixture_exact':True,'regression':True},'independent_acceptance':True}

def row(tid, b=8.0, v=1.5, score=1.0):
    return {'task_id':tid,'heldout':True,'same_task':True,
      'opus':{'calls':[{'model':'opus','usage':b,'purpose':'generation'}],'accepted':True,'quality':1.0,
              'critical_failures':0,'evaluator':'independent','producer':'teacher'},
      'distilled':{'calls':[{'model':'haiku','usage':v,'purpose':'generation'}],'accepted':True,'quality':score,
                   'critical_failures':0,'evaluator':'independent','producer':'student'}}

class V11Tests(unittest.TestCase):
 def setUp(self):
    self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
    self.raw=rec(self.root);self.compiled=d.compile_recipe(self.raw);self.case=case(self.raw)
 def tearDown(self):self.tmp.cleanup()
 def test_exact_hash_candidate_not_quality_proof(self):
    x=d.reuse_gate(self.compiled,self.case,self.root)
    self.assertEqual(x['state'],'EXACT_REUSE_CANDIDATE');self.assertFalse(x['quality_equivalence_verified']);self.assertFalse(x['allow_live_model_call'])
 def test_input_mutation_blocks(self):
    (self.root/'input.txt').write_text('Modified')
    self.assertIn('INPUT_HASH_MISMATCH',d.reuse_gate(self.compiled,self.case,self.root)['reasons'])
 def test_source_mutation_blocks(self):
    (self.root/'source.txt').write_text('Modified')
    self.assertIn('SOURCE_HASH_MISMATCH',d.reuse_gate(self.compiled,self.case,self.root)['reasons'])
 def test_output_mutation_blocks(self):
    (self.root/'output.txt').write_text('Modified')
    self.assertIn('OUTPUT_HASH_MISMATCH',d.reuse_gate(self.compiled,self.case,self.root)['reasons'])
 def test_different_input_hash_blocks(self):
    x=deepcopy(self.case);x['input']=dict(x['input'],sha256='1'*64)
    self.assertIn('INPUT_CHANGED',d.reuse_gate(self.compiled,x,self.root)['reasons'])
 def test_novel_risk(self):
    x=deepcopy(self.case);x['novel']=True;x['risk']='critical'
    self.assertEqual(d.reuse_gate(self.compiled,x,self.root)['reasons'],['HIGH_RISK','NOVEL_WORK'])
 def test_checks_failure(self):
    x=deepcopy(self.case);x['checks']['regression']=False
    self.assertIn('FAILED_CHECK',d.reuse_gate(self.compiled,x,self.root)['reasons'])
 def test_checks_missing(self):
    x=deepcopy(self.case);x['checks'].pop('regression')
    self.assertIn('MISSING_OR_INVALID_CHECKS',d.reuse_gate(self.compiled,x,self.root)['reasons'])
 def test_no_acceptance(self):
    x=deepcopy(self.case);x['independent_acceptance']=False
    self.assertIn('NO_INDEPENDENT_ACCEPTANCE',d.reuse_gate(self.compiled,x,self.root)['reasons'])
 def test_tampered_recipe(self):
    x=deepcopy(self.compiled);x['recipe']['task_class']='altered'
    self.assertEqual(d.reuse_gate(x,self.case,self.root)['state'],'HOLD_TAMPERED_RECIPE')
 def test_symlink_denied(self):
    (self.root/'output.txt').unlink();(self.root/'output.txt').symlink_to(self.root/'input.txt')
    with self.assertRaises(ValueError):d.reuse_gate(self.compiled,self.case,self.root)
 def test_missing_required_trigger(self):
    r=deepcopy(self.raw);r['escalation_triggers'].remove('high_risk')
    with self.assertRaises(ValueError):d.compile_recipe(r)
 def test_not_opus_teacher(self):
    r=deepcopy(self.raw);r['teacher_model']='haiku'
    with self.assertRaises(ValueError):d.compile_recipe(r)
 def test_duplicate_checks(self):
    r=deepcopy(self.raw);r['acceptance_checks']*=2
    with self.assertRaises(ValueError):d.compile_recipe(r)
 def test_benchmark_matched(self):
    p={'units':'api_equivalent_usd','quality_floor':0.95,'quality_tolerance':0.01,'tasks':[row('a'),row('b')]}
    x=d.benchmark(p);self.assertEqual(x['state'],'REVIEW_CANDIDATE');self.assertAlmostEqual(x['modeled_savings_percent'],81.25)
    self.assertFalse(x['opus_equivalence_proven'])
 def test_benchmark_includes_retries(self):
    r=row('a');r['distilled']['calls']+=[{'model':'sonnet','usage':3,'purpose':'retry'},{'model':'opus','usage':6,'purpose':'recovery'}]
    x=d.benchmark({'units':'api_equivalent_usd','quality_floor':0.9,'quality_tolerance':0.1,'tasks':[r]})
    self.assertLess(x['modeled_savings_percent'],0)
 def test_quality_regression_blocks(self):
    x=d.benchmark({'units':'token_proxy','quality_floor':0.95,'quality_tolerance':0.01,'tasks':[row('x',score=.94)]})
    self.assertEqual(x['state'],'HOLD_QUALITY_OR_PROVENANCE');self.assertEqual(x['failed_quality_task_ids'],['x'])
 def test_critical_failure_blocks(self):
    r=row('x');r['distilled']['critical_failures']=1
    x=d.benchmark({'units':'token_proxy','quality_floor':.9,'quality_tolerance':.1,'tasks':[r]})
    self.assertEqual(x['state'],'HOLD_QUALITY_OR_PROVENANCE')
 def test_self_review_blocks(self):
    r=row('x');r['distilled']['evaluator']='student'
    x=d.benchmark({'units':'token_proxy','quality_floor':.9,'quality_tolerance':.1,'tasks':[r]})
    self.assertEqual(x['state'],'HOLD_QUALITY_OR_PROVENANCE');self.assertTrue(x['incomplete_evaluation'])
 def test_duplicate_task_rejected(self):
    with self.assertRaises(ValueError):d.benchmark({'units':'token_proxy','quality_floor':.9,'quality_tolerance':.1,'tasks':[row('a'),row('a')]})
 def test_nonheldout_rejected(self):
    r=row('x');r['heldout']=False
    with self.assertRaises(ValueError):d.benchmark({'units':'token_proxy','quality_floor':.9,'quality_tolerance':.1,'tasks':[r]})
 def test_nan_rejected(self):
    r=row('x');r['distilled']['calls'][0]['usage']=float('nan')
    with self.assertRaises(ValueError):d.benchmark({'units':'token_proxy','quality_floor':.9,'quality_tolerance':.1,'tasks':[r]})
 def test_bad_model_rejected(self):
    r=row('x');r['distilled']['calls'][0]['model']='secret_paid_provider'
    with self.assertRaises(ValueError):d.benchmark({'units':'token_proxy','quality_floor':.9,'quality_tolerance':.1,'tasks':[r]})

if __name__=='__main__':unittest.main()
