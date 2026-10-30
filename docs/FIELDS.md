# 输入字段说明

所有模板第一行为表头。金额与币种是独立字段，金额不带币种符号或千分位。参考号缺失可以为空，金额不可留空。

| 文件 | 字段与含义 |
|---|---|
| journal | voucher_id 凭证号；date 日期；account 科目；currency 币种；debit 借方；credit 贷方；description 摘要。借贷零值填 0，每行只允许一边为正 |
| balances | account 科目；currency 币种；opening 期初余额；closing 期末余额，均借正贷负 |
| budget / actual | month 月份；department 部门；account 费用科目；currency 币种；amount 费用金额 |
| bank / ledger | id 唯一流水号；date 日期；currency 币种；amount 流入正、流出负；reference 业务参考号，可空 |
| invoices | invoice_id 唯一发票号；customer 客户；invoice_date 开票日期；due_date 到期日；currency 币种；amount 正发票额 |
| receipts | receipt_id 唯一收款号；invoice_id 对应发票；date 收款日期；currency 币种；amount 正收款额 |
| expenses | id 唯一费用号；date 发生日；category 费用类别；currency 原币；amount 原币金额；budget_rate 预算折算汇率 |
| rates | date 日期；currency 外币；rate 本位币/外币，每个日期币种只有一条 |

配置中的金额 tolerance 用于凭证平衡和流水匹配。matching_days 为绝对日期差上限，不区分工作日。budget_alert_pct 使用百分数，例如 10 表示 10%。

读取金额失败、重复唯一 ID、结构错误会中止对应运行。凭证行格式错误进入 close_issues，其金额不纳入凭证或余额汇总，必须人工修复。处理后的余额结果因此应结合异常清单阅读。
