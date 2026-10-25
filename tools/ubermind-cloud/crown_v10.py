#!/usr/bin/env python3
"""Transcendent V10: conservative *offline* mission and billing intelligence.
No subprocess, network, provider login, model calls or external side effects.
"""
from __future__ import annotations
import argparse, hashlib, json, math, os, re, sys
from pathlib import Path

RISK={'low','medium','high','critical'}
ALLOWED_ROLES={'native','haiku_scout_low','haiku_research_medium','sonnet_builder_medium','sonnet_falsifier_high','opus_solo_high','opus_frontier_xhigh'}
ALLOW_ACTION={'read','compute','test_local','edit_sandbox'}
EXTERNAL_ACTION={'message','pay','trade','deploy','file','probe_external','access_secret','collect_private_data'}
SOURCE_HEX=re.compile(r'^[0-9a-f]{64}$')
SENSITIVE=['ANTHROPIC_API_KEY','ANTHROPIC_AUTH_TOKEN','ANTHROPIC_FOUNDRY_API_KEY','AWS_ACCESS_KEY_ID','GOOGLE_APPLICATION_CREDENTIALS','CLAUDE_CODE_USE_BEDROCK','CLAUDE_CODE_USE_VERTEX','CLAUDE_CODE_USE_FOUNDRY','ANTHROPIC_BASE_URL']

def canonical(obj):return json.dumps(obj,sort_keys=True,ensure_ascii=False,separators=(',',':'),allow_nan=False)
def digest(obj):return hashlib.sha256(canonical(obj).encode()).hexdigest()
def filehash(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def _integer(n):return type(n)==int and 0<=n<=2**53

# Names a documented Claude Code cloud host may itself set while it manages provider routing.
# Tolerated ONLY under recognized host markers; every other SENSITIVE name always holds.
HOST_ROUTING_NAMES=frozenset({'ANTHROPIC_BASE_URL','AWS_ACCESS_KEY_ID'})

def _runtime_class(env):
    # Documented: CLAUDE_CODE_REMOTE='true' in a cloud session; CLAUDE_CODE_PROVIDER_MANAGED_BY_HOST is set by
    # host platforms that manage provider routing; CLAUDECODE='1' in subprocesses Claude Code spawns.
    # None of these certifies subscription auth, and inherited markers cannot prove which process launched a CLI.
    if env.get('CLAUDE_CODE_REMOTE')=='true' and env.get('CLAUDE_CODE_PROVIDER_MANAGED_BY_HOST'):return 'HOST_MANAGED_REMOTE'
    if env.get('CLAUDECODE')=='1':return 'LOCAL_CLI'
    return 'UNKNOWN'

def preflight(env=None, model_settings=None):
    env=dict(os.environ if env is None else env)
    present=sorted(k for k in SENSITIVE if env.get(k))
    override=bool(env.get('CLAUDE_CODE_SUBAGENT_MODEL') or env.get('CLAUDE_CODE_SUBAGENT_MODEL_FORCE'))
    runtime=_runtime_class(env)
    tolerated=sorted(k for k in present if k in HOST_ROUTING_NAMES) if runtime=='HOST_MANAGED_REMOTE' else []
    holding=[k for k in present if k not in tolerated]
    if holding:state='HOLD_BILLING_ROUTE'
    elif runtime=='HOST_MANAGED_REMOTE':state='HOST_MANAGED_ROUTE_SUBSCRIPTION_UNVERIFIED'
    elif runtime=='LOCAL_CLI':state='SUBSCRIPTION_IDENTITY_UNVERIFIED'
    else:state='HOLD_RUNTIME_EVIDENCE_MISSING'
    details={'state':state,
      'runtime_class':runtime,
      'credential_or_provider_override_names':holding,
      'host_managed_routing_names':tolerated,
      'model_override':override,
      'authenticated_plan_verified':False,
      'api_charge_absence_verified':False,
      'allow_live_model_call':False,
      'next_step':'In Claude Code run /status, /model, /usage; verify Claude subscription login and disabled extra credits. Never paste secrets into reports.'}
    if override:details['state']='HOLD_MODEL_OVERRIDE'
    if model_settings is not None:
        if type(model_settings)!=dict:raise ValueError('settings must be object')
        details['configured_model']=model_settings.get('model','not_set')
    return details

def _graph(tasks):
    if type(tasks)!=list or not 1<=len(tasks)<=100:raise ValueError('bounded task list required')
    ids={}
    for task in tasks:
        if type(task)!=dict or set(task)!={'id','depends','action','description','risk','source_sha256','acceptance'}:raise ValueError('exact task schema required')
        tid=task['id']
        if type(tid)!=str or not re.fullmatch('[a-z0-9][a-z0-9_-]{0,63}',tid) or tid in ids:raise ValueError('bad/duplicate id')
        if type(task['depends'])!=list or len(set(task['depends']))!=len(task['depends']):raise ValueError('duplicate dependencies')
        if any(type(x)!=str for x in task['depends']):raise ValueError('invalid dependencies')
        if task['action'] not in ALLOW_ACTION|EXTERNAL_ACTION:raise ValueError('unknown action')
        if task['risk'] not in RISK:raise ValueError('unknown risk')
        if type(task['description'])!=str or not 1<=len(task['description'])<=300:raise ValueError('description')
        if type(task['acceptance'])!=str or not 1<=len(task['acceptance'])<=500:raise ValueError('acceptance criterion')
        if type(task['source_sha256'])!=str or not SOURCE_HEX.fullmatch(task['source_sha256']):raise ValueError('source hash')
        ids[tid]=task
    for t in tasks:
        if t['id'] in t['depends'] or any(d not in ids for d in t['depends']):raise ValueError('unknown/cyclic dependency')
    order=[];temp=set();done=set()
    def visit(tid):
        if tid in temp:raise ValueError('cycle')
        if tid in done:return
        temp.add(tid)
        for d in ids[tid]['depends']:visit(d)
        temp.remove(tid);done.add(tid);order.append(tid)
    for tid in sorted(ids):visit(tid)
    return ids,order

def task_contract(payload):
    if type(payload)!=dict or set(payload)!={'mission_id','tasks','authorized_actions','objective','source_manifest_sha256','claude_subscription_only'}:raise ValueError('mission schema')
    if type(payload['mission_id'])!=str or not re.fullmatch('[A-Za-z0-9_-]{1,80}',payload['mission_id']):raise ValueError('mission id')
    if type(payload['objective'])!=str or not 1<=len(payload['objective'])<=1000:raise ValueError('objective')
    if not SOURCE_HEX.fullmatch(payload['source_manifest_sha256']):raise ValueError('manifest hash')
    if payload['claude_subscription_only'] is not True:raise ValueError('subscription route required')
    if type(payload['authorized_actions'])!=list or any(x not in ALLOW_ACTION for x in payload['authorized_actions']):raise ValueError('unapproved external authority cannot be granted by a JSON manifest')
    ids,order=_graph(payload['tasks'])
    blocked={};safe=[]
    for tid in order:
        task=ids[tid]
        reason=('REQUIRES_OWNER_PERMISSION' if task['action'] not in ALLOW_ACTION or task['action'] not in payload['authorized_actions'] else None)
        if any(d in blocked for d in task['depends']):reason='BLOCKED_DEPENDENCY'
        if reason:blocked[tid]=reason
        else:safe.append(tid)
    return {'mission_id':payload['mission_id'],'mission_sha256':digest(payload),'ordered_tasks':order,'eligible':safe,'blocked':blocked,
      'claude_calls':0,'permission_boundary_enforced':True,'status':'OFFLINE_CONTRACT_ONLY'}

def route_auction(payload):
    if type(payload)!=dict or set(payload)!={'mission_sha256','task_id','risk','quality_floor','candidates','subscription_verified','source_verified'}:raise ValueError('auction schema')
    if not SOURCE_HEX.fullmatch(payload['mission_sha256']):raise ValueError('mission SHA')
    if payload['risk'] not in RISK or type(payload['quality_floor']) not in (float,int) or not 0<=payload['quality_floor']<=1:raise ValueError('quality parameters')
    if type(payload['candidates'])!=list or not payload['candidates']:raise ValueError('candidates')
    rankings=[]
    for c in payload['candidates']:
        required={'role','quality_lower','usage_upper','rework_upper','switch_tax','tail_loss','evidence_verified','independent_acceptance'}
        if type(c)!=dict or set(c)!=required or c['role'] not in ALLOWED_ROLES:raise ValueError('candidate schema')
        for k in ('quality_lower','usage_upper','rework_upper','switch_tax','tail_loss'):
            v=c[k]
            if type(v) not in (int,float) or not math.isfinite(v) or v<0:raise ValueError('numeric bounds')
        if c['quality_lower']>1:raise ValueError('quality bound')
        if type(c['evidence_verified'])!=bool or type(c['independent_acceptance'])!=bool:raise ValueError('evidence fields')
        if c['role']!='native' and payload['subscription_verified'] is not True:continue
        if not c['evidence_verified'] or not c['independent_acceptance'] or c['quality_lower']<payload['quality_floor']:continue
        if payload['source_verified'] is not True:continue
        if payload['risk'] in {'high','critical'} and c['tail_loss']>0:continue
        worst=c['usage_upper']+c['rework_upper']+c['switch_tax']
        rankings.append({'role':c['role'],'worst_case_usage_proxy':round(worst,5),'tail_loss':c['tail_loss'],'quality_lower':c['quality_lower']})
    rankings.sort(key=lambda x:(x['worst_case_usage_proxy'],x['tail_loss'],-x['quality_lower'],x['role']))
    return {'state':'NOMINATE_FOR_REVIEW' if rankings else 'HOLD_UNPROVEN','recommended':rankings[0] if rankings else None,
      'ranked':rankings,'automatic_dispatch':False,'cost_units':'USER-SUPPLIED NORMALIZED PROXY, NOT CLAUDE BAR','source_verified':payload['source_verified'] is True}

KEYWORDS={
 'eq':('stakeholder','trust','empathy','consent','culture','reputation','batna','relationship'),
 'game_theory':('player','payoff','outside_option','repeated_game','cooperation','equilibrium'),
 'power':('counterparty','incentive','legitimacy','reputation','negotiation','institution'),
 'creativity':('novel_option','analogy_limit','counterfactual','feasibility','experiment'),
 'falsification':('strongest_counterexample','test','reversibility','tail_risk'),
}
def cognitive_gate(report,requested=None,source_root=None):
    if type(report)!=dict or type(report.get('mission_sha256'))!=str or not SOURCE_HEX.fullmatch(report['mission_sha256']):raise ValueError('report missing source')
    requested=list(KEYWORDS) if requested is None else requested
    if type(requested)!=list or len(set(requested))!=len(requested) or any(k not in KEYWORDS for k in requested):raise ValueError('invalid dimensions')
    present=report.get('dimensions')
    if type(present)!=dict:raise ValueError('dimension map')
    misses={}
    for k in requested:
        m=present.get(k)
        missing=[n for n in KEYWORDS[k] if type(m)!=dict or type(m.get(n))!=str or len(m[n].strip())<5]
        if missing:misses[k]=missing
    if report.get('source_attestations') is None or type(report['source_attestations'])!=list or not report['source_attestations']:
        misses['sources']=['at least one exact source attestation required']
    else:
        for x in report['source_attestations']:
            if type(x)!=dict or set(x)!={'path','sha256','passage'} or not SOURCE_HEX.fullmatch(x['sha256']) or not x['path'] or not x['passage']:
                misses['sources']=['invalid source attestation'];break
    exact_local=False
    if source_root is not None and 'sources' not in misses:
        root=Path(source_root).resolve(strict=True)
        if not root.is_dir():raise ValueError('source root must be directory')
        for att in report['source_attestations']:
            rel=Path(att['path'])
            if rel.is_absolute() or '..' in rel.parts:raise ValueError('source traversal denied')
            target=root/rel
            resolved=target.resolve(strict=True)
            try:resolved.relative_to(root)
            except ValueError:raise ValueError('source escaped trusted root')
            if target.is_symlink() or not resolved.is_file() or resolved.stat().st_size>3_000_000:
                raise ValueError('unsafe source path')
            if filehash(resolved)!=att['sha256']:raise ValueError('source hash changed')
            if att['passage'] not in resolved.read_text(encoding='utf-8'):
                raise ValueError('source passage not present')
        exact_local=True
    return {'state':'READY_FOR_INDEPENDENT_REVIEW' if not misses else 'HOLD_UNPROVEN_COGNITION',
      'missing':misses,'local_source_text_exact':exact_local,'source_authenticity_verified':False,
      'automatic_promotion':False,
      'note':'Local source hashes/passages, completed fields and self-reports cannot independently prove truth, EQ, model quality or real effects.'}

def transcript_usage(filepath,max_bytes=10_000_000):
    p=Path(filepath)
    if not p.is_file() or p.is_symlink() or p.stat().st_size>max_bytes:raise ValueError('unsafe transcript')
    totals={'input_tokens':0,'output_tokens':0,'cache_read_input_tokens':0,'cache_creation_input_tokens':0};count=0;seen={};models={}
    with p.open('rb') as f:
        for raw in f:
            if len(raw)>250000:raise ValueError('line too large')
            try:row=json.loads(raw)
            except Exception:continue
            if type(row)!=dict or row.get('type')!='assistant':continue
            msg=row.get('message',{})
            if type(msg)!=dict:continue
            usage=msg.get('usage',{})
            if type(usage)!=dict:continue
            rid=msg.get('id')
            # Event stream often repeats same message id with evolving usage; keep highest output in each final assistant message.
            if type(rid)!=str:continue
            model=msg.get('model','unknown');model=model if type(model)==str else 'unknown'
            vals={k:usage.get(k,0) for k in totals}
            if not all(_integer(v) for v in vals.values()):raise ValueError('invalid usage number')
            prior=seen.get(rid)
            if prior and sum(vals.values())<=sum(prior['usage'].values()):continue
            seen[rid]={'usage':vals,'model':model}
    for data in seen.values():
        count+=1;models[data['model']]=models.get(data['model'],0)+1
        for k,v in data['usage'].items():totals[k]+=v
    return {'messages':count,'models_message_counts':models,'tokens':totals,'transcript_sha256':filehash(p),
      'estimated_usage_only':True,'verified_subscription_meter_savings':False,
      'note':'Local Claude Code transcript counters are not authenticated subscription allowance or billing receipts; conversation text is not stored.'}

def main():
    a=argparse.ArgumentParser();s=a.add_subparsers(dest='action',required=True)
    s.add_parser('preflight')
    for cmd in ('plan','auction','cognitive','transcript'):
        p=s.add_parser(cmd);p.add_argument('file')
    o=a.parse_args()
    try:
        if o.action=='preflight':value=preflight()
        elif o.action=='transcript':value=transcript_usage(o.file)
        else:
            p=Path(o.file)
            if not p.is_file() or p.stat().st_size>2_000_000:raise ValueError('unsafe input')
            payload=json.loads(p.read_text())
            value={'plan':task_contract,'auction':route_auction,'cognitive':cognitive_gate}[o.action](payload)
        print(json.dumps(value,indent=2,ensure_ascii=False))
    except (ValueError,TypeError,KeyError,FileNotFoundError) as e:
        print(json.dumps({'state':'REJECTED','reason':str(e)}));raise SystemExit(2)
if __name__=='__main__':main()
