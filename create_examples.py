"""Recreate clearly synthetic demo fixtures; never reads company data."""
import csv
from pathlib import Path
from finance_tools import SCHEMAS
ROOT=Path(__file__).resolve().parent
DATA={
'journal':[
['V001','2026-10-01','1002','CNY','1000','0','Customer payment'],
['V001','2026-10-01','1122','CNY','0','1000','Customer payment'],
['V002','2026-10-02','6602','CNY','200','0','Office supplies'],
['V002','2026-10-02','1002','CNY','0','180','Office supplies'],
['V003','2026-10-03','9999','CNY','50','0','Unknown account'],
['V003','2026-10-03','9999','CNY','50','0','Unknown account'],
['V004','2026-09-30','6602','CNY','10','0','Outside period'],
['V005','2026-10-05','6602','CNY','bad','0','Invalid amount']],
'balances':[['1002','CNY','5000','5820'],['1122','CNY','3000','2000'],['6602','CNY','0','250']],
'budget':[['2026-09','Sales','6602','CNY','900'],['2026-10','Sales','6602','CNY','1000'],['2026-10','IT','6602','CNY','500']],
'actual':[['2026-09','销售部','6602','CNY','950'],['2026-10','销售','6602','CNY','1250'],['2026-10','IT','6602','CNY','400'],['2026-10','HR','6602','CNY','100']],
'bank':[['B1','2026-10-01','CNY','1000','PAY001'],['B2','2026-10-02','CNY','-200',''],['B3','2026-10-03','CNY','-15','FEE'],['B4','2026-10-04','USD','100','USD001']],
'ledger':[['L1','2026-10-02','CNY','1000','PAY001'],['L2','2026-10-02','CNY','-200',''],['L3','2026-10-03','CNY','-200',''],['L4','2026-10-04','CNY','100','USD001']],
'invoices':[['I1','Example Customer A','2026-09-01','2026-09-30','CNY','1000'],['I2','Example Customer B','2026-10-01','2026-11-15','USD','500'],['I3','Example Customer C','2026-07-01','2026-07-15','CNY','200']],
'receipts':[['R1','I1','2026-10-10','CNY','400'],['R2','I2','2026-11-01','USD','100'],['R3','UNKNOWN','2026-10-10','CNY','30'],['R4','I3','2026-10-15','CNY','250']],
'expenses':[['E1','2026-10-01','Travel','USD','100','7.00'],['E2','2026-10-01','Software','CNY','200','1'],['E3','2026-10-02','Travel','EUR','50','7.80']],
'rates':[['2026-10-01','USD','7.10'],['2026-10-01','EUR','7.90']]
}

def main():
    for name,fields in SCHEMAS.items():
        for folder,rows in [('examples',DATA[name]),('templates',[])]:
            target=ROOT/folder; target.mkdir(exist_ok=True)
            with (target/(name+'.csv')).open('w',encoding='utf-8-sig',newline='') as f:
                writer=csv.writer(f);writer.writerow(fields);writer.writerows(rows)
    print('Synthetic examples and empty CSV templates created.')

if __name__=='__main__': main()
