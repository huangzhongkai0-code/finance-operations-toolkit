# 演示验收与面试讲解

1. 在 VS Code 打开 main.py，运行一次。展示终端输出目录及 report.md。
2. voucher_checks 中 V001 平衡，V002 差额为 20 CNY；close_issues 包含跨期、未知科目、重复和无效金额。
3. budget_monthly 中 Sales 十月预算 1,000、实际 1,250、超支 250 / 25%；HR 为无预算发生额。Sales 累计实际为 2,200。
4. bank_reconciliation 中 B1 匹配 L1；B2 有两个候选而保留 REVIEW；B4 的 USD 不与 CNY 混配。
5. receivables_aging 中 I1 剩余 600、逾期 31 天；I2 的未来收款未计入；I3 超收 50。
6. fx_expenses 中 E1 折算 710 CNY，比预算汇率金额多 10；E3 缺失当日 EUR 汇率而进入异常。
7. 将示例复制到 private_data，再调整其中一项金额重新运行。展示更新前后差异和原始行号。
8. 运行 test_tools.py，解释测试如何避免重复匹配、未来收款和金额精度问题。

讲解重点：业务问题 → 输入口径 → 检查规则 → 异常复核 → 输出追溯。改动前备份自己的业务文件；示例本身就是测试数据。
