# 题库复核覆盖核对（2026-11-06）

全库 **2271 题均有当前有效证据，待复核 0 题**。这里的“待复核”指没有当前有效证据覆盖的真实题号，不能与“缺少完整自动核验模型”混用。后者仍是 **13 题**，全部已经逐题复核并明确保留人工参考依据。本轮实际逐题复核 5 题并补齐旧复核工具的问法识别，未新增整题模型或修改题目；另外核对全库和全部历史复核范围。

完整机器证据见 [review_coverage_audit.json](../data/review_coverage_audit.json)，包括输入文件 SHA-256、两个互斥题号集合、14 份范围的基线与集合差、13 道人工参考题及 17 道学生自评题的清单。证据绑定源提交 `46675531faf051ca92e8ee2911cdd1c323054a68`；覆盖审计完成时结果仅保存在本地；后续提交、推送及部署状态以 Git 与 Pages 工作流记录为准。

附加重放发现 `primary_recheck.py` 原先只能重放 859/864 道小学题，5 种既有问法会抛 `ParseError`，不是参考答案不一致。本轮逐题核对并修复这些识别缺口，参考答案和题库判题模式保持不变：

| 实际逐题复核 | 依据与边界 |
|---|---|
| `cnm_p003_q2` | 从左计数的首位为第 1 个，序号不等于总数 |
| `cnm_p015_q1` | 以观察者为参照，正对方向为前面，不推断地理方向 |
| `cnm_p019_q1` | 指定凑十法：10−9=1，3−1=2；从题干数值计算拆分，拒绝非法数域、被拆数不一致或多个等价候选 |
| `cnm_p072_q1` | 用 `(a+b)−a=b` 验算；不排斥其它完整方法，也不以只核个位代替全值 |
| `cnm_p099_q1` | 线段的两个端点与有限长度，区别于直线、射线 |

定义和课堂规则只识别明确的完整问法，不能吞掉否定或改义题干；候选必须唯一。修复后全部 864 道小学题均可只读题干、题型与选项重放，无法求解 0、不匹配 0。该步骤是算术/事实规则复核，不冒称全部是人工盲解或完整形式证明；也未将历史日志直接当成本次重放结果。

本轮 767 项 Python 测试全部通过（含 9 项新增复核工具回归及全量小学题重放），数据格式与全库参考验证通过；14 份历史范围、当前源指纹和 26 项人工参考组件检查均通过。题库、模型和原验证报告未改动。

| 当前覆盖依据 | 题数 | 核对方式 |
|---|---:|---|
| 原有自动核验题 | 1739 | 与 `be357c0af72d88c2bdd8c02ea7169424e1eb6de9` 的完整题目对象逐字段相同，本轮重新执行参考核验通过 |
| 后续逐题复核记录 | 532 | 精确等于该基线中全部无 `verify` 题，`answer_review_2026-10-30.json` 每个题号恰出现一次，答案和源指纹均有效 |
| 两类有效证据的并集 | 2271 | 等于当前题库全部题号；交集、额外题号和未覆盖题号均为空 |
| 待复核 | 0 | 当前题号集合减有效证据题号集合为空 |

当前题库和该基线均有 2271 个不重复题号，题号集合完全一致。14 份固定范围（532、455、160、105、63、43、41、36、33、29、25、20、16、13）均与各自历史基线无 `verify` 的真实题号集合相同；范围缺失、额外、重复题号均为 0。它们重叠，不能把各轮题数相加作为全库覆盖数。

全库当前参考答案自动核验 **2258 / 2271**，不一致 **0**。未自动参考集合、当前报告的 `unverifiable_ids`、最新 13 题复核清单中的人工集合三者完全相等；13 题的推导、边界、缺失依据及重新建模条件均有效，共 26 项可执行组件。分类是比较准则 10、课堂约定 1、设计或应答证据 1、开放解释 1。它们的自动化限制仍存在，不属于漏审，也未被改成自动通过。

人工参考题号如下：

```text
cnm_085_q1
cnm_102_q1 cnm_102_q2 cnm_102_q3
cnm_105_q1 cnm_105_q2
cnm_118_q1
cnm_130_q4
cnm_198_q2
cnm_292_q2 cnm_292_q3 cnm_292_q4
cnm_303_q1
```

学生作答自评仍为 **17 题（11 道 choice + 6 道 self）**。其中 5 道 self 的参考答案有自动核验模型，学生自由作答仍需自评；`cnm_118_q1` 按题面课堂格式约定判选项，其参考依据保留人工。这些口径不应合并。

可以在仓库内复算覆盖差集，并用现有验证器检查答案、指纹及模型/组件：

```sh
python3 scripts/validate.py
python3 scripts/verify_questions.py --check
python3 -m unittest discover -s tests -p 'test_*.py'
python3 - <<'PY'
import hashlib, json, subprocess
from pathlib import Path
r = json.loads(Path('data/review_coverage_audit.json').read_text())
for name, digest in r['input_sha256'].items():
    assert hashlib.sha256(Path(name).read_bytes()).hexdigest() == digest, name
q = json.loads(Path('data/questions.json').read_text())
ids = {x['id'] for x in q}
base = json.loads(subprocess.check_output(['git', 'show', r['baseline_commit'] + ':data/questions.json']))
base_auto = {x['id'] for x in base if x.get('verify')}
current_by_id = {x['id']: x for x in q}
assert all(current_by_id[x['id']] == x for x in base if x.get('verify'))
review = json.loads(Path('data/answer_review_2026-10-30.json').read_text())
review_ids = {x['id'] for x in review['entries']}
assert len(q) == len(ids) == 2271
assert ids == {x['id'] for x in base}
assert len(base_auto) == 1739 and len(review_ids) == len(review['entries']) == 532
assert review_ids == {x['id'] for x in base if not x.get('verify')}
assert not (base_auto & review_ids)
assert ids - (base_auto | review_ids) == set()
assert r['inventory_partition']['pending_review_ids'] == []
print('PASS: 2271 covered; pending review IDs = []')
PY
```

上述结果属于 AI 生成题库的核验与复核覆盖证据，不等于教师审核，也不把任意学生自然语言自动评分为正确。
