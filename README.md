# Finance Operations Toolkit｜财务运营工具箱

在 VS Code 直接运行的五类财务工具：月结检查、预算差异、银行对账、应收账龄、多币种费用。

**Python 3.10+，仅用标准库，无需 pip 安装依赖。所有计算在本地执行。** 示例是明确标注的模拟业务数据，含刻意植入的异常；不代表真实公司数据或实际工作业绩。

## 在 VS Code 中运行

1. 下载或克隆本仓库，在 VS Code 选择「文件 → 打开文件夹」，打开仓库根目录。
2. 安装 Python 3.10 或以上和微软 Python 扩展；用 `Python: Select Interpreter` 选择已安装的解释器。
3. 打开 `main.py`，点击右上角 **Run Python File / 运行 Python 文件**。默认运行全部演示。
4. 也可按 **F5**，选择「运行全部演示工具」。运行配置已包含在 `.vscode/launch.json`。
5. 在终端显示的 `outputs/时间戳/` 文件夹查看 `report.md` 和 CSV；CSV 使用 UTF-8 BOM，可用 Excel 打开。

命令行等价操作：

```bash
python main.py
python main.py --module close
python main.py --module budget
python main.py --module reconcile
python main.py --module aging
python main.py --module fx
python test_tools.py
```

若系统使用 `python3` 或 `py` 命令，可相应替换 `python`。从任意工作目录运行 `main.py`，默认数据和配置路径均相对于脚本位置解析。

## 五类工具

| 模块 | 输入文件 | 主要输出与判断 |
|---|---|---|
| `close` 月结检查 | `journal.csv`、`balances.csv` | 按凭证及币种检查借贷平衡；疑似重复行、空字段、异常科目、跨期；期初＋本期借方－贷方与期末余额核对 |
| `budget` 预算分析 | `budget.csv`、`actual.csv` | 月度与年初至期末累计差异；部门名称映射；超预算和无预算发生额；中英文摘要 |
| `reconcile` 银行对账 | `bank.csv`、`ledger.csv` | 按币种、方向、金额容差和日期窗口匹配；双方唯一且非空参考号一致才标记 MATCHED；歧义交人工处理 |
| `aging` 应收账龄 | `invoices.csv`、`receipts.csv` | 指定基准日的剩余应收、部分回款、逾期分层；未来收款不计入；超额和未分配收款单列 |
| `fx` 外币费用 | `expenses.csv`、`rates.csv` | 按交易日准确匹配汇率；折算金额、预算汇率金额和差异；缺失汇率单列 |

这些是本地辅助核对工具，不会自动记账、发送催款或修改原始文件。月结规则只能检验已配置的规则，不能替代会计判断或完整合规审查。

## 使用自己的数据

1. 将 `templates/` 中所需的空 CSV 复制到本地 `private_data/`，填入数据。该文件夹已加入 `.gitignore`。
2. 编辑 `config.json`：期间、账龄基准日、金额容差、匹配天数、预算阈值、币种、科目清单与字段映射。
3. 运行：

```bash
python main.py --module budget --input private_data --config config.json
```

运行 `all` 需提供全部十个输入文件；单模块只需对应的两个文件。输入 CSV 必须为 UTF-8 或 UTF-8 BOM。输出目录每次新建；显式指定的输出目录若已存在则拒绝覆盖。

字段映射格式（标准字段名 → 你的表头）：

```json
"column_mapping": {
  "actual": {
    "month": "月份", "department": "部门", "account": "科目",
    "currency": "币种", "amount": "实际金额"
  }
}
```

## 数据口径与边界

- 金额以十进制定点计算，输入最多两位小数，不接受千分位逗号、NaN 或无穷值。汇率可使用更多小数位。当前统一为两位小数工作流，未实现 JPY 零位或 KWD 三位币种精度配置。
- 日期 `YYYY-MM-DD`，预算月份 `YYYY-MM`；币种使用一致的大写编码。源文件名和源行号随异常输出，预算输出保留聚合来源。
- 科目余额统一用**借方为正、贷方为负**。导入前将余额表转换为该口径。日记账覆盖目标期间全部发生额，才可解释余额核对结果。
- 重复凭证检查为“相同凭证、日期、科目、币种、借贷额和摘要”的疑似重复行；不会将同一凭证正常的多条分录误当作重复凭证号。
- 预算模块是**费用预算**：正差异表示费用超出预算。收入预算应另配方向逻辑；当前不把费用规则直接用于收入。
- 银行和账面金额统一为流入正、流出负。仅实现一对一；一对多、多对一、净额结算和手续费拆分保留人工复核。自动匹配不是银行余额调节表，也不执行记账。
- 应收按发票号分配收款；到期当日为 Current。未分配和币种不一致的收款不冲减应收。超额回款显示负余额及 OVERPAID。贷项通知单和跨发票抵扣需先整理后导入。
- 汇率定义为 **1 单位外币 = rate 单位本位币**，要求交易日完全匹配，不自动向前填充；缺失行不会转换。FX variance 是相同外币金额在实际与预算汇率下的差额，不是已实现汇兑损益或报表折算调整。
- 不同币种分开分析，不直接加总。输出 CSV 的文本公式前缀会被转义以减少在 Excel 打开时执行公式的风险。

## 文件说明

```text
main.py                 VS Code 直接运行入口 / CLI
finance_tools.py        五类可复用计算模块
config.json             配置与映射
examples/               有意包含异常的模拟业务数据
templates/              空白 CSV 表头模板
sample_outputs/         演示结果，方便先看效果
test_tools.py           自动化测试
create_examples.py      重建演示数据及空模板
.vscode/                VS Code 运行配置
docs/                   字段说明与验收指南
```

## 验证与复核

运行 `python test_tools.py` 验证借贷不平、重复行、双边匹配歧义、币种隔离、账龄边界、未来收款、超额收款、汇率缺失、金额精度和不覆盖结果等行为。演示有意包含问题，出现 REVIEW/UNMATCHED 不代表工具运行失败。无效金额等源数据应先修复再运行。

真实公司账务明细通常不公开，因此这里提供透明的模拟输入来检验规则。将真实业务数据替换后，可记录复核结果和实际耗时；不要将未经验证的效率或准确率写成项目成果。

Development: independently scoped, AI-assisted implementation. Suitable for portfolio demonstrations and adaptable to local workflows after validation.
