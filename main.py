"""VS Code: open this file and choose Run Python File, or press F5."""
import argparse
import json
from datetime import datetime
from pathlib import Path
from finance_tools import MODULES, run

ROOT=Path(__file__).resolve().parent

def main():
    parser=argparse.ArgumentParser(description='本地财务运营工具 / Local finance toolkit')
    parser.add_argument('--module',choices=['all',*MODULES],default='all')
    parser.add_argument('--input',type=Path,default=ROOT/'examples')
    parser.add_argument('--config',type=Path,default=ROOT/'config.json')
    parser.add_argument('--output',type=Path,default=None)
    args=parser.parse_args()
    output=args.output or ROOT/'outputs'/datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    try:
        config=json.loads(args.config.read_text(encoding='utf-8-sig'))
        results=run(args.input,output,config,args.module)
    except (ValueError,OSError,KeyError) as exc:
        parser.exit(1,f'运行失败 / Failed: {exc}\n')
    print(f'完成 / Completed: {output.resolve()}')
    print('请打开 report.md 查看摘要，CSV 可用 Excel 打开。')
    print(f'{len(results)} result tables generated. Source files unchanged.')

if __name__=='__main__': main()
