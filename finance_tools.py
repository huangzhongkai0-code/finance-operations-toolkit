"""Local finance operations toolkit. Python 3.10+, standard library only."""
import csv
import json
from collections import Counter, defaultdict
from datetime import date
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path

D = Decimal
CENT = D('0.01')


def number(value):
    try:
        result = D(str(value).strip())
    except InvalidOperation as exc:
        raise ValueError(f'Invalid amount: {value!r}') from exc
    if not result.is_finite():
        raise ValueError('Amount must be finite')
    return result


def money(value):
    value = number(value)
    if value != value.quantize(CENT):
        raise ValueError(f'Amount must have at most 2 decimal places: {value}')
    return value


def day(value):
    parsed = date.fromisoformat(value)
    if parsed.isoformat() != value:
        raise ValueError('Dates must use YYYY-MM-DD')
    return parsed


def read_csv(path, required, mapping=None):
    """mapping maps canonical field -> source header; trace physical start row."""
    mapping = mapping or {}
    with Path(path).open(encoding='utf-8-sig', newline='') as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames or len(reader.fieldnames) != len(set(reader.fieldnames)):
            raise ValueError(f'{path}: empty or duplicate headers')
        missing = [k for k in required if mapping.get(k, k) not in reader.fieldnames]
        if missing:
            raise ValueError(f'{path}: missing fields {missing}')
        rows = []
        previous = reader.line_num
        for raw in reader:
            row_number = previous + 1
            previous = reader.line_num
            if None in raw or any(v is None for v in raw.values()):
                raise ValueError(f'{path}:{row_number}: wrong column count')
            row = {k: raw[mapping.get(k, k)].strip() for k in required}
            row['_source'] = Path(path).name
            row['_row'] = row_number
            rows.append(row)
        return rows


def safe_cell(value):
    # CSV outputs may be opened in Excel: neutralize text formulas, retain numbers.
    if isinstance(value, str) and value.lstrip().startswith(('=', '+', '-', '@', '\t', '\r')):
        return "'" + value
    return value


def write_csv(path, rows, fields):
    with Path(path).open('w', encoding='utf-8-sig', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction='ignore')
        writer.writeheader()
        for row in rows:
            writer.writerow({k: safe_cell(row.get(k, '')) for k in fields})


def issue(row, code, detail):
    return {'source': row['_source'], 'row': row['_row'], 'code': code, 'detail': detail}


def close_checks(rows, balances, config):
    issues, totals, fingerprints, voucher_days = [], defaultdict(lambda: [D(0), D(0)]), {}, defaultdict(set)
    start, end = day(config['period_start']), day(config['period_end'])
    tolerance = money(config['tolerance'])
    valid_accounts = set(config.get('accounts', []))
    valid_rows = []
    for row in rows:
        try:
            for field in ('voucher_id', 'date', 'account', 'currency'):
                if not row[field]:
                    raise ValueError(f'Empty {field}')
            dt, debit, credit = day(row['date']), money(row['debit']), money(row['credit'])
            if debit < 0 or credit < 0 or (debit and credit) or not (debit or credit):
                raise ValueError('Use one positive debit or credit per line')
        except ValueError as exc:
            issues.append(issue(row, 'INVALID_LINE', str(exc)))
            continue
        valid_rows.append(row)
        key = (row['voucher_id'], row['currency'])
        totals[key][0] += debit
        totals[key][1] += credit
        voucher_days[key].add(dt)
        if not start <= dt <= end:
            issues.append(issue(row, 'OUT_OF_PERIOD', str(dt)))
        if valid_accounts and row['account'] not in valid_accounts:
            issues.append(issue(row, 'UNKNOWN_ACCOUNT', row['account']))
        signature = tuple(row[k] for k in ('voucher_id', 'date', 'account', 'currency', 'debit', 'credit', 'description'))
        if signature in fingerprints:
            issues.append(issue(row, 'POSSIBLE_DUPLICATE', f"Same line as row {fingerprints[signature]}; review required"))
        fingerprints[signature] = row['_row']
    voucher_results = []
    for (voucher, currency), (debit, credit) in sorted(totals.items()):
        voucher_results.append({'voucher_id': voucher, 'currency': currency, 'debit': debit, 'credit': credit,
                                'difference': debit-credit, 'status': 'BALANCED' if abs(debit-credit) <= tolerance else 'UNBALANCED'})
        if len(voucher_days[(voucher, currency)]) > 1:
            issues.append({'source': 'journal.csv', 'row': '', 'code': 'MULTIPLE_VOUCHER_DATES', 'detail': voucher})
    movements = defaultdict(lambda: D(0))
    for row in valid_rows:
        try:
            if start <= day(row['date']) <= end:
                movements[(row['account'], row['currency'])] += money(row['debit'])-money(row['credit'])
        except ValueError:
            pass
    balance_results, seen = [], set()
    for row in balances:
        try:
            key = (row['account'], row['currency'])
            if key in seen:
                raise ValueError('Duplicate account/currency balance')
            seen.add(key)
            opening, closing = money(row['opening']), money(row['closing'])
            expected = opening+movements[key]
            balance_results.append({'account': key[0], 'currency': key[1], 'opening': opening, 'movement': movements[key],
                                    'expected_closing': expected, 'reported_closing': closing, 'difference': closing-expected,
                                    'status': 'OK' if abs(closing-expected) <= tolerance else 'REVIEW'})
        except ValueError as exc:
            issues.append(issue(row, 'INVALID_BALANCE', str(exc)))
    for key in movements.keys()-seen:
        issues.append({'source': 'balances.csv', 'row': '', 'code': 'MISSING_BALANCE', 'detail': '/'.join(key)})
    return {'close_issues': issues, 'voucher_checks': voucher_results, 'balance_checks': balance_results}


def budget_analysis(budget, actual, config):
    totals = defaultdict(lambda: [D(0), D(0), []])
    for idx, rows in enumerate((budget, actual)):
        for row in rows:
            month = row['month']
            day(month+'-01')
            if month > config['period_end'][:7] or month < config['period_start'][:4]+'-01':
                continue
            for field in ('department', 'account', 'currency'):
                if not row[field]:
                    raise ValueError(f"{row['_source']}:{row['_row']}: empty {field}")
            department = config.get('department_mapping', {}).get(row['department'], row['department'])
            key = (month, department, row['account'], row['currency'])
            totals[key][idx] += money(row['amount'])
            totals[key][2].append(f"{row['_source']}:{row['_row']}")
    results = []
    for key, (planned, spent, refs) in sorted(totals.items()):
        delta = spent-planned
        percent = delta/abs(planned)*100 if planned else None
        results.append(dict(zip(('month', 'department', 'account', 'currency'), key)) | {
            'budget': planned, 'actual': spent, 'variance': delta, 'variance_pct': percent if percent is not None else '',
            'status': 'UNBUDGETED' if not planned and spent else 'OVER_BUDGET' if delta > 0 and percent is not None and percent > number(config['budget_alert_pct']) else 'WITHIN_THRESHOLD',
            'sources': '; '.join(refs)})
    ytd = defaultdict(lambda: [D(0), D(0)])
    for row in results:
        key = (row['department'], row['account'], row['currency'])
        ytd[key][0] += row['budget']; ytd[key][1] += row['actual']
    return {'budget_monthly': results, 'budget_ytd': [dict(zip(('department','account','currency'),k)) | {'budget':v[0],'actual':v[1],'variance':v[1]-v[0]} for k,v in sorted(ytd.items())]}


def reconcile(bank, ledger, config):
    tolerance, window = money(config['tolerance']), int(config['matching_days'])
    prepared = []
    for label, rows in (('bank', bank), ('ledger', ledger)):
        ids = [r['id'] for r in rows]
        if any(not x for x in ids) or len(ids) != len(set(ids)):
            raise ValueError(f'{label}: blank or duplicate transaction IDs')
        prepared.append([(r, day(r['date']), money(r['amount'])) for r in rows])
    left, right = prepared
    candidates = defaultdict(list); reverse = defaultdict(list)
    for i,(a,dt,amount) in enumerate(left):
        for j,(b,otherdt,other) in enumerate(right):
            if a['currency'] == b['currency'] and amount*other > 0 and abs(amount-other) <= tolerance and abs((dt-otherdt).days) <= window:
                # Non-empty references must agree; absent references remain suggestions.
                if a['reference'] and b['reference'] and a['reference'] != b['reference']:
                    continue
                candidates[i].append(j); reverse[j].append(i)
    result, used = [], set()
    for i,(a,_,amount) in enumerate(left):
        possible = candidates[i]
        j = possible[0] if len(possible)==1 else None
        mutual = j is not None and len(reverse[j])==1
        exact_reference = mutual and bool(a['reference']) and a['reference']==right[j][0]['reference']
        matched = bool(exact_reference)
        if matched: used.add(j)
        result.append({'bank_id':a['id'],'ledger_id':right[j][0]['id'] if matched else '', 'currency':a['currency'],
                       'bank_amount':amount,'status':'MATCHED' if matched else 'REVIEW' if possible else 'UNMATCHED',
                       'candidate_ids':';'.join(right[x][0]['id'] for x in possible), 'source':a['_source'],'row':a['_row']})
    return {'bank_reconciliation':result,'ledger_unmatched':[{'ledger_id':r['id'],'currency':r['currency'],'amount':v,'source':r['_source'],'row':r['_row']} for j,(r,_,v) in enumerate(right) if j not in used]}


def aging(invoices, receipts, config):
    asof=day(config['as_of']); by_id={}; paid=defaultdict(lambda:D(0)); exceptions=[]
    for row in invoices:
        if not row['invoice_id'] or row['invoice_id'] in by_id:
            raise ValueError('Blank or duplicate invoice ID')
        if money(row['amount']) <= 0 or day(row['due_date']) < day(row['invoice_date']):
            raise ValueError('Invoice amount must be positive and due date cannot precede issue date')
        by_id[row['invoice_id']]=row
    ids=set()
    for row in receipts:
        if not row['receipt_id'] or row['receipt_id'] in ids:
            raise ValueError('Blank or duplicate receipt ID')
        ids.add(row['receipt_id'])
        amount=money(row['amount']); dt=day(row['date'])
        if amount <= 0: raise ValueError('Receipt amount must be positive')
        if dt>asof: continue
        inv=by_id.get(row['invoice_id'])
        if not inv or inv['currency']!=row['currency'] or dt<day(inv['invoice_date']):
            exceptions.append(issue(row,'UNALLOCATED_RECEIPT','Unknown invoice, currency mismatch or receipt before invoice'))
        else: paid[row['invoice_id']]+=amount
    result=[]
    for id_,row in by_id.items():
        if day(row['invoice_date'])>asof: continue
        outstanding=money(row['amount'])-paid[id_]
        overdue=max(0,(asof-day(row['due_date'])).days)
        bucket='Current' if overdue==0 else '1-30' if overdue<=30 else '31-60' if overdue<=60 else '61-90' if overdue<=90 else '90+'
        result.append({'invoice_id':id_,'customer':row['customer'],'currency':row['currency'],'amount':money(row['amount']),'paid':paid[id_],
                       'outstanding':outstanding,'days_overdue':overdue,'bucket':bucket,'status':'OVERPAID' if outstanding<0 else 'PAID' if outstanding==0 else 'OPEN','source':row['_source'],'row':row['_row']})
    return {'receivables_aging':result,'receipt_exceptions':exceptions}


def fx_expenses(expenses, rates, config):
    rate_map={}; result=[]; issues=[]; base=config['base_currency']
    for row in rates:
        key=(row['date'],row['currency']); day(row['date'])
        if key in rate_map: raise ValueError('Duplicate daily currency rate')
        value=number(row['rate'])
        if value<=0 or (row['currency']==base and value!=1): raise ValueError('Invalid FX rate')
        rate_map[key]=value
    seen=set()
    for row in expenses:
        if not row['id'] or row['id'] in seen: raise ValueError('Blank or duplicate expense ID')
        seen.add(row['id']); day(row['date'])
        amount=money(row['amount']); plan=number(row['budget_rate'])
        if amount<0 or plan<=0: raise ValueError('Expense must be non-negative and budget rate positive')
        if row['currency']==base and plan!=1: raise ValueError('Base currency budget rate must equal 1')
        rate=D(1) if row['currency']==base else rate_map.get((row['date'],row['currency']))
        if rate is None:
            issues.append(issue(row,'MISSING_FX_RATE','No exact-date rate; transaction not converted')); continue
        actual=(amount*rate).quantize(CENT,rounding=ROUND_HALF_UP); budget=(amount*plan).quantize(CENT,rounding=ROUND_HALF_UP)
        result.append({'id':row['id'],'date':row['date'],'category':row['category'],'currency':row['currency'],'foreign_amount':amount,'rate':rate,
                       'base_currency':base,'converted_amount':actual,'budget_rate_amount':budget,'fx_variance':actual-budget,'source':row['_source'],'row':row['_row']})
    return {'fx_expenses':result,'fx_exceptions':issues}


SCHEMAS={
 'journal':['voucher_id','date','account','currency','debit','credit','description'],
 'balances':['account','currency','opening','closing'],
 'budget':['month','department','account','currency','amount'],
 'actual':['month','department','account','currency','amount'],
 'bank':['id','date','currency','amount','reference'],
 'ledger':['id','date','currency','amount','reference'],
 'invoices':['invoice_id','customer','invoice_date','due_date','currency','amount'],
 'receipts':['receipt_id','invoice_id','date','currency','amount'],
 'expenses':['id','date','category','currency','amount','budget_rate'],
 'rates':['date','currency','rate']}
MODULES={'close':(close_checks,('journal','balances')),'budget':(budget_analysis,('budget','actual')),
         'reconcile':(reconcile,('bank','ledger')),'aging':(aging,('invoices','receipts')),'fx':(fx_expenses,('expenses','rates'))}


def run(input_dir, output_dir, config, module='all'):
    if money(config['tolerance'])<0 or int(config['matching_days'])<0 or number(config['budget_alert_pct'])<0:
        raise ValueError('Tolerances, matching days and alert threshold must be non-negative')
    if day(config['period_start'])>day(config['period_end']): raise ValueError('Invalid reporting period')
    day(config['as_of'])
    outputs={}
    for name,(fn,inputs) in MODULES.items():
        if module!='all' and name!=module: continue
        rows=[read_csv(Path(input_dir)/(key+'.csv'),SCHEMAS[key],config.get('column_mapping',{}).get(key)) for key in inputs]
        outputs.update(fn(*rows,config))
    target=Path(output_dir); target.mkdir(parents=True,exist_ok=False)
    for name,rows in outputs.items():
        fields=list(rows[0]) if rows else ['source','row','code','detail']
        write_csv(target/(name+'.csv'),rows,fields)
    (target/'results.json').write_text(json.dumps(outputs,ensure_ascii=False,indent=2,default=str),encoding='utf-8')
    (target/'config_used.json').write_text(json.dumps(config,ensure_ascii=False,indent=2),encoding='utf-8')
    report=['# 财务检查报告 / Finance Operations Report','', '工具输出供人工复核，未修改原始数据。 / Review outputs before accounting action.','']
    for name,rows in outputs.items(): report.append(f'- {name}: {len(rows)} 条 / rows')
    alerts=[r for r in outputs.get('budget_monthly',[]) if r['status']!='WITHIN_THRESHOLD']
    report+=['','## 预算重点 / Budget highlights']
    for row in sorted(alerts,key=lambda r:r['variance'],reverse=True)[:10]:
        report.append(f"- {row['department']} / {row['account']} / {row['month']}: 差异 variance {row['variance']} {row['currency']} ({row['status']})")
    report+=['','金额按币种分别分析；不同币种之间不求和。 / Amounts are not aggregated across currencies.']
    (target/'report.md').write_text('\n'.join(report)+'\n',encoding='utf-8')
    return outputs
