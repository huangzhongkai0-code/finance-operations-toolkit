import json
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path
from decimal import Decimal as D
from finance_tools import *

ROOT=Path(__file__).resolve().parent

class FinanceTests(unittest.TestCase):
    def setUp(self):
        self.config=json.loads((ROOT/'config.json').read_text(encoding='utf-8'))
    def rows(self,key):
        return read_csv(ROOT/'examples'/(key+'.csv'),SCHEMAS[key])
    def test_close_detects_seeded_exceptions(self):
        r=close_checks(self.rows('journal'),self.rows('balances'),self.config)
        codes={x['code'] for x in r['close_issues']}
        self.assertTrue({'INVALID_LINE','UNKNOWN_ACCOUNT','POSSIBLE_DUPLICATE','OUT_OF_PERIOD','MISSING_BALANCE'}<=codes)
        self.assertEqual(next(x for x in r['voucher_checks'] if x['voucher_id']=='V002')['difference'],D('20'))
        self.assertEqual(next(x for x in r['balance_checks'] if x['account']=='6602')['difference'],D('50'))
    def test_invalid_double_sided_line_excluded_from_balance(self):
        rows=self.rows('journal')[:1]; rows[0]['debit']='500';rows[0]['credit']='100'
        r=close_checks(rows,[],self.config)
        self.assertEqual(r['voucher_checks'],[])
        self.assertEqual(r['balance_checks'],[])
    def test_budget_mapping_zero_budget_and_ytd(self):
        r=budget_analysis(self.rows('budget'),self.rows('actual'),self.config)
        sales=next(x for x in r['budget_monthly'] if x['department']=='Sales' and x['month']=='2026-10')
        self.assertEqual(sales['variance'],D('250'));self.assertEqual(sales['variance_pct'],D('25'))
        hr=next(x for x in r['budget_monthly'] if x['department']=='HR')
        self.assertEqual(hr['status'],'UNBUDGETED');self.assertEqual(hr['variance_pct'],'')
        self.assertEqual(next(x for x in r['budget_ytd'] if x['department']=='Sales')['actual'],D('2200'))
    def test_reconciliation_ambiguity_and_currency(self):
        r=reconcile(self.rows('bank'),self.rows('ledger'),self.config)
        self.assertEqual([x['status'] for x in r['bank_reconciliation']],['MATCHED','REVIEW','UNMATCHED','UNMATCHED'])
        self.assertEqual(len(r['ledger_unmatched']),3)
    def test_reverse_ambiguity_prevents_reusing_ledger(self):
        bank=self.rows('bank')[:1]; duplicate=deepcopy(bank[0]);duplicate['id']='B99'
        r=reconcile(bank+[duplicate],self.rows('ledger')[:1],self.config)
        self.assertTrue(all(x['status']=='REVIEW' for x in r['bank_reconciliation']))
    def test_unique_without_reference_still_requires_review(self):
        b=self.rows('bank')[:1];l=self.rows('ledger')[:1];b[0]['reference']='';l[0]['reference']=''
        self.assertEqual(reconcile(b,l,self.config)['bank_reconciliation'][0]['status'],'REVIEW')
    def test_aging_partial_future_overpayment(self):
        r=aging(self.rows('invoices'),self.rows('receipts'),self.config)
        values={x['invoice_id']:x for x in r['receivables_aging']}
        self.assertEqual(values['I1']['outstanding'],D('600'));self.assertEqual(values['I1']['bucket'],'31-60')
        self.assertEqual(values['I2']['paid'],0);self.assertEqual(values['I3']['status'],'OVERPAID')
        self.assertEqual(len(r['receipt_exceptions']),1)
    def test_aging_boundary(self):
        inv=self.rows('invoices')[:1];inv[0]['due_date']='2026-10-01'
        self.assertEqual(aging(inv,[],self.config)['receivables_aging'][0]['bucket'],'1-30')
    def test_fx_rate_missing_and_decimal_rounding(self):
        r=fx_expenses(self.rows('expenses'),self.rows('rates'),self.config)
        self.assertEqual(r['fx_expenses'][0]['converted_amount'],D('710'));self.assertEqual(r['fx_expenses'][0]['fx_variance'],D('10'))
        self.assertEqual(len(r['fx_exceptions']),1)
        rows=self.rows('expenses')[:1];rows[0]['amount']='0.05'
        self.assertEqual(fx_expenses(rows,self.rows('rates'),self.config)['fx_expenses'][0]['converted_amount'],D('0.36'))
    def test_invalid_money(self):
        for val in ['NaN','Infinity','1,000','0.001']:
            with self.assertRaises(ValueError):money(val)
    def test_duplicate_receipt_rejected(self):
        r=self.rows('receipts')
        with self.assertRaises(ValueError):aging(self.rows('invoices'),r+[r[0]],self.config)
    def test_csv_bom_mapping_quoted_text_and_formula(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'test.csv';p.write_text('\ufeff金额,说明\n1.00,"a,b"\n',encoding='utf-8')
            r=read_csv(p,['amount','description'],{'amount':'金额','description':'说明'})
            self.assertEqual(r[0]['description'],'a,b');self.assertEqual(r[0]['_row'],2)
            self.assertEqual(safe_cell('=1+1'),"'=1+1")
            self.assertEqual(safe_cell(D('-12')),D('-12'))
    def test_all_outputs_and_no_overwrite(self):
        with tempfile.TemporaryDirectory() as tmp:
            target=Path(tmp)/'run';r=run(ROOT/'examples',target,self.config)
            self.assertEqual(len(r),11);self.assertTrue((target/'report.md').exists())
            with self.assertRaises(FileExistsError):run(ROOT/'examples',target,self.config)

if __name__=='__main__':unittest.main(verbosity=2)
